"""
Unit tests for session state management
"""
import pytest
from src.state import CallSession, SessionStore
from src.models import Intent, FlowState


class TestCallSession:
    """Test CallSession functionality"""
    
    def test_session_creation(self):
        """Test creating a new session"""
        session = CallSession("test-conn-123", "306912345678")
        assert session.call_connection_id == "test-conn-123"
        assert session.phone_number == "306912345678"
        assert len(session.conversation_history) == 0
        assert session.last_intent == Intent.UNKNOWN
    
    def test_add_message(self):
        """Test adding messages to conversation history"""
        session = CallSession("test-123")
        session.add_message("user", "Γεια σας")
        session.add_message("assistant", "Καλησπέρα!")
        
        assert len(session.conversation_history) == 2
        assert session.conversation_history[0]["role"] == "user"
        assert session.conversation_history[1]["role"] == "assistant"
    
    def test_session_to_dict(self):
        """Test session serialization"""
        session = CallSession("test-123", "306912345678")
        session.add_message("user", "test")
        session.ticket_id = "100"
        
        data = session.to_dict()
        assert data["call_connection_id"] == "test-123"
        assert data["phone_number"] == "306912345678"
        assert data["ticket_id"] == "100"
        assert len(data["conversation_history"]) == 1
    
    def test_session_from_dict(self):
        """Test session deserialization"""
        data = {
            "call_connection_id": "test-123",
            "phone_number": "306912345678",
            "created_at": 1234567890,
            "conversation_history": [{"role": "user", "content": "test"}],
            "last_intent": "INFORMATION",
            "collected_slots": {},
            "ticket_id": "100",
            "ticket_url": "https://example.com/100",
            "greeting_triggered": True,
            "active_intent": "REFUND_REQUEST",
            "flow_state": {
                "active_intent": "REFUND_REQUEST",
                "slots": {"order_id": "#123"},
                "missing_slots": ["reason"],
                "next_question": "Ποιος είναι ο λόγος;",
                "confirmation_summary": None,
                "last_action": "asked_question"
            },
            "last_agent_action": "asked_question"
        }
        
        session = CallSession.from_dict(data)
        assert session.call_connection_id == "test-123"
        assert session.ticket_id == "100"
        assert len(session.conversation_history) == 1
        assert session.active_intent == Intent.REFUND_REQUEST
        assert session.flow_state is not None
        assert session.flow_state.slots["order_id"] == "#123"
    
    def test_flow_state_persistence(self):
        """Test that flow state persists correctly"""
        session = CallSession("test-123")
        session.active_intent = Intent.REFUND_REQUEST
        session.flow_state = FlowState(
            active_intent=Intent.REFUND_REQUEST,
            slots={"order_id": "#123"},
            missing_slots=["reason"],
            next_question="Ποιος είναι ο λόγος;",
            last_action="asked_question"
        )
        
        data = session.to_dict()
        assert data["active_intent"] == "REFUND_REQUEST"
        assert data["flow_state"]["slots"]["order_id"] == "#123"
        
        # Restore
        restored = CallSession.from_dict(data)
        assert restored.flow_state.slots["order_id"] == "#123"
        assert restored.flow_state.missing_slots == ["reason"]


class TestSessionStore:
    """Test SessionStore functionality"""
    
    @pytest.fixture
    def store(self, tmp_path):
        """Create session store with temp directory"""
        import os
        import tempfile
        temp_dir = tmp_path / "sessions"
        temp_dir.mkdir()
        
        # Create store with custom directory
        store = SessionStore()
        store.storage_dir = str(temp_dir)
        return store
    
    def test_get_or_create_session_new(self, store):
        """Test creating a new session"""
        session = store.get_or_create_session("new-conn-123", "306912345678")
        assert session.call_connection_id == "new-conn-123"
        assert session.phone_number == "306912345678"
    
    def test_save_and_load_session(self, store):
        """Test saving and loading a session"""
        session = CallSession("test-123", "306912345678")
        session.add_message("user", "test message")
        session.ticket_id = "100"
        
        store.save_session(session)
        
        loaded = store.get_or_create_session("test-123")
        assert loaded.phone_number == "306912345678"
        assert len(loaded.conversation_history) == 1
        assert loaded.ticket_id == "100"
    
    def test_delete_session(self, store):
        """Test deleting a session"""
        session = CallSession("delete-test-123")
        store.save_session(session)
        
        store.delete_session("delete-test-123")
        
        # Should create new session when loading deleted one
        new_session = store.get_or_create_session("delete-test-123")
        assert len(new_session.conversation_history) == 0
