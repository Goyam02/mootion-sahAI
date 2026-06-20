import sys
import os

# Add backend to path so we can import app core models
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

# Load env variables from the backend directory
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from app.core.database import engine
from sqlalchemy import text, inspect

def migrate():
    print("Connecting to DB...")
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        if 'student_doubts' in tables:
            columns = [col['name'] for col in inspector.get_columns('student_doubts')]
            if 'messages' not in columns:
                # Use JSONB for PostgreSQL, TEXT/JSON for SQLite
                col_type = "JSONB" if engine.dialect.name == "postgresql" else "TEXT"
                with engine.begin() as conn:
                    conn.execute(text(f"ALTER TABLE student_doubts ADD COLUMN messages {col_type};"))
                print(f"Successfully added messages column ({col_type}) to student_doubts table!")
            else:
                print("messages column already exists in student_doubts table.")
        else:
            print("student_doubts table does not exist yet. It will be created by Alembic/SQLAlchemy metadata.")
    except Exception as e:
        print("Error executing migration SQL:", e)

if __name__ == "__main__":
    migrate()
