
import sqlite3
from pathlib import Path


# Assumes the existing SQLite database is backend/feedback.db.
# Verify this against backend/app/database.py before running.
DB_PATH = Path(__file__).resolve().parent / "feedback.db"


def get_columns(connection, table_name):
    rows = connection.execute(
        f"PRAGMA table_info({table_name})"
    ).fetchall()
    return {row[1] for row in rows}


def migrate():
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}\n"
            "Check backend/app/database.py and update DB_PATH if needed."
        )

    connection = sqlite3.connect(DB_PATH)

    try:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }

        required_tables = {"subjects", "feedback_submissions"}
        missing_tables = required_tables - tables

        if missing_tables:
            raise RuntimeError(
                "Expected database tables are missing: "
                + ", ".join(sorted(missing_tables))
            )

        subject_columns = get_columns(connection, "subjects")
        feedback_columns = get_columns(
            connection,
            "feedback_submissions",
        )

        with connection:
            if "semester" not in subject_columns:
                connection.execute(
                    """
                    ALTER TABLE subjects
                    ADD COLUMN semester INTEGER NOT NULL DEFAULT 1
                    """
                )
                print("Added subjects.semester.")
            else:
                print("subjects.semester already exists.")

            if "semester" not in feedback_columns:
                connection.execute(
                    """
                    ALTER TABLE feedback_submissions
                    ADD COLUMN semester INTEGER
                    """
                )
                print("Added feedback_submissions.semester.")
            else:
                print("feedback_submissions.semester already exists.")

            # Populate historic academic feedback from the matching
            # subject when possible. Existing rows are not deleted.
            connection.execute(
                """
                UPDATE feedback_submissions
                SET semester = COALESCE(
                    (
                        SELECT s.semester
                        FROM subjects AS s
                        JOIN departments AS d
                          ON d.id = s.department_id
                        WHERE lower(s.name) = lower(
                            feedback_submissions.subject_name
                        )
                          AND lower(d.name) = lower(
                            feedback_submissions.department_name
                        )
                        LIMIT 1
                    ),
                    1
                )
                WHERE COALESCE(is_other, 0) = 0
                  AND subject_name IS NOT NULL
                  AND semester IS NULL
                """
            )

            # General institutional feedback is not tied to a semester.
            connection.execute(
                """
                UPDATE feedback_submissions
                SET semester = NULL
                WHERE COALESCE(is_other, 0) = 1
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS ix_subjects_semester
                ON subjects (semester)
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS ix_feedback_submissions_semester
                ON feedback_submissions (semester)
                """
            )

        print("\nSemester migration completed successfully.")
        print(f"Database: {DB_PATH}")
        print("Existing feedback records were preserved.")

    finally:
        connection.close()


if __name__ == "__main__":
    migrate()
