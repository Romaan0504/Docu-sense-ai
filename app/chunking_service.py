# Import json so we can save chunks in a JSON file
import json

# Import Path for safe file paths
from pathlib import Path

# Import LangChain's text splitter
from langchain_text_splitters import RecursiveCharacterTextSplitter


# Set chunk size to 800 characters
CHUNK_SIZE = 800

# Repeat 150 characters between nearby chunks
CHUNK_OVERLAP = 150


# Create chunks while preserving document and page metadata
def create_chunks(
    document_id: str,
    original_filename: str,
    pages: list[dict],
) -> list[dict]:
    # Create a LangChain splitter
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", " ", ""],
    )

    # Store every chunk from every page
    chunks = []

    # Count chunks across the entire document
    document_chunk_number = 1

    # Process one extracted page at a time
    for page in pages:
        page_number = page["page_number"]
        page_text = page["text"]

        # Split this page's text into smaller pieces
        page_chunks = splitter.split_text(page_text)

        # Save metadata with every chunk
        for page_chunk_number, chunk_text in enumerate(page_chunks, start=1):
            chunks.append(
                {
                    "chunk_id": (
                        f"{document_id}_page_{page_number}_"
                        f"chunk_{page_chunk_number}"
                    ),
                    "document_id": document_id,
                    "original_filename": original_filename,
                    "page_number": page_number,
                    "page_chunk_number": page_chunk_number,
                    "document_chunk_number": document_chunk_number,
                    "text": chunk_text,
                    "character_count": len(chunk_text),
                }
            )

            # Increase document-wide chunk number
            document_chunk_number += 1

    return chunks


# Save all chunks for one document in a JSON file
def save_chunks(
    output_path: Path,
    document_id: str,
    original_filename: str,
    chunks: list[dict],
) -> None:
    # Create one structured object for this document's chunks
    chunk_data = {
        "document_id": document_id,
        "original_filename": original_filename,
        "chunk_size": CHUNK_SIZE,
        "chunk_overlap": CHUNK_OVERLAP,
        "total_chunks": len(chunks),
        "chunks": chunks,
    }

    # Save readable JSON data
    output_path.write_text(
        json.dumps(chunk_data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )