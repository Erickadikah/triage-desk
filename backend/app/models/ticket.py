import uuid
import enum
from sqlalchemy import Column, String, Text, Enum, DateTime, func, Uuid
from app.database import Base


class TicketStatus(str, enum.Enum):
    OPEN = "Open"
    IN_PROGRESS = "In Progress"
    RESOLVED = "Resolved"


class TicketPriority(str, enum.Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class TicketCategory(str, enum.Enum):
    BILLING = "Billing"
    TECHNICAL_BUG = "Technical Bug"
    FEATURE_REQUEST = "Feature Request"
    GENERAL = "General"
    ACCOUNT = "Account"


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    customer_email = Column(String(255), nullable=False)
    category = Column(Enum(TicketCategory), nullable=False)
    priority = Column(Enum(TicketPriority), nullable=False, index=True)
    status = Column(Enum(TicketStatus), nullable=False, default=TicketStatus.OPEN, index=True)
    ai_reasoning = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
