from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

class Intent(str, Enum):
    COMPLAINT_TICKET = "COMPLAINT_TICKET"
    INFORMATION = "INFORMATION"
    GREETING = "GREETING"
    GOODBYE = "GOODBYE"
    UNKNOWN = "UNKNOWN"

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

class FAQResult(BaseModel):
    question: str
    answer: str
    score: float

class AgentResponse(BaseModel):
    intent: Intent
    response_text: str
    tool_call: Optional[str] = None
    tool_args: Optional[dict] = None
