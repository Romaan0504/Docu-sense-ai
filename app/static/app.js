// Select important HTML elements once
const pdfFile = document.getElementById("pdfFile");
const dropZone = document.getElementById("dropZone");
const selectedFile = document.getElementById("selectedFile");
const uploadButton = document.getElementById("uploadButton");
const uploadStatus = document.getElementById("uploadStatus");

const documentCount = document.getElementById("documentCount");
const documentsList = document.getElementById("documentsList");

const questionInput = document.getElementById("questionInput");
const characterCount = document.getElementById("characterCount");
const askButton = document.getElementById("askButton");
const questionStatus = document.getElementById("questionStatus");

const emptyAnswerState = document.getElementById("emptyAnswerState");
const answerCard = document.getElementById("answerCard");
const displayQuestion = document.getElementById("displayQuestion");
const answerText = document.getElementById("answerText");
const sourcesList = document.getElementById("sourcesList");

const thumbsUpButton = document.getElementById("thumbsUpButton");
const thumbsDownButton = document.getElementById("thumbsDownButton");

const refreshHistoryButton = document.getElementById("refreshHistoryButton");
const historyList = document.getElementById("historyList");

// Remember the latest answered question for feedback
let currentHistoryId = null;


// Show a status message below upload or question areas
function setStatus(element, message, type = "") {
    element.textContent = message;
    element.className = "status-message";

    if (type) {
        element.classList.add(type);
    }
}


// Read a useful error message from FastAPI
async function getErrorMessage(response) {
    try {
        const errorData = await response.json();
        return errorData.detail || "Something went wrong.";
    } catch {
        return "Something went wrong.";
    }
}


// Show selected PDF name before upload
function showSelectedFile(file) {
    if (!file) {
        selectedFile.textContent = "";
        selectedFile.classList.add("hidden");
        uploadButton.disabled = true;
        return;
    }

    selectedFile.textContent = `Selected: ${file.name}`;
    selectedFile.classList.remove("hidden");
    uploadButton.disabled = false;
}


// Check the selected file
function chooseFile(file) {
    if (!file) {
        return;
    }

    if (!file.name.toLowerCase().endsWith(".pdf")) {
        setStatus(uploadStatus, "Please choose a PDF file.", "error");
        pdfFile.value = "";
        showSelectedFile(null);
        return;
    }

    if (file.size > 25 * 1024 * 1024) {
        setStatus(uploadStatus, "PDF must be smaller than 25 MB.", "error");
        pdfFile.value = "";
        showSelectedFile(null);
        return;
    }

    setStatus(uploadStatus, "");
    showSelectedFile(file);
}


// Choose a PDF using the normal file picker
pdfFile.addEventListener("change", () => {
    chooseFile(pdfFile.files[0]);
});


// Support drag-and-drop PDFs
dropZone.addEventListener("dragover", (event) => {
    event.preventDefault();
    dropZone.classList.add("drag-active");
});


dropZone.addEventListener("dragleave", () => {
    dropZone.classList.remove("drag-active");
});


dropZone.addEventListener("drop", (event) => {
    event.preventDefault();
    dropZone.classList.remove("drag-active");

    const droppedFile = event.dataTransfer.files[0];

    if (!droppedFile) {
        return;
    }

    // Put dropped file into the real file input
    const dataTransfer = new DataTransfer();
    dataTransfer.items.add(droppedFile);
    pdfFile.files = dataTransfer.files;

    chooseFile(droppedFile);
});


// Upload selected PDF to FastAPI
uploadButton.addEventListener("click", async () => {
    const file = pdfFile.files[0];

    if (!file) {
        setStatus(uploadStatus, "Select a PDF first.", "error");
        return;
    }

    uploadButton.disabled = true;
    uploadButton.textContent = "Uploading and indexing...";

    setStatus(
        uploadStatus,
        "Extracting text, creating chunks, and indexing document..."
    );

    const formData = new FormData();
    formData.append("file", file);

    try {
        const response = await fetch("/api/documents/upload", {
            method: "POST",
            body: formData,
        });

        if (!response.ok) {
            throw new Error(await getErrorMessage(response));
        }

        const result = await response.json();

        setStatus(
            uploadStatus,
            `${result.original_filename} is ready — ` +
            `${result.pages_with_text} pages and ` +
            `${result.chunks_created} searchable sections created.`,
            "success"
        );

        // Clear selected file after a successful upload
        pdfFile.value = "";
        showSelectedFile(null);

        // Refresh uploaded-document library
        await loadDocuments();

    } catch (error) {
        setStatus(uploadStatus, error.message, "error");
    } finally {
        uploadButton.textContent = "Upload and index";
        uploadButton.disabled = !pdfFile.files[0];
    }
});


