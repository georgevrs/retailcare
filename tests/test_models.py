"""
Unit tests for data models
"""
import pytest
from src.models import (
    Intent, Urgency, Category, TicketDetails, 
    FAQResult, Slot, FlowState, AgentResponse
)


class TestModels:
    """Test data model validation and structure"""
    
    def test_intent_enum(self):
        """Test Intent enum values"""
        assert Intent.ORDER_CANCEL == "ORDER_CANCEL"
        assert Intent.REFUND_REQUEST == "REFUND_REQUEST"
        assert Intent.STORE_HOURS == "STORE_HOURS"
    
    def test_urgency_enum(self):
        """Test Urgency enum"""
        assert Urgency.LOW == "low"
        assert Urgency.MEDIUM == "medium"
        assert Urgency.HIGH == "high"
    
    def test_category_enum(self):
        """Test Category enum"""
        assert Category.DELIVERY == "delivery"
        assert Category.REFUND == "refund"
        assert Category.OTHER == "other"
    
    def test_ticket_details_creation(self):
        """Test TicketDetails model creation"""
        ticket = TicketDetails(
            title="Test Title",
            description="Test Description",
            category=Category.DELIVERY,
            urgency=Urgency.HIGH
        )
        
        assert ticket.title == "Test Title"
        assert ticket.category == Category.DELIVERY
        assert ticket.urgency == Urgency.HIGH
        assert ticket.order_id is None
    
    def test_ticket_details_with_optional_fields(self):
        """Test TicketDetails with optional fields"""
        ticket = TicketDetails(
            title="Test",
            description="Test",
            category=Category.OTHER,
            urgency=Urgency.MEDIUM,
            order_id="#123",
            product="Test Product",
            store="Athens"
        )
        
        assert ticket.order_id == "#123"
        assert ticket.product == "Test Product"
        assert ticket.store == "Athens"
    
    def test_faq_result(self):
        """Test FAQResult model"""
        result = FAQResult(
            question="Test question?",
            answer="Test answer",
            score=0.95
        )
        
        assert result.question == "Test question?"
        assert result.answer == "Test answer"
        assert result.score == 0.95
    
    def test_slot_model(self):
        """Test Slot model"""
        slot = Slot(
            name="order_id",
            value="#12345",
            confidence=0.9,
            required=True
        )
        
        assert slot.name == "order_id"
        assert slot.value == "#12345"
        assert slot.confidence == 0.9
        assert slot.required is True
    
    def test_flow_state_model(self):
        """Test FlowState model"""
        flow = FlowState(
            active_intent=Intent.REFUND_REQUEST,
            slots={"order_id": "#123"},
            missing_slots=["reason"],
            next_question="Ποιος είναι ο λόγος;",
            last_action="asked_question"
        )
        
        assert flow.active_intent == Intent.REFUND_REQUEST
        assert flow.slots["order_id"] == "#123"
        assert "reason" in flow.missing_slots
        assert flow.next_question is not None
    
    def test_agent_response_model(self):
        """Test AgentResponse model"""
        response = AgentResponse(
            intent=Intent.INFORMATION,
            response_text="Test response",
            tool_call="search_faq",
            tool_args={"query": "test"}
        )
        
        assert response.intent == Intent.INFORMATION
        assert response.response_text == "Test response"
        assert response.tool_call == "search_faq"
        assert response.tool_args["query"] == "test"
