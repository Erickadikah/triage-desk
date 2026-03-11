import anthropic
import json
import logging
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from app.config import settings
from app.schemas.ticket import AITriageResult
from app.models.ticket import TicketCategory, TicketPriority

logger = logging.getLogger(__name__)

TRIAGE_PROMPT = """You are a smart customer support triage assistant. 
Analyze the following support ticket and classify it.

Ticket Title: {title}
Ticket Description: {description}

You must respond with ONLY a valid JSON object in this exact format:
{{
  "category": "<one of: Billing, Technical Bug, Feature Request, General, Account>",
  "priority": "<one of: High, Medium, Low>",
  "reasoning": "<brief 1-2 sentence explanation of your classification>"
}}

Priority guidelines:
- High: System down, data loss, security issue, payment failure
- Medium: Feature broken but workaround exists, billing confusion
- Low: Feature requests, general questions, minor UI issues

Respond with ONLY the JSON. No markdown, no extra text."""


def _get_mock_triage(title: str, description: str) -> AITriageResult:
    """Fallback mock triage when AI is unavailable."""
    logger.warning("Using mock triage fallback")
    desc_lower = (title + " " + description).lower()

    if any(word in desc_lower for word in ["payment", "bill", "charge", "invoice", "refund"]):
        category = TicketCategory.BILLING
    elif any(word in desc_lower for word in ["bug", "error", "crash", "broken", "not working", "fail"]):
        category = TicketCategory.TECHNICAL_BUG
    elif any(word in desc_lower for word in ["feature", "request", "add", "improve", "suggest"]):
        category = TicketCategory.FEATURE_REQUEST
    elif any(word in desc_lower for word in ["account", "login", "password", "access"]):
        category = TicketCategory.ACCOUNT
    else:
        category = TicketCategory.GENERAL

    if any(word in desc_lower for word in ["urgent", "critical", "down", "loss", "security", "breach"]):
        priority = TicketPriority.HIGH
    elif any(word in desc_lower for word in ["broken", "error", "fail", "payment"]):
        priority = TicketPriority.MEDIUM
    else:
        priority = TicketPriority.LOW

    return AITriageResult(
        category=category,
        priority=priority,
        reasoning="Classified using keyword-based fallback due to AI service unavailability."
    )


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((anthropic.APIConnectionError, anthropic.RateLimitError)),
    reraise=False
)
async def triage_ticket(title: str, description: str) -> AITriageResult:
    """
    Use Claude to automatically categorize and prioritize a support ticket.
    Includes retry logic for transient failures and graceful fallback.
    """
    if not settings.ANTHROPIC_API_KEY:
        logger.warning("ANTHROPIC_API_KEY not set — using mock triage")
        return _get_mock_triage(title, description)

    try:
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[
                {
                    "role": "user",
                    "content": TRIAGE_PROMPT.format(title=title, description=description)
                }
            ]
        )

        raw_response = message.content[0].text.strip()
        logger.info(f"Claude triage response: {raw_response}")

        parsed = json.loads(raw_response)

        return AITriageResult(
            category=TicketCategory(parsed["category"]),
            priority=TicketPriority(parsed["priority"]),
            reasoning=parsed["reasoning"]
        )

    except anthropic.APIStatusError as e:
        logger.error(f"Claude API error {e.status_code}: {e.message}")
        return _get_mock_triage(title, description)

    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.error(f"Failed to parse Claude response: {e}")
        return _get_mock_triage(title, description)

    except Exception as e:
        logger.error(f"Unexpected error during triage: {e}")
        return _get_mock_triage(title, description)
