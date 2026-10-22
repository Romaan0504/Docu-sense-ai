# Import JSON for reading saved chunk files
import json

# Import UUID to create unique document IDs
import uuid

# Import Path for safe folder and file handling
from pathlib import Path

# Import FastAPI tools
from fastapi import FastAPI, File, HTTPException, UploadFile

# Import HTML and static-file support
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request

# Import Pydantic for request validation
from pydantic import BaseModel, Field

# Import our PDF extraction functions
from app.pdf_service import extract_pdf_pages, save_extraction

# Import our chunking functions
from app.chunking_service import create_chunks, save_chunks

# Import Chroma vector database functions
from app.vector_store import (
    delete_document_chunks,
    index_chunks,
    search_chunks,
)

# Import Groq grounded-answer function
from app.rag_service import generate_grounded_answer

# Import SQLite functions
from app.database import (
    delete_document_record,
    get_document,
    get_documents,
    get_question_history,
    initialize_database,
    save_document,
    save_feedback,
    save_question,
)


# Find the app folder
APP_DIR = Path(__file__).resolve().parent

# Find the main Docu-sense-ai folder
PROJECT_DIR = APP_DIR.parent

# Important project folders
UPLOADS_DIR = PROJECT_DIR / "uploads"
EXTRACTED_DIR = PROJECT_DIR / "data" / "extracted"
CHUNKS_DIR = PROJECT_DIR / "data" / "chunks"

# Create folders if they do not already exist
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)
CHUNKS_DIR.mkdir(parents=True, exist_ok=True)

# Allow PDF files up to 25 MB
MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024


# Define the question body for search and RAG APIs
class SearchRequest(BaseModel):
    question: str = Field(
        min_length=3,
        max_length=500,
        description="Question to search in uploaded documents.",
    )


# Define the feedback body
class FeedbackRequest(BaseModel):
    feedback: str = Field(
        pattern="^(up|down)$",
        description="Use up for helpful and down for unhelpful.",
    )


# Create the FastAPI application
app = FastAPI(
    title="DocuSense AI",
    description="Policy, compliance, and contract document intelligence.",
    version="1.0.0",
)

# Create SQLite tables when the server starts
initialize_database()

# Make CSS and JavaScript available to the browser
app.mount(
    "/static",
    StaticFiles(directory=APP_DIR / "static"),
    name="static",
)

# Tell FastAPI where HTML templates are stored
templates = Jinja2Templates(directory=APP_DIR / "templates")


