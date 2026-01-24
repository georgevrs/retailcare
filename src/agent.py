import os
import json
import logging
from typing import List, Dict, Any, Optional
from openai import AsyncAzureOpenAI
from src.models import Intent, AgentResponse, TicketDetails
from src.faq import faq_kb
from src.github_issues import github_client

logger = logging.getLogger(__name__)

class CallCenterAgent:
    def __init__(self):
        self.client = AsyncAzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_KEY"),
            api_version="2024-02-15-preview",
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )
        self.deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")

    async def process_utterance(self, session: Any, user_input: str) -> AgentResponse:
        session.add_message("user", user_input)
        
        system_prompt = """Είσαι η ψηφιακή εξυπηρέτηση του καταστήματος RetailCare. 
Μιλάς ΜΟΝΟ Ελληνικά με ευγενικό και επαγγελματικό ύφος.

ΣΚΟΠΟΣ:
1. Κατανόηση αν ο χρήστης έχει παράπονο/πρόβλημα (COMPLAINT_TICKET) ή ζητά πληροφορίες (INFORMATION).
2. Αν είναι παράπονο: Συλλέγεις απαραίτητα στοιχεία (τίτλο, περιγραφή, κατηγορία, επείγον) και καλείς το εργαλείο `create_ticket`. Ρωτάς μόνο ΕΝΑ πράγμα τη φορά.
3. Αν είναι πληροφορία: Αναζητάς στο FAQ χρησιμοποιώντας το εργαλείο `search_faq`.
4. Αν είναι χαιρετισμός: Απαντάς ευγενικά.

ΚΑΝΟΝΕΣ:
- Μην ζητάς πολλές πληροφορίες μαζί.
- Αν λείπει ο αριθμός παραγγελίας, πες ότι δεν πειράζει αλλά αν τον βρουν ας τον πουν.
- Αν δεν βρεις απάντηση στο FAQ, πες ότι θα το προωθήσεις σε εκπρόσωπο.
- Πάντα να επιβεβαιώνεις τον αριθμό εισιτηρίου (ticket ID) αν δημιουργηθεί.
- Απόκριση σε JSON format αν δεν καλείς εργαλείο.

Εργαλεία:
- search_faq(query: str): Αναζήτηση στη βάση γνώσεων.
- create_ticket(details: dict): Δημιουργία ticket στο σύστημα.
"""

        tools = [
            {
                "type": "function",
                "function": {
                    "name": "search_faq",
                    "description": "Search the local FAQ knowledge base for retail information",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "The search query in Greek"}
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "create_ticket",
                    "description": "Create a support ticket in the PM tool (GitHub)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "Short summary of the issue"},
                            "description": {"type": "string", "description": "Detailed description"},
                            "category": {"type": "string", "enum": ["delivery", "refund", "billing", "warranty", "product", "other"]},
                            "urgency": {"type": "string", "enum": ["low", "medium", "high"]},
                            "order_id": {"type": "string", "description": "Optional order ID"},
                            "product": {"type": "string", "description": "Optional product name"}
                        },
                        "required": ["title", "description", "category", "urgency"]
                    }
                }
            }
        ]

        messages = [{"role": "system", "content": system_prompt}] + session.conversation_history

        try:
            response = await self.client.chat.completions.create(
                model=self.deployment,
                messages=messages,
                tools=tools,
                tool_choice="auto"
            )

            message = response.choices[0].message
            
            if message.tool_calls:
                tool_call = message.tool_calls[0]
                function_name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)
                
                if function_name == "search_faq":
                    faq_results = faq_kb.search(args["query"])
                    if faq_results:
                        answer = faq_results[0].answer
                        final_response = await self._generate_final_answer(session, f"FAQ found: {answer}")
                        return AgentResponse(intent=Intent.INFORMATION, response_text=final_response)
                    else:
                        return AgentResponse(
                            intent=Intent.INFORMATION, 
                            response_text="Λυπάμαι, δεν βρήκα συγκεκριμένη πληροφορία για αυτό. Θα το σημειώσω για να σας καλέσει ένας εκπρόσωπος."
                        )
                
                elif function_name == "create_ticket":
                    ticket_details = TicketDetails(**args)
                    result = await github_client.create_ticket(ticket_details, session.phone_number)
                    if result:
                        session.ticket_id = result["number"]
                        session.ticket_url = result["url"]
                        msg = f"Το αίτημά σας καταχωρήθηκε με αριθμό #{result['number']}. Θα ενημερωθείτε σύντομα."
                        session.add_message("assistant", msg)
                        return AgentResponse(intent=Intent.COMPLAINT_TICKET, response_text=msg)
                    else:
                        return AgentResponse(
                            intent=Intent.COMPLAINT_TICKET,
                            response_text="Υπήρξε ένα πρόβλημα κατά την καταχώρηση του αιτήματος. Παρακαλώ περιμένετε να σας συνδέσω με έναν εκπρόσωπο."
                        )

            # Normal text response
            text = message.content or ""
            session.add_message("assistant", text)
            
            # Simple intent heuristic for demo
            intent = Intent.UNKNOWN
            if "ticket" in text.lower() or "αίτημα" in text.lower():
                intent = Intent.COMPLAINT_TICKET
            elif "?" in text:
                intent = Intent.INFORMATION
                
            return AgentResponse(intent=intent, response_text=text)

        except Exception as e:
            logger.error(f"Error in agent processing: {e}")
            return AgentResponse(
                intent=Intent.UNKNOWN,
                response_text="Με συγχωρείτε, αντιμετωπίζω ένα τεχνικό πρόβλημα. Μπορείτε να επαναλάβετε;"
            )

    async def _generate_final_answer(self, session: Any, context: str) -> str:
        # Mini-turn to format the FAQ answer naturally
        prompt = f"Με βάση αυτή την πληροφορία: '{context}', απάντησε στον χρήστη ευγενικά στα Ελληνικά."
        messages = [{"role": "system", "content": "Είσαι η RetailCare. Απάντησε σύντομα."}, {"role": "user", "content": prompt}]
        
        resp = await self.client.chat.completions.create(
            model=self.deployment,
            messages=messages,
            max_tokens=150
        )
        text = resp.choices[0].message.content
        session.add_message("assistant", text)
        return text

# Singleton
agent = CallCenterAgent()
