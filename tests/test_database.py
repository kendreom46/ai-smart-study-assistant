"""
Unit tests for StudyMate AI SQLite Database operations.
All tests use temporary file paths to prevent modifying actual study data.
"""

import os
import pytest
from src.database import (
    init_db,
    add_history_entry,
    get_history,
    get_history_by_id,
    delete_history_entry,
    clear_all_history,
    get_history_stats,
)


@pytest.fixture
def temp_db(tmp_path):
    """Fixture to provide a clean, isolated temporary SQLite database."""
    db_file = str(tmp_path / "test_studymate.db")
    init_db(db_file)
    return db_file


def test_init_db(temp_db):
    """Verify that the database and table initialize without errors."""
    assert os.path.exists(temp_db)
    stats = get_history_stats(temp_db)
    assert stats["total_sessions"] == 0
    assert stats["type_counts"] == {}


def test_add_and_retrieve_history(temp_db):
    """Verify adding entries and retrieving them with get_history."""
    entry_id = add_history_entry(
        session_type="topic_explainer",
        title="Binary Search Trees",
        content="Detailed explanation of BST operations.",
        input_excerpt="Explain BST",
        db_path=temp_db,
    )
    assert entry_id > 0

    history = get_history(db_path=temp_db)
    assert len(history) == 1
    assert history[0]["title"] == "Binary Search Trees"
    assert history[0]["session_type"] == "topic_explainer"
    assert history[0]["input_excerpt"] == "Explain BST"


def test_get_history_search_and_filter(temp_db):
    """Verify search filtering and session_type categorization."""
    add_history_entry(
        session_type="topic_explainer",
        title="Merge Sort Algorithm",
        content="Divide and conquer algorithm explanation.",
        db_path=temp_db,
    )
    add_history_entry(
        session_type="notes_summary",
        title="Operating Systems Notes",
        content="Paging and virtual memory concepts.",
        db_path=temp_db,
    )
    add_history_entry(
        session_type="quiz",
        title="DBMS Practice Quiz",
        content="Quiz on SQL and Normalization.",
        db_path=temp_db,
    )

    # Filter by session type
    explainer_records = get_history(session_type="topic_explainer", db_path=temp_db)
    assert len(explainer_records) == 1
    assert explainer_records[0]["title"] == "Merge Sort Algorithm"

    # Search keyword
    search_results = get_history(search_query="virtual memory", db_path=temp_db)
    assert len(search_results) == 1
    assert search_results[0]["title"] == "Operating Systems Notes"

    # Search non-matching keyword
    empty_results = get_history(search_query="quantum physics", db_path=temp_db)
    assert len(empty_results) == 0


def test_get_history_by_id(temp_db):
    """Verify fetching an entry specifically by primary key."""
    entry_id = add_history_entry(
        session_type="chat",
        title="Study Chat: Polymorphism",
        content="Polymorphism enables OOP flexibility.",
        db_path=temp_db,
    )
    record = get_history_by_id(entry_id, db_path=temp_db)
    assert record is not None
    assert record["id"] == entry_id
    assert record["title"] == "Study Chat: Polymorphism"

    # Non-existent ID
    non_existent = get_history_by_id(99999, db_path=temp_db)
    assert non_existent is None


def test_delete_history_entry(temp_db):
    """Verify individual record deletion."""
    id1 = add_history_entry("quiz", "Quiz 1", "Content 1", db_path=temp_db)
    id2 = add_history_entry("quiz", "Quiz 2", "Content 2", db_path=temp_db)

    assert len(get_history(db_path=temp_db)) == 2

    # Delete id1
    deleted = delete_history_entry(id1, db_path=temp_db)
    assert deleted is True

    remaining = get_history(db_path=temp_db)
    assert len(remaining) == 1
    assert remaining[0]["id"] == id2


def test_clear_all_history(temp_db):
    """Verify clearing all history records."""
    add_history_entry("quiz", "Quiz 1", "Content 1", db_path=temp_db)
    add_history_entry("quiz", "Quiz 2", "Content 2", db_path=temp_db)

    assert len(get_history(db_path=temp_db)) == 2
    clear_all_history(temp_db)
    assert len(get_history(db_path=temp_db)) == 0


def test_history_stats(temp_db):
    """Verify that genuine counts are aggregated without fabricated statistics."""
    add_history_entry("topic_explainer", "Topic 1", "Content", db_path=temp_db)
    add_history_entry("topic_explainer", "Topic 2", "Content", db_path=temp_db)
    add_history_entry("quiz", "Quiz 1", "Content", db_path=temp_db)

    stats = get_history_stats(temp_db)
    assert stats["total_sessions"] == 3
    assert stats["type_counts"].get("topic_explainer") == 2
    assert stats["type_counts"].get("quiz") == 1
