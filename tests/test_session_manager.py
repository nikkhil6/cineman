"""
Tests for session manager functionality.
"""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from cineman.session_manager import SessionManager, SessionData


def test_create_session():
    """Test creating a new session."""
    manager = SessionManager()
    session_id = manager.create_session()

    assert session_id is not None
    assert len(session_id) > 0
    print(f"✅ Created session: {session_id}")

    session = manager.get_session(session_id)
    assert session is not None
    assert session.session_id == session_id
    print("✅ Retrieved session successfully")


def test_session_data():
    """Test session data operations."""
    session = SessionData("test-session-123")

    # Test adding messages
    session.add_message("user", "I want a sci-fi movie")
    session.add_message("assistant", "Here are some recommendations...")

    history = session.get_chat_history()
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[1]["role"] == "assistant"
    print(f"✅ Chat history: {len(history)} messages")

    # Test adding recommended movies
    session.add_recommended_movies(["Inception", "Interstellar", "The Matrix"])
    movies = session.get_recommended_movies()
    assert len(movies) == 3
    assert "Inception" in movies
    print(f"✅ Recommended movies: {movies}")

    # Test avoiding duplicates
    session.add_recommended_movies(["Inception", "Blade Runner"])
    movies = session.get_recommended_movies()
    assert len(movies) == 4  # Should only add Blade Runner
    print(f"✅ Duplicate prevention works: {movies}")


def test_session_manager():
    """Test session manager operations."""
    manager = SessionManager()

    # Create multiple sessions
    session1_id = manager.create_session()
    session2_id = manager.create_session()

    assert session1_id != session2_id
    print("✅ Created 2 unique sessions")

    # Get sessions
    session1 = manager.get_session(session1_id)
    session2 = manager.get_session(session2_id)

    assert session1 is not None
    assert session2 is not None
    print("✅ Retrieved both sessions")

    # Add different data to each session
    session1.add_message("user", "Sci-fi movies")
    session2.add_message("user", "Horror movies")

    # Verify isolation
    assert len(session1.get_chat_history()) == 1
    assert len(session2.get_chat_history()) == 1
    assert (
        session1.get_chat_history()[0]["content"]
        != session2.get_chat_history()[0]["content"]
    )
    print("✅ Session isolation verified")

    # Test get_or_create
    existing_id, existing_session = manager.get_or_create_session(session1_id)
    assert existing_id == session1_id
    assert len(existing_session.get_chat_history()) == 1
    print("✅ get_or_create returned existing session")

    new_id, new_session = manager.get_or_create_session("non-existent-id")
    assert new_id != "non-existent-id"
    assert len(new_session.get_chat_history()) == 0
    print("✅ get_or_create created new session for invalid ID")

    # Test delete
    deleted = manager.delete_session(session1_id)
    assert deleted is True
    print("✅ Deleted session")

    session1_after = manager.get_session(session1_id)
    assert session1_after is None
    print("✅ Session no longer exists after deletion")


def test_chat_history_limit():
    """Test limiting chat history retrieval."""
    session = SessionData("test-limit")

    # Add many messages
    for i in range(10):
        session.add_message("user", f"Message {i}")
        session.add_message("assistant", f"Response {i}")

    # Get all messages
    all_history = session.get_chat_history()
    assert len(all_history) == 20
    print(f"✅ Total history: {len(all_history)} messages")

    # Get limited messages
    limited = session.get_chat_history(limit=5)
    assert len(limited) == 5
    assert limited[0]["content"] == "Response 7"  # Should get last 5
    print(f"✅ Limited history: {len(limited)} messages (last 5)")


if __name__ == "__main__":
    print("\n--- Testing Session Manager ---\n")

    try:
        test_create_session()
        print()
        test_session_data()
        print()
        test_session_manager()
        print()
        test_chat_history_limit()
        print()
        print("✅ All tests passed!")
    except AssertionError as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
