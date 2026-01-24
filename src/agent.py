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
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        key = os.getenv("AZURE_OPENAI_KEY")
        deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
        
        if not endpoint or not key or not deployment:
            logger.error(f"Missing Azure OpenAI configuration: endpoint={bool(endpoint)}, key={bool(key)}, deployment={bool(deployment)}")
        else:
            logger.info(f"Initializing Azure OpenAI with endpoint: {endpoint} and deployment: {deployment}")

        self.client = AsyncAzureOpenAI(
            api_key=key,
            api_version="2024-02-15-preview",
            azure_endpoint=endpoint
        )
        self.deployment = deployment

    async def process_utterance(self, session: Any, user_input: str) -> AgentResponse:
        session.add_message("user", user_input)
        
        system_prompt = """Είσαι η ψηφιακή εξυπηρέτηση του καταστήματος RetailCare. 
Μιλάς ΜΟΝΟ Ελληνικά με ευγενικό και επαγγελματικό ύφος.

ΣΚΟΠΟΣ:
1. Κατανόηση αν ο χρήστης έχει παράπονο/πρόβλημα (COMPLAINT_TICKET) ή ζητά πληροφορίες (INFORMATION).
2. Αν είναι παράπονο: Συλλέγεις απαραίτητα στοιχεία (τίτλο, περιγραφή, κατηγορία, επείγον) και καλείς το εργαλείο `create_ticket`.
3. ΑΠΟΦΑΣΙΣΤΙΚΟΤΗΤΑ: Αν ο χρήστης αναφέρει σαφές πρόβλημα (π.χ. καθυστέρηση, σπασμένο προϊόν) και δώσει στοιχεία (π.χ. αριθμό παραγγελίας), κάλεσε το `create_ticket` ΑΜΕΣΩΣ. Μην ζητάς επιβεβαίωση για την κατηγορία αν είναι προφανής.
4. Αν είναι πληροφορία: Αναζητάς στο FAQ χρησιμοποιώντας το εργαλείο `search_faq`.
5. Αν είναι χαιρετισμός: Απαντάς ευγενικά.

ΚΑΝΟΝΕΣ:
- Ρωτάς μόνο ΕΝΑ πράγμα τη φορά αν λείπουν στοιχεία.
- Αν λείπει ο αριθμός παραγγελίας, πες ότι δεν πειράζει αλλά αν τον βρουν ας τον πουν.
- Αν δεν βρεις απάντηση στο FAQ, πες ότι θα το προωθήσεις σε εκπρόσωπο.
- Πάντα να επιβεβαιώνεις τον αριθμό εισιτηρίου (ticket ID) αν δημιουργηθεί.
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
            
            # Improved intent heuristic for demo
            intent = Intent.UNKNOWN
            lower_text = text.lower()
            
            # Keywords for complaints/tickets
            complaint_keywords = ["ticket", "αίτημα", "καταγραφή", "πρόβλημα", "παράπονο", "εξέλιξη", "αρ. #"]
            if any(k in lower_text for k in complaint_keywords):
                intent = Intent.COMPLAINT_TICKET
            # Keywords for information
            elif "?" in text or any(k in lower_text for k in ["πληροφορία", "ωράριο", "πολιτική", "διεύθυνση"]):
                intent = Intent.INFORMATION
            # Check last user message if AI is asking for more info on a complaint
            elif len(session.conversation_history) >= 2:
                last_user_msg = session.conversation_history[-2]["content"].lower()
                if any(k in last_user_msg for k in ["πρόβλημα", "καθυστέρηση", "σπασμένο", "χρέωση"]):
                    intent = Intent.COMPLAINT_TICKET
                
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
