"""
Study Service for StudyMate AI
Coordinates business logic, input validation, quiz grading, and history persistence.
"""

import json
from typing import Any, Dict, List, Optional, Tuple
from src.database import add_history_entry


def validate_input_length(
    text: str,
    min_length: int = 2,
    max_length: int = 30000,
    field_name: str = "Input",
) -> Tuple[bool, Optional[str]]:
    """
    Validate that user input meets length requirements.
    Returns (is_valid, error_message).
    """
    if not text or not text.strip():
        return False, f"{field_name} cannot be empty."

    stripped = text.strip()
    if len(stripped) < min_length:
        return False, f"{field_name} is too short (minimum {min_length} characters required)."

    if len(stripped) > max_length:
        return False, f"{field_name} exceeds maximum allowed length of {max_length:,} characters."

    return True, None


def grade_quiz(
    quiz_questions: List[Dict[str, Any]],
    user_answers: Dict[str, str],
) -> Dict[str, Any]:
    """
    Grade user answers against the generated quiz answer key.

    Returns:
    {
        "total_questions": int,
        "correct_count": int,
        "score_percentage": float,
        "detailed_results": List[Dict[str, Any]]
    }
    """
    total = len(quiz_questions)
    if total == 0:
        return {
            "total_questions": 0,
            "correct_count": 0,
            "score_percentage": 0.0,
            "detailed_results": [],
        }

    correct_count = 0
    detailed_results = []

    for q in quiz_questions:
        q_id = str(q.get("id", ""))
        correct_opt = str(q.get("correct_answer", "")).upper()
        user_opt = str(user_answers.get(q_id, "")).upper()

        is_correct = bool(user_opt and user_opt == correct_opt)
        if is_correct:
            correct_count += 1

        options = q.get("options", {})
        detailed_results.append({
            "id": q_id,
            "question": q.get("question", ""),
            "options": options,
            "selected_option": user_opt,
            "selected_text": options.get(user_opt, "Unanswered" if not user_opt else user_opt),
            "correct_option": correct_opt,
            "correct_text": options.get(correct_opt, ""),
            "is_correct": is_correct,
            "explanation": q.get("explanation", ""),
        })

    percentage = round((correct_count / total) * 100, 1)

    return {
        "total_questions": total,
        "correct_count": correct_count,
        "score_percentage": percentage,
        "detailed_results": detailed_results,
    }


def format_quiz_markdown(
    topic: str,
    grade_data: Dict[str, Any],
) -> str:
    """Format quiz results as structured Markdown for review and history storage."""
    total = grade_data["total_questions"]
    correct = grade_data["correct_count"]
    pct = grade_data["score_percentage"]

    lines = [
        f"# Quiz Results: {topic}",
        f"**Score:** {correct}/{total} ({pct}%)\n",
        "---",
    ]

    for item in grade_data.get("detailed_results", []):
        status = "✅ Correct" if item["is_correct"] else "❌ Incorrect"
        lines.append(f"### Question {item['id']}: {item['question']}")
        lines.append(f"**Status:** {status}")
        lines.append(f"- **Your Answer:** {item['selected_option']}) {item['selected_text']}")
        lines.append(f"- **Correct Answer:** {item['correct_option']}) {item['correct_text']}")
        lines.append(f"\n💡 **Explanation:** {item['explanation']}\n")

    return "\n".join(lines)


def save_study_session(
    session_type: str,
    title: str,
    content: str,
    input_excerpt: Optional[str] = None,
    metadata_dict: Optional[Dict[str, Any]] = None,
    db_path: Optional[str] = None,
) -> int:
    """Save an educational session into the local SQLite database."""
    meta_json = json.dumps(metadata_dict or {})
    return add_history_entry(
        session_type=session_type,
        title=title,
        content=content,
        input_excerpt=input_excerpt,
        metadata=meta_json,
        db_path=db_path,
    )
