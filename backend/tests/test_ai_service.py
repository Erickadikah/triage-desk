import pytest
from unittest.mock import patch, MagicMock
import anthropic
import json

from app.services.ai_service import triage_ticket, _get_mock_triage
from app.models.ticket import TicketCategory, TicketPriority


# --- Keyword fallback tests ---

class TestMockTriage:
    def test_billing_keywords(self):
        result = _get_mock_triage("Payment issue", "I was charged twice on my invoice")
        assert result.category == TicketCategory.BILLING

    def test_technical_bug_keywords(self):
        result = _get_mock_triage("App crash", "The app crashes with an error on startup")
        assert result.category == TicketCategory.TECHNICAL_BUG

    def test_feature_request_keywords(self):
        result = _get_mock_triage("New feature", "Please add dark mode to the app")
        assert result.category == TicketCategory.FEATURE_REQUEST

    def test_account_keywords(self):
        result = _get_mock_triage("Login issue", "I cannot access my account or reset password")
        assert result.category == TicketCategory.ACCOUNT

    def test_general_fallback(self):
        result = _get_mock_triage("Hello", "I have a general question about your services")
        assert result.category == TicketCategory.GENERAL

    def test_high_priority_keywords(self):
        result = _get_mock_triage("Urgent", "System is down, critical security breach detected")
        assert result.priority == TicketPriority.HIGH

    def test_medium_priority_keywords(self):
        result = _get_mock_triage("Problem", "Payment processing is broken for some users")
        assert result.priority == TicketPriority.MEDIUM

    def test_low_priority_default(self):
        result = _get_mock_triage("Hello", "I have a general question about your product")
        assert result.priority == TicketPriority.LOW

    def test_fallback_reasoning_message(self):
        result = _get_mock_triage("Test", "Just a general test ticket for the system")
        assert "fallback" in result.reasoning.lower()


# --- Claude API integration tests ---

class TestTriageTicket:
    @pytest.mark.asyncio
    async def test_missing_api_key_uses_fallback(self):
        with patch("app.services.ai_service.settings") as mock_settings:
            mock_settings.ANTHROPIC_API_KEY = ""
            result = await triage_ticket("Bug report", "The application crashes on startup every time")
            assert result.category is not None
            assert result.priority is not None
            assert "fallback" in result.reasoning.lower()

    @pytest.mark.asyncio
    async def test_successful_claude_response(self):
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps({
            "category": "Technical Bug",
            "priority": "High",
            "reasoning": "Application crash indicates a technical issue",
        }))]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response

        with patch("app.services.ai_service.settings") as mock_settings, \
             patch("app.services.ai_service.anthropic.Anthropic", return_value=mock_client):
            mock_settings.ANTHROPIC_API_KEY = "test-key"
            result = await triage_ticket("App crash", "Application crashes on startup")
            assert result.category == TicketCategory.TECHNICAL_BUG
            assert result.priority == TicketPriority.HIGH
            assert "crash" in result.reasoning.lower()

    @pytest.mark.asyncio
    async def test_api_status_error_uses_fallback(self):
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.headers = {}
        mock_client.messages.create.side_effect = anthropic.APIStatusError(
            message="Internal Server Error",
            response=mock_resp,
            body=None,
        )

        with patch("app.services.ai_service.settings") as mock_settings, \
             patch("app.services.ai_service.anthropic.Anthropic", return_value=mock_client):
            mock_settings.ANTHROPIC_API_KEY = "test-key"
            result = await triage_ticket("Payment failed", "My payment is not going through")
            assert result.category is not None
            assert "fallback" in result.reasoning.lower()

    @pytest.mark.asyncio
    async def test_malformed_json_uses_fallback(self):
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="This is not JSON at all")]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response

        with patch("app.services.ai_service.settings") as mock_settings, \
             patch("app.services.ai_service.anthropic.Anthropic", return_value=mock_client):
            mock_settings.ANTHROPIC_API_KEY = "test-key"
            result = await triage_ticket("Test ticket title", "Some description for the test ticket here")
            assert result.category is not None
            assert "fallback" in result.reasoning.lower()

    @pytest.mark.asyncio
    async def test_missing_json_keys_uses_fallback(self):
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps({"category": "Billing"}))]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response

        with patch("app.services.ai_service.settings") as mock_settings, \
             patch("app.services.ai_service.anthropic.Anthropic", return_value=mock_client):
            mock_settings.ANTHROPIC_API_KEY = "test-key"
            result = await triage_ticket("Billing question", "I have a question about my recent bill")
            assert result.category is not None
            assert "fallback" in result.reasoning.lower()
