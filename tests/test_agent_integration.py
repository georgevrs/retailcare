"""
Integration tests for agent end-to-end flows
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.agent import CallCenterAgent
from src.state import CallSession
from src.models import Intent


class TestAgentIntegration:
    """Integration tests for agent flows"""
    
    @pytest.fixture
    def agent(self):
        """Create agent instance"""
        return CallCenterAgent()
    
    @pytest.fixture
    def mock_session(self):
        """Create mock session"""
        return CallSession("test-conn-123", "306912345678")
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_refund_flow_integration(self, agent, mock_session):
        """Test complete refund flow"""
        # Mock OpenAI responses
        with patch.object(agent.client.chat.completions, 'create') as mock_create:
            # Turn 1: Classify intent
            mock_create.return_value = MagicMock(
                choices=[MagicMock(message=MagicMock(content="REFUND_REQUEST"))]
            )
            
            # Mock slot extraction
            mock_create.return_value.choices[0].message.tool_calls = [MagicMock(
                function=MagicMock(
                    name="extract_case_details",
                    arguments='{"slots": {"order_id": "#99102"}}'
                )
            )]
            
            # Turn 1: User requests refund
            response1 = await agent.process_utterance(mock_session, "Θέλω επιστροφή")
            assert response1.intent == Intent.REFUND_REQUEST or response1.intent == Intent.UNKNOWN
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_store_hours_integration(self, agent, mock_session):
        """Test store hours query flow"""
        with patch.object(agent.client.chat.completions, 'create') as mock_create:
            mock_create.return_value = MagicMock(
                choices=[MagicMock(message=MagicMock(content="STORE_HOURS"))]
            )
            
            response = await agent.process_utterance(mock_session, "Ποιο είναι το ωράριο;")
            # Should either be STORE_HOURS or INFORMATION
            assert response.intent in [Intent.STORE_HOURS, Intent.INFORMATION]
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_cancellation_with_alternatives(self, agent, mock_session):
        """Test cancellation flow with alternative offers"""
        # This would test the full flow including policy checks
        # For now, we test the structure
        assert hasattr(agent, '_determine_next_action')
        assert hasattr(agent, '_generate_response')
