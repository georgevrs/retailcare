"""
Unit tests for FAQ knowledge base functionality
"""
import pytest
from src.faq import FAQKnowledgeBase, faq_kb


class TestFAQKnowledgeBase:
    """Test FAQ search and retrieval"""
    
    @pytest.fixture
    def faq(self):
        """Create FAQ instance"""
        return FAQKnowledgeBase()
    
    def test_search_store_hours(self, faq):
        """Test searching for store hours"""
        results = faq.search("ωράριο")
        assert len(results) > 0
        assert any("ωράριο" in r.question.lower() or "09:00" in r.answer for r in results)
    
    def test_search_return_policy(self, faq):
        """Test searching for return policy"""
        results = faq.search("επιστροφών")
        assert len(results) > 0
        assert any("επιστροφ" in r.question.lower() or "14" in r.answer for r in results)
    
    def test_search_delivery(self, faq):
        """Test searching for delivery information"""
        results = faq.search("παράδοση")
        assert len(results) > 0
    
    def test_search_no_results(self, faq):
        """Test search with no matching results"""
        results = faq.search("xyz random query that won't match")
        # Should return empty list or low-scoring results
        assert isinstance(results, list)
    
    def test_search_limit(self, faq):
        """Test search result limit"""
        results = faq.search("ωράριο", limit=1)
        assert len(results) <= 1
    
    def test_faq_result_structure(self, faq):
        """Test that FAQ results have correct structure"""
        results = faq.search("ωράριο")
        if results:
            result = results[0]
            assert hasattr(result, "question")
            assert hasattr(result, "answer")
            assert hasattr(result, "score")
            assert isinstance(result.score, float)
