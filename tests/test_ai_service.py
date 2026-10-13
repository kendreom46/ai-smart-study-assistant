"""
Unit tests for AI Service using mocks.
Validates structured JSON quiz parsing, error sanitization, and client initialization
without making real API calls or requiring a paid API key.
"""

from unittest.mock import MagicMock
import pytest
from src.ai_service import AIService


def test_missing_api_key_raises_value_error():
    """Verify that calling get_client without an API key raises a helpful ValueError."""
    service = AIService(api_key="")
    assert not service.is_configured()
    with pytest.raises(ValueError) as excinfo:
        service.get_client()
    assert "GEMINI_API_KEY in your .env file" in str(excinfo.value)


def test_parse_quiz_json_clean():
    """Verify parsing valid structured JSON string into formatted quiz questions."""
    service = AIService(api_key="dummy_key")
    raw_json = """
    {
        "topic": "Data Structures",
        "questions": [
            {
                "question": "What is the worst-case time complexity of quicksort?",
                "option_a": "O(n)",
                "option_b": "O(n log n)",
                "option_c": "O(n^2)",
                "option_d": "O(1)",
                "correct_answer": "C",
                "explanation": "Quicksort degrades to O(n^2) with poor pivot choices."
            }
        ]
    }
    """
    questions = service._parse_quiz_json(raw_json)
    assert len(questions) == 1
    q = questions[0]
    assert q["id"] == 1
    assert q["question"] == "What is the worst-case time complexity of quicksort?"
    assert q["options"]["C"] == "O(n^2)"
    assert q["correct_answer"] == "C"
    assert "Quicksort degrades" in q["explanation"]


def test_parse_quiz_json_markdown_wrapped():
    """Verify that JSON wrapped in markdown code fences is parsed successfully."""
    service = AIService(api_key="dummy_key")
    wrapped_json = """```json
    {
        "topic": "Python",
        "questions": [
            {
                "question": "Is Python dynamically typed?",
                "option_a": "Yes",
                "option_b": "No",
                "option_c": "Only in strict mode",
                "option_d": "None of the above",
                "correct_answer": "A",
                "explanation": "Python performs type checks at runtime."
            }
        ]
    }
    ```"""
    questions = service._parse_quiz_json(wrapped_json)
    assert len(questions) == 1
    assert questions[0]["correct_answer"] == "A"


def test_parse_quiz_json_malformed():
    """Verify that invalid JSON raises a clear error."""
    service = AIService(api_key="dummy_key")
    with pytest.raises(Exception):
        service._parse_quiz_json("Not a valid json response")


def test_sanitize_error_protects_key():
    """Verify that API keys are never leaked in error messages."""
    service = AIService(api_key="dummy_key")
    fake_key = "AIzaSyDummySecretKey1234567890abcdef"
    raw_error = Exception(f"400 Bad Request with key {fake_key}")
    sanitized = service._sanitize_error(raw_error)
    assert fake_key not in sanitized
    assert "[PROTECTED_API_KEY]" in sanitized or "Authentication Error" in sanitized


def test_explain_topic_with_mock_client():
    """Verify explain_topic workflow with mocked Gemini client."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "### 📌 Overview & Definition\nRecursion is a programming technique..."
    mock_client.models.generate_content.return_value = mock_response

    service = AIService(api_key="test_key", client=mock_client)
    explanation = service.explain_topic("Recursion", level="beginner", length="concise")

    assert "Recursion is a programming technique" in explanation
    mock_client.models.generate_content.assert_called_once()
