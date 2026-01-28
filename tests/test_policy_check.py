"""
Unit tests for policy engine functionality
"""
import pytest
from src.policy_engine import PolicyEngine, policy_engine


class TestPolicyEngine:
    """Test policy checking logic"""
    
    @pytest.fixture
    def engine(self):
        """Create policy engine instance"""
        return PolicyEngine()
    
    def test_refund_policy_changed_mind_eligible(self, engine):
        """Test refund policy for changed mind - eligible case"""
        slots = {
            "reason": "άλλαξα γνώμη",
            "days_since_delivery": 5,
            "condition": "unopened"
        }
        
        result = engine.check_policy("refund", slots)
        assert result["eligible"] is True
        assert result["eligible_days"] == 14
    
    def test_refund_policy_changed_mind_too_late(self, engine):
        """Test refund policy for changed mind - too late"""
        slots = {
            "reason": "άλλαξα γνώμη",
            "days_since_delivery": 20,
            "condition": "unopened"
        }
        
        result = engine.check_policy("refund", slots)
        assert result["eligible"] is False
        assert "14 ημερών" in result["next_steps_text_el"] or "14" in result["next_steps_text_el"]
    
    def test_refund_policy_damaged_requires_photo(self, engine):
        """Test refund policy for damaged product - requires photo"""
        slots = {
            "reason": "ελαττωματικό",
            "days_since_delivery": 2
        }
        
        result = engine.check_policy("refund", slots)
        assert "φωτογραφία" in result["next_steps_text_el"].lower() or "photo" in result["what_we_need"][0].lower() if result["what_we_need"] else False
    
    def test_refund_policy_wrong_item(self, engine):
        """Test refund policy for wrong item"""
        slots = {
            "reason": "λάθος προϊόν",
            "days_since_delivery": 3
        }
        
        result = engine.check_policy("refund", slots)
        assert result["eligible_days"] == 7
    
    def test_cancellation_policy_before_shipment(self, engine):
        """Test cancellation policy - before shipment"""
        slots = {
            "shipment_status": "pending"
        }
        
        result = engine.check_policy("cancellation", slots)
        assert result["eligible"] is True
        assert "μπορεί να γίνει" in result["next_steps_text_el"].lower()
    
    def test_cancellation_policy_after_shipment(self, engine):
        """Test cancellation policy - after shipment"""
        slots = {
            "shipment_status": "shipped"
        }
        
        result = engine.check_policy("cancellation", slots)
        assert result["eligible"] is False
        assert "alternative" in result or "εναλλακτικά" in result["next_steps_text_el"].lower()
    
    def test_policy_unknown_key(self, engine):
        """Test policy check with unknown policy key"""
        slots = {"test": "value"}
        result = engine.check_policy("unknown_policy", slots)
        assert result["eligible"] is True  # Defaults to eligible
        assert "εξετάσουμε" in result["next_steps_text_el"].lower()
