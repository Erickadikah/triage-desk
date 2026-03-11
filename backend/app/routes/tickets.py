from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from uuid import UUID
from app.database import get_db
from app.models.ticket import Ticket, TicketStatus, TicketPriority, User
from app.schemas.ticket import TicketCreate, TicketUpdate, TicketResponse, PaginatedTickets
from app.services.ai_service import triage_ticket
from app.middleware.auth import get_current_user
import math

router = APIRouter(prefix="/tickets", tags=["Tickets"])


@router.post("", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket(payload: TicketCreate, db: Session = Depends(get_db)):
    """
    Public endpoint — any customer can submit a ticket.
    Claude automatically assigns category and priority.
    """
    # Run AI triage
    triage_result = await triage_ticket(payload.title, payload.description)

    ticket = Ticket(
        title=payload.title,
        description=payload.description,
        customer_email=payload.customer_email,
        category=triage_result.category,
        priority=triage_result.priority,
        ai_reasoning=triage_result.reasoning,
    )

    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


@router.get("", response_model=PaginatedTickets)
def get_tickets(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    status: Optional[TicketStatus] = Query(default=None),
    priority: Optional[TicketPriority] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Protected endpoint — only authenticated agents can view all tickets.
    Supports filtering by status and priority with pagination.
    """
    query = db.query(Ticket)

    if status:
        query = query.filter(Ticket.status == status)
    if priority:
        query = query.filter(Ticket.priority == priority)

    total = query.count()
    tickets = (
        query
        .order_by(Ticket.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    return PaginatedTickets(
        tickets=tickets,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=math.ceil(total / per_page)
    )


@router.patch("/{ticket_id}", response_model=TicketResponse)
def update_ticket_status(
    ticket_id: UUID,
    payload: TicketUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Protected endpoint — agents can update ticket status.
    """
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()

    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )

    ticket.status = payload.status
    db.commit()
    db.refresh(ticket)
    return ticket


@router.get("/{ticket_id}", response_model=TicketResponse)
def get_ticket(
    ticket_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a single ticket by ID."""
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()

    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )

    return ticket