// Load and show all uploaded documents
async function loadDocuments() {
    documentsList.innerHTML = `
        <p class="empty-message">Loading documents...</p>
    `;

    try {
        const response = await fetch("/api/documents");

        if (!response.ok) {
            throw new Error("Could not load uploaded documents.");
        }

        const result = await response.json();

        documentCount.textContent = result.count;

        if (result.documents.length === 0) {
            documentsList.innerHTML = `
                <p class="empty-message">
                    No PDFs uploaded yet.
                </p>
            `;
            return;
        }

        // Clear previous document cards
        documentsList.innerHTML = "";

        // IMPORTANT: uploadedDocument is the document data.
        // window.document is the browser's real HTML document object.
        result.documents.forEach((uploadedDocument) => {
            const documentItem = window.document.createElement("article");
            documentItem.className = "document-item";

            const documentName = window.document.createElement("p");
            documentName.className = "document-name";
            documentName.textContent = uploadedDocument.original_filename;

            const documentMeta = window.document.createElement("p");
            documentMeta.className = "document-meta";
            documentMeta.textContent =
                `${uploadedDocument.pages_with_text} pages · ` +
                `${uploadedDocument.chunks_created} sections`;

            const actions = window.document.createElement("div");
            actions.className = "document-actions";

            const deleteButton = window.document.createElement("button");
            deleteButton.className = "delete-button";
            deleteButton.textContent = "Delete document";

            deleteButton.addEventListener("click", async () => {
                await deleteDocument(
                    uploadedDocument.document_id,
                    uploadedDocument.original_filename
                );
            });

            actions.appendChild(deleteButton);
            documentItem.appendChild(documentName);
            documentItem.appendChild(documentMeta);
            documentItem.appendChild(actions);

            documentsList.appendChild(documentItem);
        });

    } catch (error) {
        documentsList.innerHTML = `
            <p class="empty-message">
                ${error.message}
            </p>
        `;
    }
}


// Delete one document and its vectors/files
async function deleteDocument(documentId, filename) {
    const shouldDelete = window.confirm(
        `Delete "${filename}" and all of its extracted data?`
    );

    if (!shouldDelete) {
        return;
    }

    try {
        const response = await fetch(`/api/documents/${documentId}`, {
            method: "DELETE",
        });

        if (!response.ok) {
            throw new Error(await getErrorMessage(response));
        }

        await loadDocuments();

        setStatus(
            uploadStatus,
            `"${filename}" was deleted.`,
            "success"
        );

    } catch (error) {
        setStatus(uploadStatus, error.message, "error");
    }
}


// Update the question character counter
questionInput.addEventListener("input", () => {
    characterCount.textContent = `${questionInput.value.length} / 500`;
});


// Submit using Ctrl + Enter
questionInput.addEventListener("keydown", (event) => {
    if (event.ctrlKey && event.key === "Enter") {
        askButton.click();
    }
});


