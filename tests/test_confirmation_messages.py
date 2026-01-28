"""
Unit tests for confirmation message generation
"""
import pytest
from src.models import Intent
from src.agent import CallCenterAgent


class TestConfirmationMessages:
    """Test confirmation message generation"""
    
    @pytest.fixture
    def agent(self):
        """Create agent instance"""
        return CallCenterAgent()
    
    def test_generate_captured_summary_cancellation(self, agent):
        """Test generating captured summary for cancellation"""
        slots = {
            "order_id": "#77881",
            "reason": "Άργησε"
        }
        summary = agent._generate_captured_summary(Intent.ORDER_CANCEL, slots)
        assert "#77881" in summary or "77881" in summary
        assert "ακύρωση" in summary.lower()
    
    def test_generate_captured_summary_refund(self, agent):
        """Test generating captured summary for refund"""
        slots = {
            "order_id": "#99102",
            "reason": "Ελαττωματικό"
        }
        summary = agent._generate_captured_summary(Intent.REFUND_REQUEST, slots)
        assert "#99102" in summary or "99102" in summary
        assert "επιστροφή" in summary.lower()
    
    def test_generate_confirmation_message_cancellation(self, agent):
        """Test generating confirmation message for cancellation"""
        slots = {
            "order_id": "#77881",
            "reason": "Άργησε"
        }
        message = agent._generate_confirmation_message(
            Intent.ORDER_CANCEL,
            slots,
            "104",
            []
        )
        assert "#77881" in message or "77881" in message
        assert "#104" in message or "104" in message
        assert "αίτημα" in message.lower()
    
    def test_generate_confirmation_message_with_missing_info(self, agent):
        """Test confirmation message with missing information"""
        slots = {"order_id": "#12345"}
        missing_info = ["ονοματεπώνυμο"]
        
        message = agent._generate_confirmation_message(
            Intent.COMPLAINT_TICKET,
            slots,
            "105",
            missing_info
        )
        assert "#105" in message or "105" in message
        assert "ονοματεπώνυμο" in message.lower() or any(m in message for m in missing_info)
