"""
Unit tests for GitHub Issues integration
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.github_issues import GitHubTicketing
from src.models import TicketDetails, Category, Urgency


class TestGitHubTicketing:
    """Test GitHub ticket creation and management"""
    
    @pytest.fixture
    def github_client(self, monkeypatch):
        """Create GitHub client with mocked environment"""
        monkeypatch.setenv("GITHUB_OWNER", "test-owner")
        monkeypatch.setenv("GITHUB_REPO", "test-repo")
        monkeypatch.setenv("GITHUB_TOKEN", "test-token")
        return GitHubTicketing()
    
    def test_ticket_details_creation(self):
        """Test creating ticket details"""
        details = TicketDetails(
            title="Test Issue",
            description="Test description",
            category=Category.DELIVERY,
            urgency=Urgency.HIGH,
            order_id="#12345"
        )
        
        assert details.title == "Test Issue"
        assert details.category == Category.DELIVERY
        assert details.urgency == Urgency.HIGH
        assert details.order_id == "#12345"
    
    @pytest.mark.asyncio
    async def test_create_ticket_success(self, github_client):
        """Test successful ticket creation"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "number": 100,
            "html_url": "https://github.com/test-owner/test-repo/issues/100"
        }
        mock_response.raise_for_status = MagicMock()
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            details = TicketDetails(
                title="Test",
                description="Test description",
                category=Category.OTHER,
                urgency=Urgency.MEDIUM
            )
            
            result = await github_client.create_ticket(details, "306912345678")
            
            assert result is not None
            assert result["number"] == "100"
            assert "github.com" in result["url"]
    
    @pytest.mark.asyncio
    async def test_create_ticket_with_metadata(self, github_client):
        """Test ticket creation with additional metadata"""
        mock_response = MagicMock()
        mock_response.json.return_value = {"number": 101, "html_url": "https://github.com/test/101"}
        mock_response.raise_for_status = MagicMock()
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            details = TicketDetails(
                title="Test",
                description="Test",
                category=Category.REFUND,
                urgency=Urgency.MEDIUM
            )
            
            result = await github_client.create_ticket(
                details,
                "306912345678",
                captured_summary="Test summary",
                missing_info=["order_id"],
                requested_resolution="refund"
            )
            
            assert result is not None
    
    @pytest.mark.asyncio
    async def test_post_comment(self, github_client):
        """Test posting comment to issue"""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            result = await github_client.post_comment(100, "Test comment")
            assert result is True
    
    @pytest.mark.asyncio
    async def test_close_issue(self, github_client):
        """Test closing an issue"""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.patch = AsyncMock(return_value=mock_response)
            
            result = await github_client.close_issue(100)
            assert result is True
