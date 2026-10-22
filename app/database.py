# Import SQLite for local structured storage
import sqlite3

# Import datetime for timestamps
from datetime import datetime, timezone

# Import Path to locate the project folder
from pathlib import Path


# Find the main project folder
PROJECT_DIR = Path(__file__).resolve().parent.parent

# Save the database inside data/
DATABASE_PATH = PROJECT_DIR / "data" / "docu_sense.db"


def get_connection() -> sqlite3.Connection:
    """Open a connection to the SQLite database."""

    # Ensure the data folder exists
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Open the database
    connection = sqlite3.connect(DATABASE_PATH)

    # Let us access columns by names instead of positions
    connection.row_factory = sqlite3.Row

    return connection


def initialize_database() -> None:
    """Create required tables if they do not already exist."""

    connection = get_connection()
    cursor = connection.cursor()

    # Store uploaded document details
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS documents (
            document_id TEXT PRIMARY KEY,
            original_filename TEXT NOT NULL,
            saved_filename TEXT NOT NULL,
            pages_with_text INTEGER NOT NULL,
            total_characters INTEGER NOT NULL,
            chunks_created INTEGER NOT NULL,
            uploaded_at TEXT NOT NULL
        )
        """
    )

    # Store user questions and generated answers
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS question_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            source_count INTEGER NOT NULL,
            feedback TEXT,
            created_at TEXT NOT NULL
        )
        """
    )

    connection.commit()
    connection.close()


def save_document(
    document_id: str,
    original_filename: str,
    saved_filename: str,
    pages_with_text: int,
    total_characters: int,
    chunks_created: int,
) -> None:
    """Save uploaded document information."""

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT OR REPLACE INTO documents (
            document_id,
            original_filename,
            saved_filename,
            pages_with_text,
            total_characters,
            chunks_created,
            uploaded_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            document_id,
            original_filename,
            saved_filename,
            pages_with_text,
            total_characters,
            chunks_created,
            datetime.now(timezone.utc).isoformat(),
        ),
    )

    connection.commit()
    connection.close()


def get_documents() -> list[dict]:
    """Return all uploaded documents, newest first."""

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            document_id,
            original_filename,
            pages_with_text,
            total_characters,
            chunks_created,
            uploaded_at
        FROM documents
        ORDER BY uploaded_at DESC
        """
    )

    documents = [dict(row) for row in cursor.fetchall()]

    connection.close()

    return documents


def get_document(document_id: str) -> dict | None:
    """Return one uploaded document."""

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT *
        FROM documents
        WHERE document_id = ?
        """,
        (document_id,),
    )

    row = cursor.fetchone()
    connection.close()

    return dict(row) if row else None


def delete_document_record(document_id: str) -> None:
    """Delete one document's database record."""

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        DELETE FROM documents
        WHERE document_id = ?
        """,
        (document_id,),
    )

    connection.commit()
    connection.close()


def save_question(
    question: str,
    answer: str,
    source_count: int,
) -> int:
    """Save an answered question and return its history ID."""

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO question_history (
            question,
            answer,
            source_count,
            created_at
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            question,
            answer,
            source_count,
            datetime.now(timezone.utc).isoformat(),
        ),
    )

    history_id = cursor.lastrowid

    connection.commit()
    connection.close()

    return history_id


def get_question_history() -> list[dict]:
    """Return the latest questions and answers."""

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT *
        FROM question_history
        ORDER BY id DESC
        LIMIT 50
        """
    )

    history = [dict(row) for row in cursor.fetchall()]

    connection.close()

    return history


def save_feedback(history_id: int, feedback: str) -> bool:
    """Save thumbs-up or thumbs-down feedback."""

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        UPDATE question_history
        SET feedback = ?
        WHERE id = ?
        """,
        (feedback, history_id),
    )

    updated = cursor.rowcount > 0

    connection.commit()
    connection.close()

    return updated