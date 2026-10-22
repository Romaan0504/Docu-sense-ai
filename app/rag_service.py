# Import os to read the API key from .env
import os

# Import Path to find the project folder
from pathlib import Path

# Import dotenv to load the hidden .env file
from dotenv import load_dotenv

# Import Groq client for LLM responses
from groq import Groq


# Find the main project folder
PROJECT_DIR = Path(__file__).resolve().parent.parent

# Load variables from Docu-sense-ai/.env
load_dotenv(PROJECT_DIR / ".env")


def generate_grounded_answer(
    question: str,
    retrieved_chunks: list[dict],
) -> str:
    """Generate an answer using only retrieved document text."""

    # Read the private Groq key
    api_key = os.getenv("GROQ_API_KEY")

    # Stop safely if the user forgot the key
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is missing. Add it to the .env file."
        )

    # Connect to Groq
    groq_client = Groq(api_key=api_key)

    # Build a clear context block for the AI model
    context_parts = []

    for number, chunk in enumerate(retrieved_chunks, start=1):
        context_parts.append(
            f"""
[Source {number}]
File: {chunk["source_file"]}
Page: {chunk["page_number"]}
Excerpt:
{chunk["text"]}
"""
        )

    # Join all retrieved chunks into one context string
    context = "\n".join(context_parts)

    # Ask the LLM to answer only from the retrieved document excerpts
    response = groq_client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {
                "role": "system",
                "content": """
You are DocuSense AI, a high-trust policy, compliance, and contract
document assistant.

Answer ONLY from the supplied source excerpts.

Rules:
1. Never use outside knowledge.
2. Never guess or invent a fact.
3. If the sources do not clearly answer the question, say exactly:
"I don't know based on the uploaded documents."
4. Do not give legal, compliance, HR, or contract advice beyond the sources.
5. Keep the answer concise, factual, and easy to understand.
6. Do not claim a source says something unless it is present in that source.
""",
            },
            {
                "role": "user",
                "content": f"""
Question:
{question}

Source excerpts:
{context}
""",
            },
        ],
    )

    # Return only the AI's answer text
    return response.choices[0].message.content