import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.schemas.ticket import AITriageResult
from app.models.ticket import TicketCategory, TicketPriority

# SQLite test database
TEST_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_triage():
    result = AITriageResult(
        category=TicketCategory.TECHNICAL_BUG,
        priority=TicketPriority.HIGH,
        reasoning="Test triage reasoning",
    )
    with patch(
        "app.routes.tickets.triage_ticket", new_callable=AsyncMock, return_value=result
    ) as mock:
        yield mock


def register_user(client, email="agent@test.com", password="testpassword123", full_name="Test Agent"):
    return client.post("/auth/register", json={
        "email": email,
        "password": password,
        "full_name": full_name,
    })


def login_user(client, email="agent@test.com", password="testpassword123"):
    return client.post("/auth/login", json={
        "email": email,
        "password": password,
    })


def auth_header(client):
    register_user(client)
    resp = login_user(client)
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# --- Health ---

def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


# --- Auth ---

def test_register_success(client):
    resp = register_user(client)
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "agent@test.com"
    assert "id" in data
    assert "hashed_password" not in data


def test_register_duplicate_email(client):
    register_user(client)
    resp = register_user(client)
    assert resp.status_code == 409


def test_register_short_password(client):
    resp = client.post("/auth/register", json={
        "email": "a@b.com",
        "password": "short",
        "full_name": "Test",
    })
    assert resp.status_code == 422


def test_register_invalid_email(client):
    resp = client.post("/auth/register", json={
        "email": "not-an-email",
        "password": "testpassword123",
        "full_name": "Test",
    })
    assert resp.status_code == 422


def test_login_success(client):
    register_user(client)
    resp = login_user(client)
    assert resp.status_code == 200
    assert "access_token" in resp.json()
    assert resp.json()["token_type"] == "bearer"


def test_login_wrong_password(client):
    register_user(client)
    resp = login_user(client, password="wrongpassword")
    assert resp.status_code == 401


def test_login_nonexistent_user(client):
    resp = login_user(client, email="nobody@test.com")
    assert resp.status_code == 401


# --- Create Ticket (public) ---

def test_create_ticket(client, mock_triage):
    resp = client.post("/tickets", json={
        "title": "App crashes on login",
        "description": "The application crashes every time I try to log in with my credentials.",
        "customer_email": "customer@example.com",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "App crashes on login"
    assert data["category"] == "Technical Bug"
    assert data["priority"] == "High"
    assert data["status"] == "Open"
    assert data["ai_reasoning"] == "Test triage reasoning"
    mock_triage.assert_called_once()


def test_create_ticket_validation_error(client, mock_triage):
    resp = client.post("/tickets", json={
        "title": "Hi",
        "description": "Short",
        "customer_email": "bad-email",
    })
    assert resp.status_code == 422
    mock_triage.assert_not_called()


def test_create_ticket_missing_fields(client, mock_triage):
    resp = client.post("/tickets", json={"title": "Something"})
    assert resp.status_code == 422


# --- Get Tickets (protected) ---

def test_get_tickets_unauthorized(client):
    resp = client.get("/tickets")
    assert resp.status_code == 403


def test_get_tickets_invalid_token(client):
    resp = client.get("/tickets", headers={"Authorization": "Bearer invalid-token"})
    assert resp.status_code == 401


def test_get_tickets_success(client, mock_triage):
    headers = auth_header(client)

    # Create some tickets
    for i in range(3):
        client.post("/tickets", json={
            "title": f"Ticket {i} - bug report",
            "description": f"Detailed description of ticket number {i} with enough length.",
            "customer_email": f"user{i}@example.com",
        })

    resp = client.get("/tickets", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert len(data["tickets"]) == 3
    assert data["page"] == 1


def test_get_tickets_pagination(client, mock_triage):
    headers = auth_header(client)

    for i in range(5):
        client.post("/tickets", json={
            "title": f"Ticket {i} - issue found",
            "description": f"Detailed description of ticket number {i} for pagination test.",
            "customer_email": f"user{i}@example.com",
        })

    resp = client.get("/tickets?page=1&per_page=2", headers=headers)
    data = resp.json()
    assert len(data["tickets"]) == 2
    assert data["total"] == 5
    assert data["total_pages"] == 3


def test_get_tickets_filter_by_status(client, mock_triage):
    headers = auth_header(client)

    client.post("/tickets", json={
        "title": "Filter test ticket here",
        "description": "This is a ticket to test filtering by status works correctly.",
        "customer_email": "filter@example.com",
    })

    resp = client.get("/tickets?status=Open", headers=headers)
    data = resp.json()
    assert data["total"] >= 1
    assert all(t["status"] == "Open" for t in data["tickets"])


def test_get_tickets_filter_by_priority(client, mock_triage):
    headers = auth_header(client)

    client.post("/tickets", json={
        "title": "Priority filter test item",
        "description": "This is a ticket to test filtering by priority works correctly.",
        "customer_email": "priority@example.com",
    })

    resp = client.get("/tickets?priority=High", headers=headers)
    data = resp.json()
    assert data["total"] >= 1
    assert all(t["priority"] == "High" for t in data["tickets"])


# --- Update Ticket (protected) ---

def test_update_ticket_status(client, mock_triage):
    headers = auth_header(client)

    create_resp = client.post("/tickets", json={
        "title": "Ticket to update status",
        "description": "We will update the status of this ticket in the test.",
        "customer_email": "update@example.com",
    })
    ticket_id = create_resp.json()["id"]

    resp = client.patch(f"/tickets/{ticket_id}", json={"status": "In Progress"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "In Progress"


def test_update_ticket_resolved(client, mock_triage):
    headers = auth_header(client)

    create_resp = client.post("/tickets", json={
        "title": "Ticket to resolve fully",
        "description": "We will resolve this ticket completely in the test case.",
        "customer_email": "resolve@example.com",
    })
    ticket_id = create_resp.json()["id"]

    resp = client.patch(f"/tickets/{ticket_id}", json={"status": "Resolved"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "Resolved"


def test_update_ticket_unauthorized(client, mock_triage):
    create_resp = client.post("/tickets", json={
        "title": "Unauthorized update test ticket",
        "description": "Trying to update without authentication should fail.",
        "customer_email": "noauth@example.com",
    })
    ticket_id = create_resp.json()["id"]

    resp = client.patch(f"/tickets/{ticket_id}", json={"status": "Resolved"})
    assert resp.status_code == 403


def test_update_ticket_not_found(client, mock_triage):
    headers = auth_header(client)
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = client.patch(f"/tickets/{fake_id}", json={"status": "Resolved"}, headers=headers)
    assert resp.status_code == 404


def test_update_ticket_invalid_status(client, mock_triage):
    headers = auth_header(client)

    create_resp = client.post("/tickets", json={
        "title": "Invalid status update test",
        "description": "Trying to set an invalid status value should fail validation.",
        "customer_email": "invalid@example.com",
    })
    ticket_id = create_resp.json()["id"]

    resp = client.patch(f"/tickets/{ticket_id}", json={"status": "Deleted"}, headers=headers)
    assert resp.status_code == 422


# --- Get Single Ticket ---

def test_get_single_ticket(client, mock_triage):
    headers = auth_header(client)

    create_resp = client.post("/tickets", json={
        "title": "Single ticket fetch test",
        "description": "Fetching a single ticket by its ID should return correct data.",
        "customer_email": "single@example.com",
    })
    ticket_id = create_resp.json()["id"]

    resp = client.get(f"/tickets/{ticket_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == ticket_id


def test_get_single_ticket_not_found(client, mock_triage):
    headers = auth_header(client)
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = client.get(f"/tickets/{fake_id}", headers=headers)
    assert resp.status_code == 404


# --- Delete Ticket (protected) ---

def test_delete_ticket_success(client, mock_triage):
    headers = auth_header(client)

    create_resp = client.post("/tickets", json={
        "title": "Ticket to delete completely",
        "description": "This ticket will be deleted and should no longer exist.",
        "customer_email": "delete@example.com",
    })
    ticket_id = create_resp.json()["id"]

    resp = client.delete(f"/tickets/{ticket_id}", headers=headers)
    assert resp.status_code == 204

    # Verify it's gone
    get_resp = client.get(f"/tickets/{ticket_id}", headers=headers)
    assert get_resp.status_code == 404


def test_delete_ticket_unauthorized(client, mock_triage):
    create_resp = client.post("/tickets", json={
        "title": "Unauthorized delete test ticket",
        "description": "Trying to delete without authentication should fail.",
        "customer_email": "noauth@example.com",
    })
    ticket_id = create_resp.json()["id"]

    resp = client.delete(f"/tickets/{ticket_id}")
    assert resp.status_code == 403


def test_delete_ticket_not_found(client, mock_triage):
    headers = auth_header(client)
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = client.delete(f"/tickets/{fake_id}", headers=headers)
    assert resp.status_code == 404
