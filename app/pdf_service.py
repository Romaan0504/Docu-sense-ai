# Import json so extracted page data can be saved in a JSON file
import json

# Import Path for safe file paths
from pathlib import Path

# Import PdfReader to read PDF files
from pypdf import PdfReader

# Import PDF reading error type
from pypdf.errors import PdfReadError


# Extract readable text from every page in a PDF
def extract_pdf_pages(pdf_path: Path) -> list[dict]:
    try:
        # Open the PDF file
        reader = PdfReader(pdf_path)

        # Stop password-protected PDFs for now
        if reader.is_encrypted:
            raise ValueError("Password-protected PDFs are not supported.")

        # Store extracted data from every page
        pages = []

        # Start page numbers from 1 because users see Page 1, not Page 0
        for page_number, page in enumerate(reader.pages, start=1):
            # Extract text from the current PDF page
            text = page.extract_text() or ""

            # Remove unnecessary extra spaces and blank lines
            cleaned_text = " ".join(text.split())

            # Save only pages that actually contain readable text
            if cleaned_text:
                pages.append(
                    {
                        "page_number": page_number,
                        "text": cleaned_text,
                        "character_count": len(cleaned_text),
                    }
                )

        return pages

    except PdfReadError as error:
        raise ValueError("The PDF could not be read.") from error


# Save extracted PDF text and metadata as one JSON file
def save_extraction(
    output_path: Path,
    document_id: str,
    original_filename: str,
    pages: list[dict],
) -> None:
    # Create useful metadata for this uploaded document
    extraction_data = {
        "document_id": document_id,
        "original_filename": original_filename,
        "pages_with_text": len(pages),
        "total_characters": sum(page["character_count"] for page in pages),
        "pages": pages,
    }

    # Save readable JSON with UTF-8 text support
    output_path.write_text(
        json.dumps(extraction_data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )