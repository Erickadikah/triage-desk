# Triage Desk

AI-powered customer support ticketing system that automatically categorizes and prioritizes tickets using Claude.

## Tech Stack

**Backend:** FastAPI, SQLAlchemy, PostgreSQL, Anthropic Claude API, JWT Auth
**Frontend:** Next.js 15 (App Router), React 19, Tailwind CSS v4, Lucide Icons
**Infrastructure:** Docker Compose

## Features

- **AI Triage** — Tickets are automatically categorized and prioritized by Claude with a keyword-based fallback
- **Kanban Dashboard** — Drag-free board with Open / In Progress / Resolved columns
- **Optimistic UI** — Status changes and deletes update instantly, rolling back on failure
- **JWT Authentication** — Register/login flow protecting agent-only endpoints
- **Retry Logic** — Exponential backoff via tenacity for transient API failures

## Getting Started

### Prerequisites

- Docker & Docker Compose
- An Anthropic API key ([console.anthropic.com](https://console.anthropic.com))

### Setup

1. Clone the repo:
   ```bash
   git clone <repo-url>
   cd triage-desk
   ```

2. Create the backend `.env` file:
   ```bash
   cp backend/.env.example backend/.env
   ```
   Then add your `ANTHROPIC_API_KEY` to `backend/.env`.

3. Start everything:
   ```bash
   docker compose up --build
   ```

4. Open the app:
   - **Frontend:** http://localhost:3000
   - **Backend API:** http://localhost:8000
   - **API Docs:** http://localhost:8000/docs

## API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/auth/register` | Public | Register a new agent |
| POST | `/auth/login` | Public | Login, returns JWT |
| POST | `/tickets` | Public | Create ticket (triggers AI triage) |
| GET | `/tickets` | Protected | List tickets (paginated, filterable) |
| GET | `/tickets/:id` | Protected | Get single ticket |
| PATCH | `/tickets/:id` | Protected | Update ticket status |
| DELETE | `/tickets/:id` | Protected | Delete a ticket |

## Running Tests

```bash
docker compose exec backend pytest tests/ -v
```

With coverage report:

```bash
docker compose exec backend pytest tests/ --cov=app --cov-report=term-missing
```

Current coverage: **95%** across 41 tests.

## Project Structure

```
triage-desk/
├── backend/
│   ├── app/
│   │   ├── models/          # SQLAlchemy models (ticket, user)
│   │   ├── schemas/         # Pydantic schemas (ticket, user)
│   │   ├── routes/          # API endpoints (auth, tickets)
│   │   ├── services/        # AI triage service
│   │   ├── middleware/       # JWT auth middleware
│   │   ├── config.py        # Settings via pydantic-settings
│   │   ├── database.py      # DB engine and session
│   │   └── main.py          # FastAPI app entry point
│   ├── tests/               # Pytest test suite
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/             # Next.js pages (login, register, dashboard)
│   │   ├── components/      # UI components (navbar, badge, button, card, select)
│   │   └── lib/             # API client, auth helpers, utils
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
└── AI_JOURNEY.md            # AI tool usage documentation
```

## Verification Task

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
