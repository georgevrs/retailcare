import os
import json
import logging
import re
from typing import List, Dict, Any, Optional
from openai import AsyncAzureOpenAI
from src.models import Intent, AgentResponse, TicketDetails, FlowState, Category, Urgency
from src.faq import faq_kb
from src.github_issues import github_client
from src.store_info import store_info
from src.policy_engine import policy_engine

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
        """Main entry point: classify → extract → decide → respond"""
        session.add_message("user", user_input)
        
        # Step 1: Classify intent
        intent = await self._classify_intent(session, user_input)
        
        # Step 2: Extract slots
        slots = await self._extract_slots(session, user_input, intent)
        
        # Step 3: Determine next action
        action_result = await self._determine_next_action(session, intent, slots)
        
        # Step 4: Generate response
        response = await self._generate_response(session, intent, action_result)
        
        return response

    async def _classify_intent(self, session: Any, user_input: str) -> Intent:
        """Use LLM to classify user intent"""
        # If we have an active intent in flow, continue with it
        if session.flow_state and session.flow_state.active_intent:
            return session.flow_state.active_intent
        
        system_prompt = """Είσαι η ψηφιακή εξυπηρέτηση του καταστήματος RetailCare. 
Κατάταξε την πρόθεση του χρήστη σε μία από τις παρακάτω κατηγορίες:

- COMPLAINT_TICKET: Παράπονο/πρόβλημα που χρειάζεται ticket
- INFORMATION: Ζήτηση πληροφοριών
- ORDER_CANCEL: Ακύρωση παραγγελίας
- ORDER_CHANGE: Αλλαγή παραγγελίας (διεύθυνση, προϊόν, ποσότητα)
- REFUND_REQUEST: Αίτημα επιστροφής χρημάτων
- BAD_EXPERIENCE: Κακή εμπειρία/παράπονο για εξυπηρέτηση
- HUMAN_REQUEST: Ζήτηση να μιλήσει με άνθρωπο
- STORE_HOURS: Ερώτηση για ωράριο καταστήματος
- GREETING: Χαιρετισμός
- GOODBYE: Αποχαιρετισμός
- UNKNOWN: Άγνωστο

Απάντησε ΜΟΝΟ με το όνομα της κατηγορίας."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Χρήστης: {user_input}"}
        ]

        try:
            response = await self.client.chat.completions.create(
                model=self.deployment,
                messages=messages,
                max_tokens=20,
                temperature=0.1
            )
            
            intent_str = response.choices[0].message.content.strip().upper()
            # Try to map to Intent enum
            try:
                return Intent(intent_str)
            except ValueError:
                # Fallback to keyword-based classification
                return self._classify_intent_fallback(user_input)
        except Exception as e:
            logger.error(f"Error in intent classification: {e}")
            return self._classify_intent_fallback(user_input)

    def _classify_intent_fallback(self, user_input: str) -> Intent:
        """Fallback keyword-based intent classification"""
        lower = user_input.lower()
        
        if any(k in lower for k in ["ακύρωση", "ακυρώσω", "cancel"]):
            return Intent.ORDER_CANCEL
        elif any(k in lower for k in ["αλλαγή", "αλλάξω", "change", "μεταβολή"]):
            return Intent.ORDER_CHANGE
        elif any(k in lower for k in ["επιστροφή", "refund", "επιστρέψω", "χρήματα"]):
            return Intent.REFUND_REQUEST
        elif any(k in lower for k in ["ωράριο", "ώρες", "ανοιχτά", "κλειστά"]):
            return Intent.STORE_HOURS
        elif any(k in lower for k in ["άνθρωπος", "human", "εκπρόσωπος", "πρόσωπο", "άνθρωπο"]):
            return Intent.HUMAN_REQUEST
        elif any(k in lower for k in ["αγενής", "κακή", "άσχημη", "ποτέ ξανά"]):
            return Intent.BAD_EXPERIENCE
        elif any(k in lower for k in ["πρόβλημα", "παράπονο", "καθυστέρηση", "σπασμένο"]):
            return Intent.COMPLAINT_TICKET
        elif "?" in user_input or any(k in lower for k in ["τι", "πώς", "ποιο", "ποια", "ποιος"]):
            return Intent.INFORMATION
        elif any(k in lower for k in ["γεια", "χαίρετε", "καλησπέρα"]):
            return Intent.GREETING
        elif any(k in lower for k in ["αντίο", "ευχαριστώ", "bye"]):
            return Intent.GOODBYE
        else:
            return Intent.UNKNOWN

    async def _extract_slots(self, session: Any, user_input: str, intent: Intent) -> Dict[str, Any]:
        """Extract structured slots from user input based on intent"""
        # Initialize or get existing slots
        existing_slots = {}
        if session.flow_state and session.flow_state.slots:
            existing_slots = session.flow_state.slots.copy()
        
        # Use LLM to extract slots
        system_prompt = f"""Εξάγαγε στοιχεία από το μήνυμα του χρήστη για intent: {intent.value}.

