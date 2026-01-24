import time
import json
import os
import logging
import tempfile
from typing import Dict, List, Any, Optional
from src.models import Intent, TicketDetails

logger = logging.getLogger(__name__)

class CallSession:
    # ... (rest of CallSession remains same)
    def __init__(self, call_connection_id: str, phone_number: str = "unknown"):
        self.call_connection_id = call_connection_id
        self.phone_number = phone_number
        self.created_at = time.time()
        self.conversation_history: List[Dict[str, str]] = []
        self.last_intent: Intent = Intent.UNKNOWN
        self.collected_slots: Dict[str, Any] = {}
        self.ticket_id: Optional[str] = None
        self.ticket_url: Optional[str] = None
        self.greeting_triggered: bool = False

    def add_message(self, role: str, content: str):
        self.conversation_history.append({"role": role, "content": content})

    def to_dict(self):
        return {
            "call_connection_id": self.call_connection_id,
            "phone_number": self.phone_number,
            "created_at": self.created_at,
            "conversation_history": self.conversation_history,
            "last_intent": self.last_intent.value if isinstance(self.last_intent, Intent) else self.last_intent,
            "collected_slots": self.collected_slots,
            "ticket_id": self.ticket_id,
            "ticket_url": self.ticket_url,
            "greeting_triggered": self.greeting_triggered
        }

    @classmethod
    def from_dict(cls, data):
        session = cls(data["call_connection_id"], data["phone_number"])
        session.created_at = data.get("created_at", time.time())
        session.conversation_history = data.get("conversation_history", [])
        session.last_intent = Intent(data.get("last_intent", "UNKNOWN"))
        session.collected_slots = data.get("collected_slots", {})
        session.ticket_id = data.get("ticket_id")
        session.ticket_url = data.get("ticket_url")
        session.greeting_triggered = data.get("greeting_triggered", False)
        return session

class SessionStore:
    def __init__(self, storage_dir: str = "retailcare_sessions"):
        # Use temp directory for cross-platform/Azure compatibility
        self.storage_dir = os.path.join(tempfile.gettempdir(), storage_dir)
            
        try:
            os.makedirs(self.storage_dir, exist_ok=True)
            logger.info(f"Session store initialized at: {self.storage_dir}")
            # Test write access
            test_file = os.path.join(self.storage_dir, ".write_test")
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
        except Exception as e:
            logger.error(f"CRITICAL: Session directory {self.storage_dir} not writable: {e}")
            # Extreme fallback
            self.storage_dir = tempfile.gettempdir()

    def _get_path(self, conn_id: str):
        # Sanitize filename
        safe_id = "".join([c for c in conn_id if c.isalnum() or c in ("-", "_")])
        return os.path.join(self.storage_dir, f"{safe_id}.json")

    def get_or_create_session(self, call_connection_id: str, phone_number: str = "unknown") -> CallSession:
        path = self._get_path(call_connection_id)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return CallSession.from_dict(json.load(f))
            except Exception as e:
                logger.error(f"Error loading session {call_connection_id}: {e}")
        
        # Create new if not found or error
        session = CallSession(call_connection_id, phone_number)
        self.save_session(session)
        return session

    def save_session(self, session: CallSession):
        path = self._get_path(session.call_connection_id)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(session.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving session {session.call_connection_id}: {e}")

    def delete_session(self, call_connection_id: str):
        path = self._get_path(call_connection_id)
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception as e:
                logger.error(f"Error deleting session {call_connection_id}: {e}")

# Singleton instance for the app
session_store = SessionStore()
