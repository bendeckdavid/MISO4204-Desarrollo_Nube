"""Load initial data - TEMPLATE"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from app.db import models  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.database import SessionLocal, engine  # noqa: E402

Base.metadata.create_all(bind=engine)


def load_example_data():
    """Load example data"""
    db = SessionLocal()

    try:
        print("🚀 Loading data...\n")

        tasks = [
            models.Task(name="Task 1", description="First task"),
            models.Task(name="Task 2", description="Second task"),
            models.Task(name="Task 3", description="Third task"),
        ]

        for task in tasks:
            db.add(task)

        db.commit()
        print(f"✅ Created {len(tasks)} records\n")
        print("✨ Done!")

    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    load_example_data()
