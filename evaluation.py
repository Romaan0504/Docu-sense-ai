# Import JSON to read evaluation questions and save results
import json

# Import Path to locate files safely
from pathlib import Path

# Import the semantic search function from our RAG project
from app.vector_store import search_chunks


# Find the main Docu-sense-ai project folder
PROJECT_DIR = Path(__file__).resolve().parent

# Evaluation questions live here
EVALUATION_CASES_PATH = PROJECT_DIR / "evaluation_cases.json"

# Save results here after running the evaluation
RESULTS_PATH = PROJECT_DIR / "data" / "evaluation_results.json"


def load_evaluation_cases() -> list[dict]:
    """Read test questions from evaluation_cases.json."""

    # Stop with a helpful error if file is missing
    if not EVALUATION_CASES_PATH.exists():
        raise FileNotFoundError(
            "evaluation_cases.json was not found."
        )

    # Read and convert JSON into Python data
    return json.loads(
        EVALUATION_CASES_PATH.read_text(encoding="utf-8")
    )


def text_contains_expected_keyword(
    retrieved_results: list[dict],
    expected_keywords: list[str],
) -> bool:
    """Check whether retrieved text contains at least one expected keyword."""

    # For no-answer cases, retrieval is bad if it finds lots of evidence
    if not expected_keywords:
        return len(retrieved_results) == 0

    # Join all retrieved chunks into one lower-case text block
    retrieved_text = " ".join(
        result["text"].lower()
        for result in retrieved_results
    )

    # Return True when at least one expected keyword appears
    return any(
        keyword.lower() in retrieved_text
        for keyword in expected_keywords
    )


def run_evaluation() -> None:
    """Run every retrieval test and calculate a simple score."""

    # Load all test cases
    evaluation_cases = load_evaluation_cases()

    # Store detailed results here
    results = []

    # Count successful retrievals
    passed_count = 0

    print("\nStarting DocuSense AI retrieval evaluation...\n")

    # Test each question one by one
    for test_case in evaluation_cases:
        question = test_case["question"]
        expected_keywords = test_case["expected_keywords"]

        # Retrieve the top four most relevant chunks
        retrieved_results = search_chunks(
            question=question,
            n_results=4,
        )

        # Check whether expected evidence appeared
        passed = text_contains_expected_keyword(
            retrieved_results=retrieved_results,
            expected_keywords=expected_keywords,
        )

        # Add one point for a passed test
        if passed:
            passed_count += 1

        # Create a compact source list
        sources = [
            {
                "file": result["source_file"],
                "page": result["page_number"],
                "distance": result["distance"],
            }
            for result in retrieved_results
        ]

        # Save detailed result for GitHub/demo evidence
        result = {
            "id": test_case["id"],
            "question": question,
            "expected_keywords": expected_keywords,
            "passed": passed,
            "retrieved_chunk_count": len(retrieved_results),
            "sources": sources,
        }

        results.append(result)

        # Print readable terminal output
        status = "PASS" if passed else "FAIL"

        print(f"[{status}] {test_case['id']}")
        print(f"Question: {question}")
        print(f"Retrieved chunks: {len(retrieved_results)}")

        if sources:
            print(
                f"Top source: {sources[0]['file']} "
                f"(page {sources[0]['page']})"
            )

        print()

    # Calculate percentage score
    total_cases = len(evaluation_cases)

    score_percentage = round(
        (passed_count / total_cases) * 100,
        2,
    ) if total_cases else 0

    # Create final report object
    report = {
        "project": "DocuSense AI",
        "evaluation_type": "keyword-based retrieval evaluation",
        "total_cases": total_cases,
        "passed_cases": passed_count,
        "failed_cases": total_cases - passed_count,
        "retrieval_score_percentage": score_percentage,
        "results": results,
    }

    # Ensure data folder exists
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Save report locally
    RESULTS_PATH.write_text(
        json.dumps(report, indent=4),
        encoding="utf-8",
    )

    # Print final summary
    print("-" * 55)
    print(f"Final retrieval score: {score_percentage}%")
    print(f"Passed: {passed_count}/{total_cases}")
    print(f"Saved detailed report: {RESULTS_PATH}")
    print("-" * 55)


# Run evaluation only when this file is executed directly
if __name__ == "__main__":
    run_evaluation()