Για κάθε intent, εξάγαγε τα ακόλουθα slots:
- COMPLAINT_TICKET: order_id, product, description, category, urgency
- ORDER_CANCEL: order_id, reason, shipment_status
- ORDER_CHANGE: order_id, change_type, new_details
- REFUND_REQUEST: order_id/receipt_id, reason, condition, days_since_delivery, preferred_resolution
- BAD_EXPERIENCE: summary, severity
- HUMAN_REQUEST: callback_number, preferred_time

Απάντησε ΜΟΝΟ με JSON: {{"slot_name": "value"}}"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Χρήστης: {user_input}\nΥπάρχοντα slots: {json.dumps(existing_slots, ensure_ascii=False)}"}
        ]

        try:
            # Use tool calling for structured extraction
            extract_tool = {
                "type": "function",
                "function": {
                    "name": "extract_case_details",
                    "description": "Extract structured case details from user input",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "slots": {
                                "type": "object",
                                "description": "Extracted slot values"
                            }
                        },
                        "required": ["slots"]
                    }
                }
            }
            
            response = await self.client.chat.completions.create(
                model=self.deployment,
                messages=messages,
                tools=[extract_tool],
                tool_choice={"type": "function", "function": {"name": "extract_case_details"}},
                max_tokens=200,
                temperature=0.1
            )
            
            if response.choices[0].message.tool_calls:
                extracted = json.loads(response.choices[0].message.tool_calls[0].function.arguments)
                if "slots" in extracted:
                    existing_slots.update(extracted["slots"])
                    return existing_slots
            
            # Fallback: try to parse as JSON from content
            try:
                content = response.choices[0].message.content
                if content:
                    extracted = json.loads(content)
                    if isinstance(extracted, dict) and "slots" in extracted:
                        existing_slots.update(extracted["slots"])
            except:
                pass
            
            return existing_slots
            
            extracted = json.loads(response.choices[0].message.content)
            # Merge with existing slots
            existing_slots.update(extracted)
            return existing_slots
        except Exception as e:
            logger.error(f"Error in slot extraction: {e}")
            return existing_slots

    async def _determine_next_action(self, session: Any, intent: Intent, slots: Dict[str, Any]) -> Dict[str, Any]:
        """Determine next action: ask question, create ticket, answer FAQ, handoff"""
        # Initialize flow state if needed
        if not session.flow_state:
            session.flow_state = FlowState(active_intent=intent, slots=slots)
        else:
            session.flow_state.active_intent = intent
            session.flow_state.slots.update(slots)
        
        session.active_intent = intent
        
        # Define required slots per intent
        required_slots_map = {
            Intent.ORDER_CANCEL: ["order_id"],
            Intent.ORDER_CHANGE: ["order_id", "change_type", "new_details"],
            Intent.REFUND_REQUEST: ["order_id", "reason"],
            Intent.BAD_EXPERIENCE: ["summary"],
            Intent.HUMAN_REQUEST: [],  # Optional: callback_number, preferred_time
            Intent.COMPLAINT_TICKET: ["description"],
            Intent.STORE_HOURS: [],
            Intent.INFORMATION: []
        }
        
        # For bad experience, detect severity and escalation needs
        if intent == Intent.BAD_EXPERIENCE and slots.get("summary"):
            summary_lower = slots.get("summary", "").lower()
            # Use stems to handle Greek word variations (nominative, accusative, etc.)
            high_severity_keywords = ["αγεν", "ποτέ", "καταγγελ", "απάτη", "δικηγόρ", "legal", "fraud"]
            if any(k in summary_lower for k in high_severity_keywords):
                slots["severity"] = "high"
                slots["needs_human"] = True
                # Don't offer coupon for fraud/legal
                if any(k in summary_lower for k in ["απάτη", "fraud", "δικηγόρ", "legal"]):
                    slots["offer_coupon"] = False
                else:
                    slots["offer_coupon"] = True
            else:
                slots["severity"] = "medium"
                slots["needs_human"] = False
                slots["offer_coupon"] = True
        
        # For order change, if change_type is known but new_details missing, ask specific question
        if intent == Intent.ORDER_CHANGE and slots.get("change_type") and not slots.get("new_details"):
            change_type = slots.get("change_type", "").lower()
            if "διεύθυνση" in change_type or "address" in change_type:
                required_slots_map[intent] = ["order_id", "change_type", "new_address"]
            elif "προϊόν" in change_type or "item" in change_type or "product" in change_type:
                required_slots_map[intent] = ["order_id", "change_type", "new_item"]
            elif "ποσότητα" in change_type or "quantity" in change_type:
                required_slots_map[intent] = ["order_id", "change_type", "new_quantity"]
        
        # For refund, check policy after getting reason
        if intent == Intent.REFUND_REQUEST and slots.get("reason") and not slots.get("policy_checked"):
            policy_result = policy_engine.check_policy("refund", slots)
            slots["policy_checked"] = True
            slots["policy_eligible"] = policy_result.get("eligible", True)
            slots["policy_requirements"] = policy_result.get("what_we_need", [])
            
            # If policy requires additional info, add to missing slots
            if policy_result.get("what_we_need"):
                required_slots = required_slots_map.get(intent, [])
                # Add policy requirements as additional slots to collect
                for req in policy_result.get("what_we_need", []):
                    if "ημέρες" in req.lower() and not slots.get("days_since_delivery"):
                        required_slots.append("days_since_delivery")
                    elif "φωτογραφία" in req.lower() and not slots.get("photo_provided"):
                        required_slots.append("photo_provided")
                    elif "περιγραφή" in req.lower() and not slots.get("detailed_description"):
                        required_slots.append("detailed_description")
                required_slots_map[intent] = required_slots
        
        # For cancellation, check policy and suggest alternatives
        if intent == Intent.ORDER_CANCEL and slots.get("order_id") and not slots.get("policy_checked"):
            policy_result = policy_engine.check_policy("cancellation", slots)
            slots["policy_checked"] = True
            slots["policy_eligible"] = policy_result.get("eligible", True)
            slots["cancellation_alternative"] = policy_result.get("alternative")
            
            # If not eligible, we need to ask about alternatives
            if not policy_result.get("eligible"):
                if "alternative_offer_accepted" not in slots:
                    required_slots_map[intent] = required_slots_map.get(intent, []) + ["alternative_offer_accepted"]
        
        required_slots = required_slots_map.get(intent, [])
        missing_slots = [s for s in required_slots if not slots.get(s)]
        
        # If slots missing, ask next question
        if missing_slots:
            next_question = self._generate_next_question(intent, missing_slots[0], slots)
            session.flow_state.missing_slots = missing_slots
            session.flow_state.next_question = next_question
            session.flow_state.last_action = "asked_question"
            session.last_agent_action = "asked_question"
            return {
                "action": "ask_question",
                "question": next_question
            }
        
        # All required slots present - proceed with action
        session.flow_state.missing_slots = []
        session.flow_state.next_question = None
        
        # Special handling for bad experience: high severity needs immediate human handoff
        if intent == Intent.BAD_EXPERIENCE and slots.get("severity") == "high" and slots.get("needs_human"):
            if not slots.get("handoff_confirmed"):
                # Ask if they want human callback
                next_question = "Λυπάμαι πραγματικά γι' αυτό. Θες να σε καλέσει άνθρωπος από την ομάδα μας για να το λύσουμε άμεσα;"
                session.flow_state.next_question = next_question
                session.flow_state.last_action = "asked_question"
                session.last_agent_action = "asked_question"
                return {
                    "action": "ask_question",
                    "question": next_question
                }
        
        # Special handling for cancellation: if not eligible, suggest alternatives
        if intent == Intent.ORDER_CANCEL and not slots.get("policy_eligible", True):
            if not slots.get("alternative_offer_accepted"):
                # Ask about alternatives
                next_question = "Αν η παραγγελία έχει ήδη αποσταλεί, μπορώ να σου προτείνω εναλλακτικά: **αλλαγή σε άλλο προϊόν**, **πίστωση κουπονιού**, ή **επιστροφή μετά την παράδοση**. Ποιο προτιμάς;"
                session.flow_state.next_question = next_question
                session.flow_state.last_action = "asked_question"
                session.last_agent_action = "asked_question"
                return {
                    "action": "ask_question",
                    "question": next_question
                }
        
        if intent == Intent.STORE_HOURS:
            session.flow_state.last_action = "answered_faq"
            session.last_agent_action = "answered_faq"
            return {"action": "get_store_hours"}
        
        elif intent == Intent.INFORMATION:
            session.flow_state.last_action = "answered_faq"
            session.last_agent_action = "answered_faq"
            return {"action": "search_faq", "query": session.conversation_history[-1]["content"]}
        
        elif intent in [Intent.COMPLAINT_TICKET, Intent.ORDER_CANCEL, Intent.ORDER_CHANGE, 
                        Intent.REFUND_REQUEST, Intent.BAD_EXPERIENCE]:
            # For bad experience with high severity, ensure priority label
            if intent == Intent.BAD_EXPERIENCE and slots.get("severity") == "high":
                slots["priority"] = "high"
            session.flow_state.last_action = "created_ticket"
            session.last_agent_action = "created_ticket"
            return {"action": "create_ticket", "intent": intent, "slots": slots}
        
        elif intent == Intent.HUMAN_REQUEST:
            # Check if callback info is provided
            if not slots.get("callback_number"):
                # Ask if they want callback
                next_question = "Θες να σε καλέσουμε πίσω; Αν ναι, πες μου ένα τηλέφωνο και πότε σε βολεύει (πρωί/απόγευμα). Εναλλακτικά μπορώ να ανοίξω ένα αίτημα ώστε να σε αναλάβει εκπρόσωπος."
                session.flow_state.next_question = next_question
                session.flow_state.last_action = "asked_question"
                session.last_agent_action = "asked_question"
                return {
                    "action": "ask_question",
                    "question": next_question
                }
            else:
                session.flow_state.last_action = "handoff_attempted"
                session.last_agent_action = "handoff_attempted"
                return {"action": "handoff", "slots": slots}
        
        else:
            # Default: generate text response
            return {"action": "text_response"}

    def _generate_next_question(self, intent: Intent, missing_slot: str, existing_slots: Dict[str, Any]) -> str:
        """Generate next question in Greek for missing slot"""
        # Special handling for order change new_details
        if intent == Intent.ORDER_CHANGE and missing_slot in ["new_details", "new_address", "new_item", "new_quantity"]:
            change_type = existing_slots.get("change_type", "").lower()
            if missing_slot == "new_address" or ("διεύθυνση" in change_type and missing_slot == "new_details"):
                return "Ποια είναι η νέα διεύθυνση παράδοσης;"
            elif missing_slot == "new_item" or ("προϊόν" in change_type and missing_slot == "new_details"):
                return "Ποιο προϊόν θέλεις να αλλάξεις και με τι;"
            elif missing_slot == "new_quantity" or ("ποσότητα" in change_type and missing_slot == "new_details"):
                return "Ποια είναι η νέα ποσότητα;"
        
        questions = {
            Intent.ORDER_CANCEL: {
                "order_id": "Ποιος είναι ο αριθμός παραγγελίας που θέλεις να ακυρώσεις;",
                "reason": "Γιατί θέλεις να ακυρώσεις την παραγγελία; (π.χ. άργησε, άλλαξα γνώμη)",
                "alternative_offer_accepted": "Αν η παραγγελία έχει ήδη αποσταλεί, μπορώ να σου προτείνω εναλλακτικά: **αλλαγή σε άλλο προϊόν**, **πίστωση κουπονιού**, ή **επιστροφή μετά την παράδοση**. Ποιο προτιμάς;"
            },
            Intent.ORDER_CHANGE: {
                "order_id": "Ποιος είναι ο αριθμός παραγγελίας;",
                "change_type": "Τι θέλεις να αλλάξεις; (διεύθυνση, προϊόν, ποσότητα)",
                "new_details": {
                    "address": "Ποια είναι η νέα διεύθυνση παράδοσης;",
                    "item": "Ποιο προϊόν θέλεις να αλλάξεις και με τι;",
                    "quantity": "Ποια είναι η νέα ποσότητα;"
                }
            },
            Intent.REFUND_REQUEST: {
                "order_id": "Ποιος είναι ο αριθμός παραγγελίας ή απόδειξης;",
                "reason": "Ποιος είναι ο λόγος επιστροφής; (ελαττωματικό, λάθος προϊόν, άλλαξα γνώμη)",
                "days_since_delivery": "Πόσες ημέρες έχουν περάσει από την παράδοση;",
                "condition": "Το προϊόν είναι ανοιχτό ή κλειστό;",
                "photo_provided": "Έχετε φωτογραφία του προϊόντος;",
                "detailed_description": "Μπορείτε να περιγράψετε το πρόβλημα;"
            },
            Intent.BAD_EXPERIENCE: {
                "summary": "Μπορείς να μου περιγράψεις τι συνέβη;"
            },
            Intent.COMPLAINT_TICKET: {
                "description": "Μπορείς να μου πεις περισσότερες λεπτομέρειες για το πρόβλημα;"
            }
        }
        
        intent_questions = questions.get(intent, {})
        return intent_questions.get(missing_slot, f"Μπορείς να μου δώσεις περισσότερες πληροφορίες για το {missing_slot};")

    async def _generate_response(self, session: Any, intent: Intent, action_result: Dict[str, Any]) -> AgentResponse:
        """Generate final response based on action result"""
        action = action_result.get("action")
        
        if action == "ask_question":
            question = action_result.get("question", "")
            session.add_message("assistant", question)
            clean_text = self._clean_text_for_tts(question)
            return AgentResponse(
                intent=intent,
                response_text=clean_text,
                flow_state=session.flow_state
            )
        
        elif action == "get_store_hours":
            # Check if user asked about a specific day
            user_input = session.conversation_history[-1]["content"].lower()
            day = None
            if any(k in user_input for k in ["σάββατο", "saturday", "σαββάτου"]):
                day = "saturday"
            elif any(k in user_input for k in ["κυριακή", "sunday", "κυριακής"]):
                day = "sunday"
            elif any(k in user_input for k in ["αύριο", "tomorrow"]):
                # Get tomorrow's day
                from datetime import datetime, timedelta
                tomorrow = datetime.now(store_info.timezone) + timedelta(days=1)
                day_names = {0: "sunday", 1: "monday", 2: "tuesday", 3: "wednesday", 
                           4: "thursday", 5: "saturday", 6: "saturday"}
                day = day_names[tomorrow.weekday()]
            
            response_text = store_info.render_hours_human(day=day, language="el")
            session.add_message("assistant", response_text)
            return AgentResponse(
                intent=intent,
                response_text=response_text,
                flow_state=session.flow_state
            )
        
        elif action == "search_faq":
            query = action_result.get("query", "")
            faq_results = faq_kb.search(query)
            if faq_results:
                answer = faq_results[0].answer
                final_response = await self._generate_final_answer(session, f"FAQ found: {answer}")
                return AgentResponse(
                    intent=Intent.INFORMATION,
                    response_text=final_response,
                    flow_state=session.flow_state
                )
            else:
                response_text = "Λυπάμαι, δεν βρήκα συγκεκριμένη πληροφορία για αυτό. Θα το σημειώσω για να σας καλέσει ένας εκπρόσωπος."
                session.add_message("assistant", response_text)
                return AgentResponse(
                    intent=Intent.INFORMATION,
                    response_text=response_text,
                    flow_state=session.flow_state
                )
        
        elif action == "create_ticket":
            ticket_intent = action_result.get("intent")
            slots = action_result.get("slots", {})
            
            # Convert slots to TicketDetails
            category_map = {
                Intent.ORDER_CANCEL: Category.DELIVERY,
                Intent.ORDER_CHANGE: Category.DELIVERY,
                Intent.REFUND_REQUEST: Category.REFUND,
                Intent.BAD_EXPERIENCE: Category.OTHER,
                Intent.COMPLAINT_TICKET: Category(slots.get("category", "other")) if slots.get("category") else Category.OTHER
            }
            
            urgency_map = {
                Intent.BAD_EXPERIENCE: Urgency.HIGH,
                Intent.REFUND_REQUEST: Urgency.MEDIUM,
                Intent.ORDER_CANCEL: Urgency.MEDIUM,
                Intent.ORDER_CHANGE: Urgency.MEDIUM,
                Intent.COMPLAINT_TICKET: Urgency(slots.get("urgency", "medium")) if slots.get("urgency") else Urgency.MEDIUM
            }
            
            # Generate captured summary
            captured_summary = self._generate_captured_summary(ticket_intent, slots)
            
            # Identify missing info
            missing_info = []
            if ticket_intent == Intent.ORDER_CANCEL and not slots.get("reason"):
                missing_info.append("Λόγος ακύρωσης")
            if ticket_intent == Intent.REFUND_REQUEST and not slots.get("condition"):
                missing_info.append("Κατάσταση προϊόντος (ανοιχτό/κλειστό)")
            if not slots.get("order_id") and ticket_intent in [Intent.ORDER_CANCEL, Intent.ORDER_CHANGE, Intent.REFUND_REQUEST]:
                missing_info.append("Αριθμός παραγγελίας")
            
            # Requested resolution
            requested_resolution = None
            if ticket_intent == Intent.REFUND_REQUEST:
                requested_resolution = slots.get("preferred_resolution", "Επιστροφή χρημάτων")
            elif ticket_intent == Intent.ORDER_CANCEL:
                requested_resolution = slots.get("alternative_offer_accepted", "Ακύρωση")
            
            ticket_details = TicketDetails(
                title=slots.get("description", slots.get("summary", "Customer request"))[:100],
                description=slots.get("description", slots.get("summary", "No description provided")),
                category=category_map.get(ticket_intent, Category.OTHER),
                urgency=urgency_map.get(ticket_intent, Urgency.MEDIUM),
                order_id=slots.get("order_id"),
                product=slots.get("product")
            )
            
            # Add extra labels for high severity bad experience
            if ticket_intent == Intent.BAD_EXPERIENCE and slots.get("severity") == "high":
                ticket_details.extra_labels = ["priority:high"]
            
            result = await github_client.create_ticket(
                ticket_details, 
                session.phone_number,
                captured_summary=captured_summary,
                missing_info=missing_info if missing_info else None,
                requested_resolution=requested_resolution
            )
            
            if result:
                session.ticket_id = result["number"]
                session.ticket_url = result["url"]
                
                # Generate detailed confirmation message
                confirmation_msg = self._generate_confirmation_message(
                    ticket_intent, slots, result["number"], missing_info
                )
                session.add_message("assistant", confirmation_msg)
                
                session.flow_state.confirmation_summary = confirmation_msg
                
                return AgentResponse(
                    intent=ticket_intent,
                    response_text=confirmation_msg,
                    flow_state=session.flow_state
                )
            else:
                error_msg = "Υπήρξε ένα πρόβλημα κατά την καταχώρηση του αιτήματος. Παρακαλώ περιμένετε να σας συνδέσω με έναν εκπρόσωπο."
                session.add_message("assistant", error_msg)
                return AgentResponse(
                    intent=ticket_intent,
                    response_text=error_msg,
                    flow_state=session.flow_state
                )
        
        elif action == "handoff":
            # Human handoff - collect callback info or provide contact
            slots = action_result.get("slots", {})
            callback_number = slots.get("callback_number")
            preferred_time = slots.get("preferred_time")
            
            if callback_number:
                # Callback requested
                contact_info = store_info.get_contact_info()
                response_text = f"Φυσικά. Θα σας καλέσουμε στο {callback_number}"
                if preferred_time:
                    response_text += f" {preferred_time}"
                response_text += ". Εναλλακτικά, μπορείτε να μας καλέσετε στο "
                response_text += f"{contact_info['phone']} ή να στείλετε email στο {contact_info['email']}."
                
                # Create ticket for tracking
                ticket_details = TicketDetails(
                    title="Αίτημα επικοινωνίας με εκπρόσωπο",
                    description=f"Ο πελάτης ζήτησε να τον καλέσουμε στο {callback_number}. Προτιμημένος χρόνος: {preferred_time or 'Οποιαδήποτε ώρα'}.",
                    category=Category.OTHER,
                    urgency=Urgency.MEDIUM
                )
                result = await github_client.create_ticket(ticket_details, session.phone_number)
                if result:
                    response_text += f" Άνοιξα αίτημα #{result['number']} για παρακολούθηση."
                    session.ticket_id = result["number"]
                    session.ticket_url = result["url"]
            else:
                # Just provide contact info
                contact_info = store_info.get_contact_info()
                response_text = f"Φυσικά. Μπορείτε να μας καλέσετε στο {contact_info['phone']} ή να στείλετε email στο {contact_info['email']}."
                response_text += " Εναλλακτικά, αν θέλετε να σας καλέσουμε εμείς, πείτε μου ένα τηλέφωνο και πότε σας βολεύει (πρωί/απόγευμα)."
                response_text += " Μπορώ επίσης να ανοίξω ένα αίτημα ώστε να σας αναλάβει εκπρόσωπος."
            
            session.add_message("assistant", response_text)
            return AgentResponse(
                intent=intent,
                response_text=response_text,
                flow_state=session.flow_state
            )
        
        else:
            # Default text response
            system_prompt = """Είσαι η ψηφιακή εξυπηρέτηση του καταστήματος RetailCare. 
Μιλάς ΜΟΝΟ Ελληνικά με ευγενικό και επαγγελματικό ύφος."""
            
            messages = [{"role": "system", "content": system_prompt}] + session.conversation_history[-3:]
            
            try:
                response = await self.client.chat.completions.create(
                    model=self.deployment,
                    messages=messages,
                    max_tokens=200
                )
                text = response.choices[0].message.content or ""
                session.add_message("assistant", text)
                clean_text = self._clean_text_for_tts(text)
                return AgentResponse(
                    intent=intent,
                    response_text=clean_text,
                    flow_state=session.flow_state
                )
            except Exception as e:
                logger.error(f"Error generating text response: {e}")
                return AgentResponse(
                    intent=Intent.UNKNOWN,
                    response_text="Με συγχωρείτε, αντιμετωπίζω ένα τεχνικό πρόβλημα. Μπορείτε να επαναλάβετε;",
                    flow_state=session.flow_state
                )

    def _clean_text_for_tts(self, text: str) -> str:
        """Clean text for TTS (remove emojis, markdown, etc.)"""
        clean_text = re.sub(r'[^\w\s\.,!\?\-#]', '', text)
        clean_text = clean_text.replace('*', '').replace('_', '').strip()
        return clean_text

    def _generate_captured_summary(self, intent: Intent, slots: Dict[str, Any]) -> str:
        """Generate a summary of what was captured for the ticket"""
        order_id = slots.get("order_id", "")
        product = slots.get("product", "")
        
        if intent == Intent.ORDER_CANCEL:
            reason = slots.get("reason", "Ακύρωση παραγγελίας")
            return f"Αίτημα ακύρωσης παραγγελίας {order_id if order_id else '(χωρίς αριθμό)'}. Λόγος: {reason}."
        elif intent == Intent.ORDER_CHANGE:
            change_type = slots.get("change_type", "Αλλαγή")
            return f"Αίτημα αλλαγής παραγγελίας {order_id if order_id else '(χωρίς αριθμό)'}. Τύπος αλλαγής: {change_type}."
        elif intent == Intent.REFUND_REQUEST:
            reason = slots.get("reason", "Επιστροφή")
            return f"Αίτημα επιστροφής χρημάτων για παραγγελία {order_id if order_id else '(χωρίς αριθμό)'}. Λόγος: {reason}."
        elif intent == Intent.BAD_EXPERIENCE:
            summary = slots.get("summary", "Κακή εμπειρία")
            return f"Παράπονο για κακή εμπειρία: {summary}"
        else:
            description = slots.get("description", slots.get("summary", "Παράπονο"))
            return f"Παράπονο: {description}"
    
    def _generate_confirmation_message(self, intent: Intent, slots: Dict[str, Any], 
                                      ticket_number: str, missing_info: List[str]) -> str:
        """Generate detailed confirmation message in Greek"""
        order_id = slots.get("order_id", "")
        product = slots.get("product", "")
        
        # Base confirmation
        if order_id:
            base = f"Κατέγραψα ότι η παραγγελία **#{order_id}**"
        else:
            base = "Κατέγραψα το αίτημά σας"
        
        # Intent-specific details
        if intent == Intent.ORDER_CANCEL:
            reason = slots.get("reason", "")
            alternative = slots.get("alternative_offer_accepted", "")
            policy_eligible = slots.get("policy_eligible", True)
            details = f"έχει αίτημα ακύρωσης"
            if reason:
                details += f" (λόγος: {reason})"
            if not policy_eligible and alternative:
                details += f" - Εναλλακτική: {alternative}"
        elif intent == Intent.ORDER_CHANGE:
            change_type = slots.get("change_type", "")
            new_details = slots.get("new_details") or slots.get("new_address") or slots.get("new_item") or slots.get("new_quantity")
            details = f"χρειάζεται αλλαγή"
            if change_type:
                details += f" ({change_type})"
            if new_details:
                details += f": {new_details}"
        elif intent == Intent.REFUND_REQUEST:
            reason = slots.get("reason", "")
            resolution = slots.get("preferred_resolution", "επιστροφή χρημάτων")
            policy_eligible = slots.get("policy_eligible", True)
            details = f"ζητά {resolution}"
            if reason:
                details += f" (λόγος: {reason})"
            if not policy_eligible:
                details += " - Δεν πληροί τις προϋποθέσεις"
        elif intent == Intent.BAD_EXPERIENCE:
            severity = slots.get("severity", "medium")
            summary = slots.get("summary", "Κακή εμπειρία")
            details = f"αναφέρει κακή εμπειρία (βαρύτητα: {severity})"
            if severity == "high":
                details += " - Απαιτείται άμεση ανθρώπινη επέμβαση"
        else:
            description = slots.get("description", slots.get("summary", ""))
            details = description[:50] + "..." if len(description) > 50 else description
        
        # Build message
        msg_parts = [f"{base} {details}."]
        msg_parts.append(f"Άνοιξα αίτημα με αριθμό **#{ticket_number}**.")
        msg_parts.append("Θα λάβεις ενημέρωση μόλις το δει η ομάδα μας.")
        
        # Add missing info request if any
        if missing_info:
            missing_str = ", ".join(missing_info)
            msg_parts.append(f"Για να προχωρήσουμε πιο γρήγορα, μπορείς να μου πεις: **{missing_str}**;")
        
        return " ".join(msg_parts)

    async def _generate_final_answer(self, session: Any, context: str) -> str:
        """Mini-turn to format the FAQ answer naturally"""
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
