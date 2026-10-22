# Import Path to create a permanent Chroma database folder
from pathlib import Path

# Import ChromaDB for vector search
import chromadb


# Find the main Docu-sense-ai project folder
PROJECT_DIR = Path(__file__).resolve().parent.parent

# Store Chroma vector data here
CHROMA_DIR = PROJECT_DIR / "data" / "chroma"

# Create or connect to the permanent Chroma database
chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))

# Create the collection if it does not already exist
collection = chroma_client.get_or_create_collection(
    name="document_chunks"
)


def index_chunks(chunks: list[dict]) -> None:
    """Save document chunks in Chroma for semantic search."""

    # Create a unique ID list for Chroma
    chunk_ids = [chunk["chunk_id"] for chunk in chunks]

    # Store actual text separately so Chroma can search it
    documents = [chunk["text"] for chunk in chunks]

    # Store useful citation information with every chunk
    metadatas = [
        {
            "document_id": chunk["document_id"],
            "original_filename": chunk["original_filename"],
            "page_number": chunk["page_number"],
            "document_chunk_number": chunk["document_chunk_number"],
        }
        for chunk in chunks
    ]

    # upsert means add new chunks or update existing chunks
    collection.upsert(
        ids=chunk_ids,
        documents=documents,
        metadatas=metadatas,
    )


def search_chunks(question: str, n_results: int = 4) -> list[dict]:
    """Find the most relevant document chunks for a question."""

    # Ask Chroma to find semantically similar chunk text
    results = collection.query(
        query_texts=[question],
        n_results=n_results,
        include=["documents", "metadatas", "distances"],
    )

    # Return an empty list when no chunks exist
    if not results["ids"] or not results["ids"][0]:
        return []

    # Get the first query's results
    chunk_ids = results["ids"][0]
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    # Convert Chroma's result into a clean API-friendly list
    search_results = []

    for chunk_id, document, metadata, distance in zip(
        chunk_ids,
        documents,
        metadatas,
        distances,
    ):
        search_results.append(
            {
                "chunk_id": chunk_id,
                "text": document,
                "document_id": metadata["document_id"],
                "source_file": metadata["original_filename"],
                "page_number": metadata["page_number"],
                "distance": round(float(distance), 4),
            }
        )

    return search_results


def delete_document_chunks(document_id: str) -> None:
    """Remove every vector chunk belonging to one document."""

    collection.delete(
        where={"document_id": document_id}
    )