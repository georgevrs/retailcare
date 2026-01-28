"""
Unit tests for text cleaning for TTS
"""
import pytest
from src.agent import CallCenterAgent


class TestTextCleaning:
    """Test text cleaning for TTS"""
    
    @pytest.fixture
    def agent(self):
        """Create agent instance"""
        return CallCenterAgent()
    
    def test_clean_text_removes_markdown(self, agent):
        """Test removing markdown formatting"""
        text = "**Bold** and *italic* text"
        cleaned = agent._clean_text_for_tts(text)
        assert "**" not in cleaned
        assert "*" not in cleaned
    
    def test_clean_text_removes_emojis(self, agent):
        """Test removing emojis"""
        text = "Hello 😊 world 🎉"
        cleaned = agent._clean_text_for_tts(text)
        # Should remove or clean emojis
        assert len(cleaned) < len(text) or "😊" not in cleaned
    
    def test_clean_text_preserves_punctuation(self, agent):
        """Test preserving basic punctuation"""
        text = "Hello, world! How are you?"
        cleaned = agent._clean_text_for_tts(text)
        assert "," in cleaned or "!" in cleaned or "?" in cleaned
    
    def test_clean_text_preserves_greek(self, agent):
        """Test preserving Greek characters"""
        text = "Καλησπέρα! Πώς είστε;"
        cleaned = agent._clean_text_for_tts(text)
        assert "Καλησπέρα" in cleaned
        assert "Πώς" in cleaned
