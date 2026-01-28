"""
Unit tests for intent classification functionality
"""
import pytest
from src.models import Intent
from src.agent import CallCenterAgent


class TestIntentClassification:
    """Test intent classification logic"""
    
    @pytest.fixture
    def agent(self):
        """Create agent instance for testing"""
        return CallCenterAgent()
    
    def test_classify_intent_fallback_cancellation(self, agent):
        """Test cancellation intent detection"""
        assert agent._classify_intent_fallback("Θέλω ακύρωση") == Intent.ORDER_CANCEL
        assert agent._classify_intent_fallback("θέλω να ακυρώσω") == Intent.ORDER_CANCEL
        assert agent._classify_intent_fallback("cancel order") == Intent.ORDER_CANCEL
    
    def test_classify_intent_fallback_order_change(self, agent):
        """Test order change intent detection"""
        assert agent._classify_intent_fallback("θέλω αλλαγή") == Intent.ORDER_CHANGE
        assert agent._classify_intent_fallback("change address") == Intent.ORDER_CHANGE
        assert agent._classify_intent_fallback("μεταβολή παραγγελίας") == Intent.ORDER_CHANGE
    
    def test_classify_intent_fallback_refund(self, agent):
        """Test refund intent detection"""
        assert agent._classify_intent_fallback("θέλω επιστροφή") == Intent.REFUND_REQUEST
        assert agent._classify_intent_fallback("refund") == Intent.REFUND_REQUEST
        assert agent._classify_intent_fallback("επιστρέψω χρήματα") == Intent.REFUND_REQUEST
    
    def test_classify_intent_fallback_store_hours(self, agent):
        """Test store hours intent detection"""
        assert agent._classify_intent_fallback("ποιο είναι το ωράριο") == Intent.STORE_HOURS
        assert agent._classify_intent_fallback("τι ώρες είστε ανοιχτά") == Intent.STORE_HOURS
        assert agent._classify_intent_fallback("ανοιχτά") == Intent.STORE_HOURS
    
    def test_classify_intent_fallback_human_request(self, agent):
        """Test human request intent detection"""
        assert agent._classify_intent_fallback("θέλω άνθρωπο") == Intent.HUMAN_REQUEST
        assert agent._classify_intent_fallback("human") == Intent.HUMAN_REQUEST
        assert agent._classify_intent_fallback("εκπρόσωπος") == Intent.HUMAN_REQUEST
    
    def test_classify_intent_fallback_bad_experience(self, agent):
        """Test bad experience intent detection"""
        assert agent._classify_intent_fallback("αγενής") == Intent.BAD_EXPERIENCE
        assert agent._classify_intent_fallback("κακή εμπειρία") == Intent.BAD_EXPERIENCE
        assert agent._classify_intent_fallback("ποτέ ξανά") == Intent.BAD_EXPERIENCE
    
    def test_classify_intent_fallback_complaint(self, agent):
        """Test complaint intent detection"""
        assert agent._classify_intent_fallback("έχω πρόβλημα") == Intent.COMPLAINT_TICKET
        assert agent._classify_intent_fallback("παράπονο") == Intent.COMPLAINT_TICKET
        assert agent._classify_intent_fallback("καθυστέρηση") == Intent.COMPLAINT_TICKET
    
    def test_classify_intent_fallback_information(self, agent):
        """Test information intent detection"""
        assert agent._classify_intent_fallback("τι είναι;") == Intent.INFORMATION
        assert agent._classify_intent_fallback("πώς;") == Intent.INFORMATION
        assert agent._classify_intent_fallback("ποιο;") == Intent.INFORMATION
    
    def test_classify_intent_fallback_greeting(self, agent):
        """Test greeting intent detection"""
        assert agent._classify_intent_fallback("γεια σας") == Intent.GREETING
        assert agent._classify_intent_fallback("χαίρετε") == Intent.GREETING
        assert agent._classify_intent_fallback("καλησπέρα") == Intent.GREETING
    
    def test_classify_intent_fallback_goodbye(self, agent):
        """Test goodbye intent detection"""
        assert agent._classify_intent_fallback("αντίο") == Intent.GOODBYE
        assert agent._classify_intent_fallback("ευχαριστώ") == Intent.GOODBYE
        assert agent._classify_intent_fallback("bye") == Intent.GOODBYE
    
    def test_classify_intent_fallback_unknown(self, agent):
        """Test unknown intent fallback"""
        assert agent._classify_intent_fallback("xyz random text") == Intent.UNKNOWN
