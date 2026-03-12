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


def _parse_ai_response(raw: str) -> AITriageResult:
    """Parse a JSON response from any LLM into an AITriageResult."""
    # Strip markdown code fences if present
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

    parsed = json.loads(cleaned)
    return AITriageResult(
        category=TicketCategory(parsed["category"]),
        priority=TicketPriority(parsed["priority"]),
        reasoning=parsed["reasoning"],
    )


def _get_mock_triage(title: str, description: str) -> AITriageResult:
    """Fallback mock triage when all AI providers are unavailable."""
    logger.warning("Using keyword-based fallback triage")
    text = (title + " " + description).lower()

    if any(w in text for w in ["payment", "bill", "charge", "invoice", "refund"]):
        category = TicketCategory.BILLING
    elif any(w in text for w in ["bug", "error", "crash", "broken", "not working", "fail"]):
        category = TicketCategory.TECHNICAL_BUG
    elif any(w in text for w in ["feature", "request", "add", "improve", "suggest"]):
        category = TicketCategory.FEATURE_REQUEST
    elif any(w in text for w in ["account", "login", "password", "access"]):
        category = TicketCategory.ACCOUNT
    else:
        category = TicketCategory.GENERAL

    if any(w in text for w in ["urgent", "critical", "down", "loss", "security", "breach"]):
        priority = TicketPriority.HIGH
    elif any(w in text for w in ["broken", "error", "fail", "payment"]):
        priority = TicketPriority.MEDIUM
    else:
        priority = TicketPriority.LOW

    return AITriageResult(
        category=category,
        priority=priority,
        reasoning="Classified using keyword-based fallback due to AI service unavailability.",
    )


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((anthropic.APIConnectionError, anthropic.RateLimitError)),
    reraise=True,
)
def _triage_with_claude(prompt: str) -> AITriageResult:
    """Attempt triage using Claude API with retry on transient failures."""
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = message.content[0].text.strip()
    logger.info(f"Claude triage response: {raw}")
    return _parse_ai_response(raw)


async def triage_ticket(title: str, description: str) -> AITriageResult:
    """
    AI triage with fallback:
      1. Claude (if ANTHROPIC_API_KEY is set)
      2. Keyword-based fallback (always available)
    """
    prompt = TRIAGE_PROMPT.format(title=title, description=description)

    # Layer 1: Claude
    if settings.ANTHROPIC_API_KEY:
        try:
            return _triage_with_claude(prompt)
        except Exception as e:
            logger.error(f"Claude failed: {e}")

    # Layer 2: Keyword fallback
    if not settings.ANTHROPIC_API_KEY:
        logger.warning("No AI API key configured — using keyword fallback")
    return _get_mock_triage(title, description)
