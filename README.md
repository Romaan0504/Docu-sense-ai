# DocuSense AI

> A document-grounded RAG assistant for reviewing policy, compliance, and contract PDFs with page-level citations.

![Python](https://img.shields.io/badge/Python-3.12-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688)
![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector%20Search-6E44FF)
![Groq](https://img.shields.io/badge/Groq-LLM%20Inference-orange)
![Docker](https://img.shields.io/badge/Docker-Containerized-2496ED)

## Why I Built This

Teams in HR, compliance, consulting, operations, and legal-support roles often need to find information buried inside long PDFs: employee handbooks, privacy policies, contracts, SOPs, and audit reports.

A normal chatbot may answer confidently without showing where its answer came from. This project focuses on a more trustworthy workflow:

1. Upload a PDF.
2. Extract its text page by page.
3. Split it into searchable chunks.
4. Retrieve the most relevant evidence with vector search.
5. Generate an answer only from that evidence.
6. Show the supporting filename, page number, and excerpt.

The goal is not to replace professional legal or compliance review. It is to help teams find relevant document evidence faster.

## Live Capabilities

- Upload text-based PDF documents up to 25 MB.
- Extract readable text page by page with PyPDF.
- Split long pages into overlapping chunks with LangChain Text Splitters.
- Store document chunks in ChromaDB for semantic search.
- Ask questions in plain English.
- Generate grounded answers using the Groq API.
- Display page-level source citations and source excerpts.
- Save uploaded-document metadata and question history in SQLite.
- Save helpful/unhelpful feedback for answers.
- Delete a document along with its PDF, extracted data, vector chunks, and SQLite record.
- Evaluate retrieval performance using a small local test dataset.
- Run locally or using Docker.

## Demo Workflow

```text
Upload PDF
   ↓
Extract page text
   ↓
Create overlapping chunks
   ↓
Index chunks in ChromaDB
   ↓
Retrieve relevant evidence
   ↓
Generate grounded answer with Groq
   ↓
Return answer + page-level citations
```

## Architecture

```text
Browser UI
HTML + CSS + JavaScript
   │
   ▼
FastAPI Backend
   │
   ├── PDF ingestion and validation
   ├── Text extraction with PyPDF
   ├── Chunking with LangChain Text Splitters
   ├── ChromaDB semantic retrieval
   ├── Groq grounded-answer generation
   └── SQLite document/history storage
```

## Tech Stack

| Layer | Tools Used |
|---|---|
| Backend API | Python, FastAPI, Uvicorn |
| Frontend | HTML, CSS, JavaScript |
| PDF extraction | PyPDF |
| Text chunking | LangChain Text Splitters |
| Vector database | ChromaDB |
| LLM inference | Groq API |
| Relational storage | SQLite |
| Environment variables | python-dotenv |
| Containerization | Docker |

## Key Design Decisions

### 1. Page-level citations instead of vague AI answers

Every answer includes the source filename, page number, and an excerpt from the retrieved document chunk. This lets a user verify the answer instead of trusting the model blindly.

### 2. Retrieval before generation

The LLM does not receive the entire PDF. It receives only the most relevant retrieved chunks. This follows the Retrieval-Augmented Generation pattern and keeps answers grounded in uploaded documents.

### 3. Explicit no-answer behavior

The system prompt instructs the LLM to respond with:

```text
I don't know based on the uploaded documents.
```

when the retrieved evidence does not clearly answer the question.

### 4. SQLite for practical application state

I used SQLite to store:

- Uploaded document metadata
- Question history
- Source count per answer
- Helpful/unhelpful feedback

This makes the application feel like a real internal-tool workflow rather than a one-time demo.

### 5. Retrieval evaluation

I created a small evaluation dataset to test whether expected PDFs are retrieved for known questions.

Latest local evaluation:

```text
Answerable retrieval tests: 4/4 passed
```

The evaluation also exposed a realistic RAG limitation: semantic search can still return the closest chunks for an unrelated question. This is why source citations and strict grounded-answer instructions matter.

## Project Structure

```text
docu-sense-ai/
│
├── app/
│   ├── static/
│   │   ├── app.js
│   │   └── styles.css
│   │
│   ├── templates/
│   │   └── index.html
│   │
│   ├── chunking_service.py
│   ├── database.py
│   ├── main.py
│   ├── pdf_service.py
│   ├── rag_service.py
│   └── vector_store.py
│
├── .dockerignore
├── .env.example
├── .gitignore
├── Dockerfile
├── evaluation.py
├── evaluation_cases.json
├── README.md
└── requirements.txt
```

## Local Setup

### 1. Clone the repository

```bash
git clone https://github.com/YOUR-USERNAME/docu-sense-ai.git
cd docu-sense-ai
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Add your Groq API key

Create a `.env` file in the root folder:

```env
GROQ_API_KEY=your_groq_api_key_here
```

Use `.env.example` as a reference. Never commit the real `.env` file.

### 5. Start the application

```bash
uvicorn app.main:app --reload
```

Open the website:

```text
http://127.0.0.1:8000
```

Open FastAPI documentation:

```text
http://127.0.0.1:8000/docs
```

## Docker Setup

Build the Docker image:

```bash
docker build -t docu-sense-ai .
```

Run the application:

```powershell
docker run --env-file .env -p 8000:8000 -v "${PWD}\uploads:/app/uploads" -v "${PWD}\data:/app/data" docu-sense-ai
```

Then open:

```text
http://127.0.0.1:8000
```

The mounted `uploads` and `data` folders keep local document data available after a container stops.

## Evaluation

The project includes a small retrieval evaluation file:

```text
evaluation_cases.json
```

Run it with:

```bash
python evaluation.py
```

The script checks whether the expected document content appears in the retrieved top results and saves a local JSON report under:

```text
data/evaluation_results.json
```

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Web application |
| `GET` | `/health` | API health check |
| `POST` | `/api/documents/upload` | Upload, extract, chunk, and index a PDF |
| `GET` | `/api/documents` | List uploaded documents |
| `DELETE` | `/api/documents/{document_id}` | Delete a document and its related stored data |
| `GET` | `/api/documents/{document_id}/extraction` | View page-level extracted text |
| `GET` | `/api/documents/{document_id}/chunks` | View generated chunks |
| `POST` | `/api/search` | Run semantic search without LLM generation |
| `POST` | `/api/ask` | Ask a question using retrieved document evidence |
| `GET` | `/api/history` | View recent questions and answers |
| `PATCH` | `/api/history/{history_id}/feedback` | Save answer feedback |

## Example Questions

Try these after uploading a policy or compliance PDF:

```text
What does the document say about protecting personal data?
```

```text
What rights do people have regarding their personal data?
```

```text
What does the cybersecurity framework say about governance?
```

```text
What does the document say about identifying cybersecurity risks?
```

## Known Limitations and Next Steps

This is a portfolio project and not a deployed enterprise system. Improvements I would make next:

- Add authentication and user-specific document workspaces.
- Add document filters so users can search only selected PDFs.
- Add a relevance threshold before calling the LLM.
- Add OCR support for scanned PDFs.
- Add automated answer-faithfulness evaluation.
- Add background processing for large documents.
- Add cloud deployment, monitoring, and error logging.
- Add role-based access controls and audit logs.

## What I Learned

While building this project, I practiced:

- Designing a complete Retrieval-Augmented Generation pipeline.
- Handling file uploads and validation in FastAPI.
- Extracting PDF content and preserving page metadata.
- Chunking long documents for better retrieval.
- Using ChromaDB for semantic similarity search.
- Integrating an LLM API with a strict grounding prompt.
- Building a frontend that consumes backend APIs.
- Using SQLite for application state and feedback.
- Testing retrieval quality instead of judging a RAG app only by appearance.
- Packaging a Python application with Docker.

## Author

Built by [Romaan Shaikh](https://github.com/Romaan0504) as a hands-on GenAI portfolio project.