def validate_document_id(document_id: str) -> None:
    """Reject malformed document IDs."""

    # UUID hex IDs should have exactly 32 characters
    if len(document_id) != 32:
        raise HTTPException(
            status_code=400,
            detail="Invalid document ID.",
        )

    # Allow only hexadecimal characters
    allowed_characters = "0123456789abcdef"

    if any(character not in allowed_characters for character in document_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid document ID.",
        )


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Show the DocuSense AI website."""

    return templates.TemplateResponse(
        request=request,
        name="index.html",
    )


@app.get("/health")
async def health_check():
    """Simple API health check."""

    return {
        "status": "healthy",
        "service": "DocuSense AI",
    }


@app.post("/api/documents/upload", status_code=201, tags=["Documents"])
async def upload_document(file: UploadFile = File(...)):
    """Upload, extract, chunk, index, and save one PDF document."""

    # Ensure the user selected a filename
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Please select a PDF file.",
        )

    # Only accept PDFs
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported.",
        )

    # Read the uploaded file
    file_contents = await file.read()

    # Reject an empty upload
    if not file_contents:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is empty.",
        )

    # Reject files over 25 MB
    if len(file_contents) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail="PDF must be smaller than 25 MB.",
        )

    # Confirm the file starts like a real PDF
    if not file_contents.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=400,
            detail="This file does not appear to be a valid PDF.",
        )

    # Create a unique ID for the uploaded document
    document_id = uuid.uuid4().hex

    # Create a safe saved filename
    saved_filename = f"{document_id}.pdf"

    # Choose the upload location
    upload_path = UPLOADS_DIR / saved_filename

    # Save PDF bytes locally
    upload_path.write_bytes(file_contents)

    try:
        # Extract readable text page by page
        pages = extract_pdf_pages(upload_path)

        # Stop when a PDF has no extractable text
        if not pages:
            upload_path.unlink(missing_ok=True)

            raise HTTPException(
                status_code=422,
                detail=(
                    "No readable text was found. "
                    "This may be a scanned-image PDF."
                ),
            )

        # Save page-level extracted text
        extraction_path = EXTRACTED_DIR / f"{document_id}.json"

        save_extraction(
            output_path=extraction_path,
            document_id=document_id,
            original_filename=file.filename,
            pages=pages,
        )

        # Split long page text into overlapping chunks
        chunks = create_chunks(
            document_id=document_id,
            original_filename=file.filename,
            pages=pages,
        )

        # Save chunks so they are inspectable during development
        chunks_path = CHUNKS_DIR / f"{document_id}.json"

        save_chunks(
            output_path=chunks_path,
            document_id=document_id,
            original_filename=file.filename,
            chunks=chunks,
        )

        # Save chunks in Chroma for semantic retrieval
        index_chunks(chunks)

        # Save document metadata in SQLite
        save_document(
            document_id=document_id,
            original_filename=file.filename,
            saved_filename=saved_filename,
            pages_with_text=len(pages),
            total_characters=sum(
                page["character_count"] for page in pages
            ),
            chunks_created=len(chunks),
        )

        # Return useful details to the frontend
        return {
            "message": "Document uploaded and indexed successfully.",
            "document_id": document_id,
            "original_filename": file.filename,
            "pages_with_text": len(pages),
            "characters_extracted": sum(
                page["character_count"] for page in pages
            ),
            "chunks_created": len(chunks),
        }

    except HTTPException:
        raise

    except ValueError as error:
        # Remove broken uploads when extraction fails
        upload_path.unlink(missing_ok=True)

        raise HTTPException(
            status_code=422,
            detail=str(error),
        ) from error

    except Exception as error:
        # Remove upload if an unexpected processing error occurs
        upload_path.unlink(missing_ok=True)

        raise HTTPException(
            status_code=500,
            detail=f"Document processing failed: {error}",
        ) from error


@app.get("/api/documents", tags=["Documents"])
async def list_documents():
    """Return all uploaded documents."""

    documents = get_documents()

    return {
        "count": len(documents),
        "documents": documents,
    }


@app.delete("/api/documents/{document_id}", tags=["Documents"])
async def delete_document(document_id: str):
    """Delete one document and all of its related stored data."""

    validate_document_id(document_id)

    # Check whether the document exists in SQLite
    document = get_document(document_id)

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found.",
        )

    # Delete chunks from vector database
    delete_document_chunks(document_id)

    # Delete saved PDF, extraction JSON, and chunk JSON
    (UPLOADS_DIR / document["saved_filename"]).unlink(missing_ok=True)
    (EXTRACTED_DIR / f"{document_id}.json").unlink(missing_ok=True)
    (CHUNKS_DIR / f"{document_id}.json").unlink(missing_ok=True)

    # Delete document metadata from SQLite
    delete_document_record(document_id)

    return {
        "message": "Document and related data deleted successfully.",
        "document_id": document_id,
    }


@app.get("/api/documents/{document_id}/extraction", tags=["Documents"])
async def get_extraction(document_id: str):
    """Return extracted page text for one document."""

    validate_document_id(document_id)

    extraction_path = EXTRACTED_DIR / f"{document_id}.json"

    if not extraction_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Document extraction was not found.",
        )

    return json.loads(
        extraction_path.read_text(encoding="utf-8")
    )


@app.get("/api/documents/{document_id}/chunks", tags=["Documents"])
async def get_chunks(document_id: str):
    """Return saved chunks for one document."""

    validate_document_id(document_id)

    chunk_path = CHUNKS_DIR / f"{document_id}.json"

    if not chunk_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Document chunks were not found.",
        )

    return json.loads(
        chunk_path.read_text(encoding="utf-8")
    )


@app.post("/api/search", tags=["Search"])
async def semantic_search(search_request: SearchRequest):
    """Return relevant chunks without generating an LLM answer."""

    question = search_request.question.strip()

    results = search_chunks(
        question=question,
        n_results=4,
    )

    return {
        "question": question,
        "result_count": len(results),
        "results": results,
    }


@app.post("/api/ask", tags=["RAG"])
async def ask_question(ask_request: SearchRequest):
    """Answer a question using only uploaded documents."""

    # Clean extra spaces from the question
    question = ask_request.question.strip()

    # Retrieve relevant chunks first
    retrieved_chunks = search_chunks(
        question=question,
        n_results=4,
    )

    # Handle the case where no document evidence exists
    if not retrieved_chunks:
        answer = "I don't know based on the uploaded documents."

        history_id = save_question(
            question=question,
            answer=answer,
            source_count=0,
        )

        return {
            "history_id": history_id,
            "question": question,
            "answer": answer,
            "sources": [],
        }

    try:
        # Generate an answer grounded in retrieved chunks
        answer = generate_grounded_answer(
            question=question,
            retrieved_chunks=retrieved_chunks,
        )

    except RuntimeError as error:
        raise HTTPException(
            status_code=500,
            detail=str(error),
        ) from error

    # Build source citations for the UI
    sources = []

    for chunk in retrieved_chunks:
        sources.append(
            {
                "source_file": chunk["source_file"],
                "page_number": chunk["page_number"],
                "excerpt": chunk["text"][:500],
            }
        )

    # Save the question and answer for future review
    history_id = save_question(
        question=question,
        answer=answer,
        source_count=len(sources),
    )

    return {
        "history_id": history_id,
        "question": question,
        "answer": answer,
        "sources": sources,
    }


@app.get("/api/history", tags=["History"])
async def question_history():
    """Return recently asked questions."""

    history = get_question_history()

    return {
        "count": len(history),
        "history": history,
    }


@app.patch("/api/history/{history_id}/feedback", tags=["History"])
async def update_feedback(
    history_id: int,
    feedback_request: FeedbackRequest,
):
    """Save helpful or unhelpful feedback on an answer."""

    updated = save_feedback(
        history_id=history_id,
        feedback=feedback_request.feedback,
    )

    if not updated:
        raise HTTPException(
            status_code=404,
            detail="Question history item not found.",
        )

    return {
        "message": "Feedback saved successfully.",
        "history_id": history_id,
        "feedback": feedback_request.feedback,
    }