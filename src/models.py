from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class Intent(str, Enum):
    COMPLAINT_TICKET = "COMPLAINT_TICKET"
    INFORMATION = "INFORMATION"
    GREETING = "GREETING"
    GOODBYE = "GOODBYE"
    UNKNOWN = "UNKNOWN"
    ORDER_CANCEL = "ORDER_CANCEL"
    ORDER_CHANGE = "ORDER_CHANGE"
    REFUND_REQUEST = "REFUND_REQUEST"
    BAD_EXPERIENCE = "BAD_EXPERIENCE"
    HUMAN_REQUEST = "HUMAN_REQUEST"
    STORE_HOURS = "STORE_HOURS"

class Urgency(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class Category(str, Enum):
    DELIVERY = "delivery"
    REFUND = "refund"
    BILLING = "billing"
    WARRANTY = "warranty"
    PRODUCT = "product"
    OTHER = "other"

class TicketDetails(BaseModel):
    title: str = Field(..., description="A short summary of the issue in Greek")
    description: str = Field(..., description="Detailed description of the problem in Greek")
    category: Category = Field(Category.OTHER, description="The category of the complaint")
    urgency: Urgency = Field(Urgency.MEDIUM, description="The urgency of the ticket")
    order_id: Optional[str] = Field(None, description="The order ID if provided")
    product: Optional[str] = Field(None, description="The product name if mentioned")
    store: Optional[str] = Field(None, description="The store location if mentioned")
    extra_labels: Optional[List[str]] = Field(None, description="Additional labels for the ticket")

class FAQResult(BaseModel):
    question: str
    answer: str
    score: float

class Slot(BaseModel):
    name: str
    value: Any
    confidence: float = 1.0
    required: bool = True

class FlowState(BaseModel):
    active_intent: Optional[Intent] = None
    slots: Dict[str, Any] = Field(default_factory=dict)
    missing_slots: List[str] = Field(default_factory=list)
    next_question: Optional[str] = None
    confirmation_summary: Optional[str] = None
    last_action: str = ""  # "asked_question", "created_ticket", "answered_faq", "handoff_attempted"

class AgentResponse(BaseModel):
    intent: Intent
    response_text: str
    tool_call: Optional[str] = None
    tool_args: Optional[dict] = None
    flow_state: Optional[FlowState] = None
