"""
Tests for golden conversation scenarios
"""
import pytest
import json
from pathlib import Path


class TestGoldenConversations:
    """Test golden conversation scenarios"""
    
    @pytest.fixture
    def golden_dir(self):
        """Get golden conversations directory"""
        return Path(__file__).parent / "golden_conversations"
    
    def test_golden_files_exist(self, golden_dir):
        """Test that all golden conversation files exist"""
        expected_files = [
            "cancellation_flow.json",
            "refund_flow.json",
            "bad_experience_flow.json",
            "human_request_flow.json",
            "store_hours_flow.json"
        ]
        
        for filename in expected_files:
            filepath = golden_dir / filename
            assert filepath.exists(), f"Missing golden file: {filename}"
    
    def test_golden_conversation_structure(self, golden_dir):
        """Test that golden conversations have correct structure"""
        for filepath in golden_dir.glob("*.json"):
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            assert "name" in data
            assert "description" in data
            assert "turns" in data
            assert isinstance(data["turns"], list)
            assert len(data["turns"]) > 0
            
            for turn in data["turns"]:
                assert "user" in turn
                assert "expected_intent" in turn or "expected_action" in turn
    
    def test_cancellation_flow_structure(self, golden_dir):
        """Test cancellation flow structure"""
        filepath = golden_dir / "cancellation_flow.json"
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        assert data["name"] == "Order Cancellation Flow"
        assert len(data["turns"]) >= 2
        assert data["turns"][0]["expected_intent"] == "ORDER_CANCEL"
    
    def test_refund_flow_structure(self, golden_dir):
        """Test refund flow structure"""
        filepath = golden_dir / "refund_flow.json"
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        assert data["name"] == "Refund Request Flow"
        assert len(data["turns"]) >= 3
        assert data["turns"][0]["expected_intent"] == "REFUND_REQUEST"