// Ask a question using the RAG API
askButton.addEventListener("click", async () => {
    const question = questionInput.value.trim();

    if (question.length < 3) {
        setStatus(
            questionStatus,
            "Write a question with at least 3 characters.",
            "error"
        );
        return;
    }

    askButton.disabled = true;
    askButton.textContent = "Finding evidence...";

    setStatus(
        questionStatus,
        "Retrieving relevant sections and preparing an answer..."
    );

    try {
        const response = await fetch("/api/ask", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                question: question,
            }),
        });

        if (!response.ok) {
            throw new Error(await getErrorMessage(response));
        }

        const result = await response.json();

        // Show answer area
        emptyAnswerState.classList.add("hidden");
        answerCard.classList.remove("hidden");

        // Use textContent for safe text display
        displayQuestion.textContent = result.question;
        answerText.textContent = result.answer;

        // Save ID for thumbs-up/down feedback
        currentHistoryId = result.history_id;

        thumbsUpButton.disabled = false;
        thumbsDownButton.disabled = false;

        thumbsUpButton.classList.remove("selected");
        thumbsDownButton.classList.remove("selected");

        // Show citations
        renderSources(result.sources);

        setStatus(
            questionStatus,
            "Answer generated from uploaded document evidence.",
            "success"
        );

        await loadHistory();

    } catch (error) {
        setStatus(questionStatus, error.message, "error");
    } finally {
        askButton.disabled = false;
        askButton.textContent = "Ask documents";
    }
});


// Render the source citations below an answer
function renderSources(sources) {
    sourcesList.innerHTML = "";

    if (!sources || sources.length === 0) {
        sourcesList.innerHTML = `
            <p class="empty-message">
                No matching source was found in uploaded documents.
            </p>
        `;
        return;
    }

    sources.forEach((source) => {
        const sourceItem = window.document.createElement("article");
        sourceItem.className = "source-item";

        const sourceTitle = window.document.createElement("p");
        sourceTitle.className = "source-title";
        sourceTitle.textContent =
            `${source.source_file} · Page ${source.page_number}`;

        const sourceExcerpt = window.document.createElement("p");
        sourceExcerpt.className = "source-excerpt";
        sourceExcerpt.textContent = source.excerpt;

        sourceItem.appendChild(sourceTitle);
        sourceItem.appendChild(sourceExcerpt);

        sourcesList.appendChild(sourceItem);
    });
}


// Send helpful/not helpful feedback to SQLite
async function sendFeedback(feedback) {
    if (!currentHistoryId) {
        return;
    }

    try {
        const response = await fetch(
            `/api/history/${currentHistoryId}/feedback`,
            {
                method: "PATCH",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    feedback: feedback,
                }),
            }
        );

        if (!response.ok) {
            throw new Error(await getErrorMessage(response));
        }

        thumbsUpButton.classList.toggle(
            "selected",
            feedback === "up"
        );

        thumbsDownButton.classList.toggle(
            "selected",
            feedback === "down"
        );

    } catch (error) {
        setStatus(questionStatus, error.message, "error");
    }
}


// Connect feedback buttons
thumbsUpButton.addEventListener("click", () => {
    sendFeedback("up");
});


thumbsDownButton.addEventListener("click", () => {
    sendFeedback("down");
});


// Load saved question history
async function loadHistory() {
    try {
        const response = await fetch("/api/history");

        if (!response.ok) {
            throw new Error("Could not load question history.");
        }

        const result = await response.json();

        if (result.history.length === 0) {
            historyList.innerHTML = `
                <p class="empty-message">
                    No questions asked yet.
                </p>
            `;
            return;
        }

        historyList.innerHTML = "";

        result.history.forEach((historyItemData) => {
            const historyItem = window.document.createElement("article");
            historyItem.className = "history-item";

            const historyQuestion = window.document.createElement("p");
            historyQuestion.className = "history-question";
            historyQuestion.textContent = historyItemData.question;

            const historyMeta = window.document.createElement("p");
            historyMeta.className = "history-meta";

            const feedbackText = historyItemData.feedback
                ? ` · Feedback: ${historyItemData.feedback}`
                : "";

            historyMeta.textContent =
                `${historyItemData.source_count} source(s) used` +
                feedbackText;

            historyItem.appendChild(historyQuestion);
            historyItem.appendChild(historyMeta);

            historyList.appendChild(historyItem);
        });

    } catch (error) {
        historyList.innerHTML = `
            <p class="empty-message">
                ${error.message}
            </p>
        `;
    }
}


// Refresh history manually
refreshHistoryButton.addEventListener("click", loadHistory);


// Load current data when the website opens
loadDocuments();
loadHistory();