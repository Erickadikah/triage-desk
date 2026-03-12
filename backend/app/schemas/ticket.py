from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from uuid import UUID
from datetime import datetime
from app.models.ticket import TicketStatus, TicketPriority, TicketCategory


class TicketCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    description: str = Field(..., min_length=10)
    customer_email: EmailStr


class TicketUpdate(BaseModel):
    status: TicketStatus


class TicketResponse(BaseModel):
    id: UUID
    title: str
    description: str
    customer_email: str
    category: TicketCategory
    priority: TicketPriority
    status: TicketStatus
    ai_reasoning: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PaginatedTickets(BaseModel):
    tickets: list[TicketResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class AITriageResult(BaseModel):
    category: TicketCategory
    priority: TicketPriority
    reasoning: str
