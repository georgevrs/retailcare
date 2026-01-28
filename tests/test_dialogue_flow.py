"""
Unit tests for dialogue flow and next question generation
"""
import pytest
from src.models import Intent, FlowState
from src.agent import CallCenterAgent


class TestDialogueFlow:
    """Test dialogue flow logic"""
    
    @pytest.fixture
    def agent(self):
        """Create agent instance"""
        return CallCenterAgent()
    
    def test_generate_next_question_order_cancel(self, agent):
        """Test generating next question for order cancellation"""
        question = agent._generate_next_question(
            Intent.ORDER_CANCEL,
            "order_id",
            {}
        )
        assert "αριθμός παραγγελίας" in question.lower() or "order" in question.lower()
    
    def test_generate_next_question_refund_reason(self, agent):
        """Test generating next question for refund reason"""
        question = agent._generate_next_question(
            Intent.REFUND_REQUEST,
            "reason",
            {}
        )
        assert "λόγος" in question.lower() or "reason" in question.lower()
    
    def test_generate_next_question_order_change_type(self, agent):
        """Test generating next question for order change type"""
        question = agent._generate_next_question(
            Intent.ORDER_CHANGE,
            "change_type",
            {}
        )
        assert "αλλάξεις" in question.lower() or "change" in question.lower()
    
    def test_generate_next_question_order_change_address(self, agent):
        """Test generating next question for address change"""
        question = agent._generate_next_question(
            Intent.ORDER_CHANGE,
            "new_address",
            {"change_type": "διεύθυνση"}
        )
        assert "διεύθυνση" in question.lower() or "address" in question.lower()
    
    def test_determine_missing_slots(self):
        """Test determining which slots are missing"""
        required_slots = ["order_id", "reason"]
        existing_slots = {"order_id": "#123"}
        
        missing = [s for s in required_slots if not existing_slots.get(s)]
        assert missing == ["reason"]
    
    def test_flow_state_initialization(self):
        """Test flow state initialization"""
        flow_state = FlowState(
            active_intent=Intent.REFUND_REQUEST,
            slots={"order_id": "#123"},
            missing_slots=["reason"],
            next_question="Ποιος είναι ο λόγος;",
            last_action="asked_question"
        )
        
        assert flow_state.active_intent == Intent.REFUND_REQUEST
        assert flow_state.slots["order_id"] == "#123"
        assert "reason" in flow_state.missing_slots
        assert flow_state.next_question is not None
