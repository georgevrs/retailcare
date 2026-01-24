import time
from typing import Dict, List, Any, Optional
from src.models import Intent, TicketDetails

class CallSession:
    def __init__(self, call_connection_id: str, phone_number: str = "unknown"):
        self.call_connection_id = call_connection_id
        self.phone_number = phone_number
        self.created_at = time.time()
        self.conversation_history: List[Dict[str, str]] = []
        self.last_intent: Intent = Intent.UNKNOWN
        self.collected_slots: Dict[str, Any] = {}
        self.ticket_id: Optional[str] = None
        self.ticket_url: Optional[str] = None

    def add_message(self, role: str, content: str):
        self.conversation_history.append({"role": role, "content": content})

class SessionStore:
    def __init__(self):
        # In-memory store for demo purposes
        self._sessions: Dict[str, CallSession] = {}

    def get_or_create_session(self, call_connection_id: str, phone_number: str = "unknown") -> CallSession:
        if call_connection_id not in self._sessions:
            self._sessions[call_connection_id] = CallSession(call_connection_id, phone_number)
        return self._sessions[call_connection_id]

    def delete_session(self, call_connection_id: str):
        if call_connection_id in self._sessions:
            del self._sessions[call_connection_id]

# Singleton instance for the app
session_store = SessionStore()
