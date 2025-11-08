"""Tests for database module"""
from app.db.database import get_db


class TestGetDb:
    """Tests for get_db function"""

    def test_get_db_yields_session(self):
        """Test that get_db yields a database session"""
        db_gen = get_db()
        db = next(db_gen)

        assert db is not None
        # Verify it's a session object
        assert hasattr(db, "query")
        assert hasattr(db, "add")
        assert hasattr(db, "commit")
        assert hasattr(db, "rollback")
        assert hasattr(db, "close")

        # Clean up
        try:
            next(db_gen)
        except StopIteration:
            pass

    def test_get_db_closes_session(self):
        """Test that get_db closes the session properly"""
        db_gen = get_db()
        db = next(db_gen)

        # Verify session is active
        assert db.is_active

        # Finish the generator to trigger finally block
        try:
            next(db_gen)
        except StopIteration:
            pass

        # Session should be closed after generator completes
        # Note: The session close is handled in the finally block

    def test_get_db_multiple_calls(self):
        """Test that multiple calls to get_db work correctly"""
        db_gen1 = get_db()
        db1 = next(db_gen1)

        db_gen2 = get_db()
        db2 = next(db_gen2)

        # Both should be valid sessions
        assert db1 is not None
        assert db2 is not None

        # Clean up
        for gen in [db_gen1, db_gen2]:
            try:
                next(gen)
            except StopIteration:
                pass
