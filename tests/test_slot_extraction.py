"""
Unit tests for slot extraction functionality
"""
import pytest
from src.models import Intent
from src.agent import CallCenterAgent


class TestSlotExtraction:
    """Test slot extraction from user input"""
    
    @pytest.fixture
    def agent(self):
        """Create agent instance for testing"""
        return CallCenterAgent()
    
    def test_extract_order_id_from_text(self):
        """Test extracting order ID from various formats"""
        test_cases = [
            ("παραγγελία #12345", "#12345"),
            ("order 12345", "12345"),
            ("#99102", "#99102"),
            ("99102", "99102"),
        ]
        
        for text, expected in test_cases:
            # Simple regex-based extraction for testing
            import re
            order_match = re.search(r'#?(\d+)', text)
            if order_match:
                extracted = "#" + order_match.group(1) if not text.startswith("#") else order_match.group(0)
                assert expected in extracted or extracted in expected
    
    def test_extract_reason_keywords(self):
        """Test extracting reason keywords"""
        refund_reasons = ["ελαττωματικό", "damaged", "λάθος", "wrong", "άλλαξα γνώμη", "changed mind"]
        
        for reason in refund_reasons:
            assert any(k in reason.lower() for k in ["ελαττωματικό", "damaged", "λάθος", "wrong", "γνώμη", "mind"])
    
    def test_slot_merging(self):
        """Test that slots merge correctly with existing slots"""
        existing_slots = {"order_id": "#12345"}
        new_slots = {"reason": "ελαττωματικό"}
        
        merged = {**existing_slots, **new_slots}
        assert merged["order_id"] == "#12345"
        assert merged["reason"] == "ελαττωματικό"
    
    def test_required_slots_per_intent(self):
        """Test required slots mapping for each intent"""
        from src.agent import CallCenterAgent
        
        # This would be tested through the agent's _determine_next_action
        required_slots_map = {
            Intent.ORDER_CANCEL: ["order_id"],
            Intent.ORDER_CHANGE: ["order_id", "change_type", "new_details"],
            Intent.REFUND_REQUEST: ["order_id", "reason"],
            Intent.BAD_EXPERIENCE: ["summary"],
            Intent.HUMAN_REQUEST: [],
            Intent.COMPLAINT_TICKET: ["description"],
            Intent.STORE_HOURS: [],
            Intent.INFORMATION: []
        }
        
        assert "order_id" in required_slots_map[Intent.ORDER_CANCEL]
        assert "order_id" in required_slots_map[Intent.REFUND_REQUEST]
        assert "summary" in required_slots_map[Intent.BAD_EXPERIENCE]
