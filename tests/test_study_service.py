"""
Unit tests for StudyMate AI business logic and quiz scoring.
"""

from src.study_service import (
    validate_input_length,
    grade_quiz,
    format_quiz_markdown,
    save_study_session,
)
from src.database import get_history


def test_validate_input_length():
    """Verify input validation behavior for various string lengths."""
    # Empty
    valid, err = validate_input_length("", min_length=5, field_name="Topic")
    assert not valid
    assert "cannot be empty" in err

    # Too short
    valid, err = validate_input_length("AI", min_length=5, field_name="Topic")
    assert not valid
    assert "too short" in err

    # Exceeds max length
    valid, err = validate_input_length("x" * 200, max_length=100, field_name="Notes")
    assert not valid
    assert "exceeds maximum allowed length" in err

    # Valid
    valid, err = validate_input_length("Machine Learning Principles", min_length=5)
    assert valid
    assert err is None


def test_grade_quiz():
    """Verify accurate calculation of quiz scores and feedback."""
    questions = [
        {
            "id": 1,
            "question": "What is the time complexity of binary search?",
            "options": {"A": "O(n)", "B": "O(log n)", "C": "O(n log n)", "D": "O(1)"},
            "correct_answer": "B",
            "explanation": "Binary search halves the search space each step.",
        },
        {
            "id": 2,
            "question": "Which layer of OSI model does IP operate at?",
            "options": {"A": "Data Link", "B": "Transport", "C": "Network", "D": "Application"},
            "correct_answer": "C",
            "explanation": "IP is a Network layer protocol.",
        },
    ]

    # Perfect score: 2/2 = 100%
    user_answers = {"1": "B", "2": "C"}
    grade = grade_quiz(questions, user_answers)
    assert grade["total_questions"] == 2
    assert grade["correct_count"] == 2
    assert grade["score_percentage"] == 100.0
    assert grade["detailed_results"][0]["is_correct"] is True
    assert grade["detailed_results"][1]["is_correct"] is True

    # Partial score: 1/2 = 50%
    user_answers_partial = {"1": "B", "2": "A"}
    grade_partial = grade_quiz(questions, user_answers_partial)
    assert grade_partial["correct_count"] == 1
    assert grade_partial["score_percentage"] == 50.0
    assert grade_partial["detailed_results"][1]["is_correct"] is False


def test_format_quiz_markdown():
    """Verify markdown output formatting for quiz review."""
    grade_data = {
        "total_questions": 1,
        "correct_count": 1,
        "score_percentage": 100.0,
        "detailed_results": [
            {
                "id": "1",
                "question": "What is 2+2?",
                "selected_option": "B",
                "selected_text": "4",
                "correct_option": "B",
                "correct_text": "4",
                "is_correct": True,
                "explanation": "Basic addition.",
            }
        ],
    }
    md = format_quiz_markdown("Math Basics", grade_data)
    assert "**Score:** 1/1 (100.0%)" in md
    assert "✅ Correct" in md
    assert "What is 2+2?" in md


def test_save_study_session(tmp_path):
    """Verify session saving helper with database."""
    test_db = str(tmp_path / "study_test.db")

    session_id = save_study_session(
        session_type="notes_summary",
        title="Summary of Physics Chapter 1",
        content="Newton's laws of motion...",
        input_excerpt="Paste notes excerpt...",
        metadata_dict={"type": "short"},
        db_path=test_db,
    )
    assert session_id > 0

    records = get_history(db_path=test_db)
    assert len(records) == 1
    assert records[0]["title"] == "Summary of Physics Chapter 1"
