"""Load initial data for ANB Rising Stars Showcase"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from app.db import models  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.database import SessionLocal, engine  # noqa: E402

# Create all tables
Base.metadata.create_all(bind=engine)


def load_example_data():
    """Load example data"""
    db = SessionLocal()

    try:
        print("🚀 Loading data...\n")

        # Check if data already exists
        existing_users = db.query(models.User).count()
        if existing_users > 0:
            print(f"⚠️  Database already has {existing_users} users. Skipping data load.")
            return

        # Create example users
        user1 = models.User(
            email="artist1@example.com",
            first_name="Carlos",
            last_name="Martinez",
            city="Bogota",
            country="Colombia",
        )
        user1.password = "SecurePass123"

        user2 = models.User(
            email="artist2@example.com",
            first_name="Maria",
            last_name="Lopez",
            city="Medellin",
            country="Colombia",
        )
        user2.password = "SecurePass123"

        user3 = models.User(
            email="artist3@example.com",
            first_name="Juan",
            last_name="Garcia",
            city="Cali",
            country="Colombia",
        )
        user3.password = "SecurePass123"

        users = [user1, user2, user3]

        for user in users:
            db.add(user)

        db.commit()
        print(f"✅ Created {len(users)} example users\n")
        print("📧 Users created:")
        for user in users:
            print(f"   - {user.email} (password: SecurePass123)")
        print("\n✨ Done!")

    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    load_example_data()
