# DocuSense AI

> A Retrieval-Augmented Generation (RAG) backend for policy, compliance and contract PDFs. Every answer cites the source document and page number.

![Python](https://img.shields.io/badge/Python-3.12-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688)
![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector%20Search-6E44FF)
![Groq](https://img.shields.io/badge/Groq-LLM%20Inference-orange)
![Docker](https://img.shields.io/badge/Docker-Containerized-2496ED)

<!-- Add a screenshot or short demo GIF here, e.g. ![Demo](docs/demo.gif) -->

## Overview

Teams in HR, compliance, consulting and legal support often need one specific answer buried inside a long PDF such as a handbook, privacy policy or contract. A general chatbot may answer confidently without showing where the answer came from.

DocuSense AI takes a verifiable approach: it retrieves evidence from the uploaded documents first, generates an answer only from that evidence, and shows the filename, page number and excerpt behind every answer.

**Scope:** this project focuses on the backend: ingestion, retrieval, grounded generation, storage and evaluation. The browser interface is a lightweight, AI-assisted page for exercising the API.

## Features

- Upload text-based PDFs (up to 25 MB) with validation
- Page-by-page text extraction using PyPDF
- Overlapping chunking with LangChain Text Splitters
- Semantic search over ChromaDB
- Answers generated through the Groq API, restricted to retrieved evidence
- Page-level citations with source excerpts
- Question history and helpful/unhelpful feedback stored in SQLite
- Full document deletion (PDF, extracted text, vector chunks and database record)
- Retrieval evaluation script with a local test set
- Runs locally or in Docker

## How It Works

```
Upload PDF
   ↓
Extract text page by page
   ↓
Split into overlapping chunks
   ↓
Index chunks in ChromaDB
   ↓
Retrieve the most relevant evidence for a question
   ↓
Generate an answer with Groq, using only that evidence
   ↓
Return the answer with filename, page number and excerpt
```

## Tech Stack

| Layer | Tools |
|---|---|
| Backend API | Python, FastAPI, Uvicorn |
| PDF extraction | PyPDF |
| Chunking | LangChain Text Splitters |
| Vector database | ChromaDB |
| LLM inference | Groq API |
| Application storage | SQLite |
| Configuration | python-dotenv |
| Packaging | Docker |
| Demo interface | Lightweight HTML/CSS/JavaScript page (AI-assisted) |

## Design Decisions

**1. Page-level citations.** Each answer includes the source filename, page number and a retrieved excerpt, so users can verify it instead of trusting the model blindly.

**2. Retrieval before generation.** The LLM never sees the whole PDF. It receives only the top retrieved chunks, which keeps answers tied to the uploaded documents.

**3. Explicit no-answer behavior.** The system prompt tells the model to reply `I don't know based on the uploaded documents.` when the evidence does not clearly answer the question.

**4. Persistent application state.** SQLite stores document metadata, question history, source counts and feedback, so the app behaves like a real internal tool rather than a one-off demo.

**5. Measured retrieval quality.** A small evaluation set checks whether the expected documents are retrieved for known questions.

Latest local run:

```
Answerable retrieval tests: 4/4 passed
```

The evaluation also surfaced a real RAG limitation: semantic search can still return the closest chunks for an unrelated question. That is why the grounding prompt and visible citations matter.

## Project Structure

```
Docu-sense-ai/
├── app/
│   ├── static/            # demo UI assets
│   ├── templates/         # demo UI page
│   ├── chunking_service.py
│   ├── database.py
│   ├── main.py
│   ├── pdf_service.py
│   ├── rag_service.py
│   └── vector_store.py
├── .dockerignore
├── .env.example
├── .gitignore
├── Dockerfile
├── evaluation.py
├── evaluation_cases.json
├── README.md
└── requirements.txt
```

## Getting Started

### Run locally

```bash
git clone https://github.com/Romaan0504/Docu-sense-ai.git
cd Docu-sense-ai

python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
# macOS / Linux
# source .venv/bin/activate

pip install -r requirements.txt
```

Create a `.env` file in the project root (use `.env.example` as a reference):

```
GROQ_API_KEY=your_groq_api_key_here
```

Start the server:

```bash
uvicorn app.main:app --reload
```

- App: http://127.0.0.1:8000
- Interactive API docs: http://127.0.0.1:8000/docs

### Run with Docker

```bash
docker build -t docu-sense-ai .
docker run --env-file .env -p 8000:8000 -v "${PWD}/uploads:/app/uploads" -v "${PWD}/data:/app/data" docu-sense-ai
```

The mounted `uploads` and `data` folders keep your documents after the container stops.

## Evaluation

```bash
python evaluation.py
```

The script reads `evaluation_cases.json`, checks that the expected document content appears in the top retrieved results, and writes a report to `data/evaluation_results.json`.

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Demo interface |
| GET | `/health` | Health check |
| POST | `/api/documents/upload` | Upload, extract, chunk and index a PDF |
| GET | `/api/documents` | List uploaded documents |
| DELETE | `/api/documents/{document_id}` | Delete a document and all related data |
| GET | `/api/documents/{document_id}/extraction` | View page-level extracted text |
| GET | `/api/documents/{document_id}/chunks` | View generated chunks |
| POST | `/api/search` | Semantic search without LLM generation |
| POST | `/api/ask` | Ask a question using retrieved evidence |
| GET | `/api/history` | View recent questions and answers |
| PATCH | `/api/history/{history_id}/feedback` | Save answer feedback |

## Example Questions

Try these after uploading a policy or compliance PDF:

- What does the document say about protecting personal data?
- What rights do people have regarding their personal data?
- What does the cybersecurity framework say about governance?
- What does the document say about identifying cybersecurity risks?

## Limitations and Next Steps

This is a portfolio project, not a production system. Planned improvements:

- Relevance threshold before calling the LLM
- Document filters to search only selected PDFs
- OCR support for scanned PDFs
- Automated answer-faithfulness evaluation
- Authentication and per-user workspaces
- Background processing for large documents
- Cloud deployment with monitoring and logging

## What I Learned

- Designing an end-to-end RAG pipeline
- Handling file uploads and validation in FastAPI
- Preserving page metadata through extraction and chunking
- Using ChromaDB for semantic search
- Writing a strict grounding prompt for an LLM API
- Testing retrieval quality instead of judging a RAG app by how it looks
- Packaging a Python service with Docker

## Author

Built by [Romaan Shaikh](https://github.com/Romaan0504) as a hands-on Generative AI project.
