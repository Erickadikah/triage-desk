# AI_JOURNEY.md — Triage Desk

> This document outlines how AI coding assistants were used during the development of this project, in line with Codematic's AI-First Workflow requirement.

---

## Tools Used
- **Claude (claude.ai)** — architecture planning, boilerplate generation, test writing
- **GitHub Copilot** — inline code suggestions

---

## 3 Complex Prompts Used

### Prompt 1 — Database Schema Design
**Context:** Designing the PostgreSQL schema for the ticketing system.

**Prompt used:**
> "I'm building a support ticketing system with FastAPI and PostgreSQL. The tickets need to store: title, description, customer email, AI-assigned category and priority, status (Open/In Progress/Resolved), and timestamps. Design a normalized SQLAlchemy model that is properly indexed for filtering by status and priority, and uses UUIDs as primary keys. Include an enum for status, priority, and category."

**What it generated:** A complete SQLAlchemy model with proper enums, UUID primary keys, indexed columns, and server-side timestamp defaults.

**What I changed:** I added the `ai_reasoning` column to store Claude's explanation, which the prompt didn't include. I also adjusted the `onupdate` parameter for `updated_at` to use `func.now()` rather than a Python datetime which would have been evaluated at class definition time.

---

### Prompt 2 — AI Triage Service with Retry Logic
**Context:** Building the Claude integration with proper fault tolerance.

**Prompt used:**
> "Write a Python async function that calls the Anthropic Claude API to classify a support ticket. The function should accept a title and description, send a structured prompt asking Claude to return a JSON object with category (Billing, Technical Bug, Feature Request, General, Account), priority (High, Medium, Low), and reasoning. Include retry logic using tenacity for rate limit and connection errors, a fallback mock triage when the API key is missing or the API fails, and proper logging. The response must be parsed into a Pydantic model."

**What it generated:** A solid base with retry decorators and JSON parsing.

**What I changed:** The AI used `asyncio.sleep` inside a sync retry decorator which would not work correctly. I refactored the retry logic to wrap only the API call and ensured the fallback `_get_mock_triage` is called correctly from the `except` blocks rather than letting tenacity re-raise.

---

### Prompt 3 — Pytest Test Suite
**Context:** Writing tests for the ticket API endpoints.

**Prompt used:**
> "Write a comprehensive pytest test suite for a FastAPI ticketing API with these endpoints: POST /tickets (public, triggers async AI triage), GET /tickets (protected, paginated with filters), PATCH /tickets/:id (protected, status update). Use SQLite for the test database, mock the async triage function, and include tests for authentication, validation errors, 404 handling, and duplicate registration. Use TestClient and dependency injection override."

**What it generated:** A good test structure covering most scenarios.

**What I changed:** The mock for the async `triage_ticket` function used `MagicMock` instead of `AsyncMock`, which caused coroutine errors at runtime. I replaced it with `AsyncMock` from `unittest.mock`. I also added the `@pytest.mark.asyncio` decorator where needed and fixed the test database cleanup between test runs.

---

## Instance Where AI Hallucinated

**Where it happened:** During the Docker Compose configuration.

**What happened:** Claude generated a `docker-compose.yml` that used `depends_on: backend` with a simple string format for the frontend service. This works in older versions of Docker Compose but does not support health check conditions. When I tried to add `condition: service_healthy` to wait for the backend to be fully ready, it failed because the backend service had no `healthcheck` defined.

More critically, Claude also suggested using `WidthType.PERCENTAGE` for a table in a completely unrelated context — clearly confusing context between different projects. This was caught immediately because it made no sense in a Python/FastAPI codebase.

**How I fixed it:** I added a proper `healthcheck` to the PostgreSQL service using `pg_isready`, and used the long-form `depends_on` syntax with `condition: service_healthy` to ensure the backend only starts after the database is ready. I removed the health check dependency on the frontend since it's acceptable for the frontend to retry connecting.

---

## Verification Task Answers

### 1. How would you implement RBAC if we added "Admins" and "Read-Only" users?

I would extend the `User` model with a `role` field using an enum:

```python
class UserRole(str, enum.Enum):
    AGENT = "agent"
    ADMIN = "admin"
    READ_ONLY = "read_only"
```

Then create a reusable dependency factory:

```python
def require_role(*roles: UserRole):
    def checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user
    return checker
```

Applied per route:
- `GET /tickets` — accessible by all roles
- `PATCH /tickets/:id` — `require_role(UserRole.AGENT, UserRole.ADMIN)`
- `DELETE /tickets/:id` — `require_role(UserRole.ADMIN)` only
- Read-only users get 403 on any mutating endpoint

This approach keeps role checks declarative, testable, and co-located with route definitions.

---

### 2. What happens if the LLM API goes down? How did you design your API to handle this failure gracefully?

The system is designed to **never fail a ticket submission** because of an LLM outage. Here's the layered approach:

**Layer 1 — Retry with exponential backoff (tenacity):**
```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((APIConnectionError, RateLimitError))
)
```
Transient failures (rate limits, brief outages) are retried up to 3 times before failing over.

**Layer 2 — Graceful fallback to keyword-based triage:**
If all retries fail, `_get_mock_triage()` kicks in — a deterministic keyword-based classifier that still assigns a reasonable category and priority. The ticket is saved with a note in `ai_reasoning` saying it was classified by the fallback system.

**Layer 3 — Missing API key detection:**
If `ANTHROPIC_API_KEY` is not set, the system immediately uses the fallback without attempting an API call, preventing unnecessary timeouts in development.

**The result:** A ticket is always created successfully. The worst case is a slightly less accurate triage — never a failed submission or 500 error for the customer.
