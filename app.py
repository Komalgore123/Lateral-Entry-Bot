"""
app.py — Flask application entry point.
Defines routes for the chat API and PDF upload API.
"""

import os
from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from rag import RAGEngine

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# ── Configuration ──────────────────────────────────────────────────────────────
UPLOAD_FOLDER = os.path.join("data", "documents")
ALLOWED_EXTENSIONS = {"pdf"}
MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB limit

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

# Create the upload folder if it does not exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialise the RAG engine (shared across requests)
rag_engine = RAGEngine(upload_folder=UPLOAD_FOLDER)


def allowed_file(filename: str) -> bool:
    """Return True only if the filename has a .pdf extension."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    """Serve the main chatbot page."""
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    """
    Accept a JSON body: {"question": "..."}
    Return:  {"answer": "...", "sources": [...]}
    """
    data = request.get_json(silent=True)

    if not data or not data.get("question", "").strip():
        return jsonify({"error": "Please enter a question before sending."}), 400

    question = data["question"].strip()

    try:
        answer, sources = rag_engine.answer(question)
        return jsonify({"answer": answer, "sources": sources})
    except ValueError as exc:
        # Raised when the OpenAI API key is missing
        return jsonify({"error": str(exc)}), 503
    except Exception as exc:  # pylint: disable=broad-except
        return jsonify({"error": f"An unexpected error occurred: {exc}"}), 500


@app.route("/api/upload", methods=["POST"])
def upload_pdf():
    """
    Accept a multipart/form-data request with a 'file' field.
    Save the PDF to the upload folder and index it.
    """
    if "file" not in request.files:
        return jsonify({"error": "No file part in the request."}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"error": "No file selected."}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Only PDF files are allowed."}), 400

    filename = secure_filename(file.filename)
    save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(save_path)

    # Index the newly uploaded document
    try:
        chunk_count = rag_engine.index_file(save_path)
        return jsonify({
            "message": (
                f"'{filename}' uploaded and indexed successfully "
                f"({chunk_count} text chunks created). "
                "Remember to verify this document against the official CET Cell "
                "website at https://cetcell.mahacet.org/ before relying on it."
            ),
            "filename": filename,
            "chunks": chunk_count,
        })
    except Exception as exc:  # pylint: disable=broad-except
        return jsonify({"error": f"Failed to process PDF: {exc}"}), 500


@app.route("/api/documents", methods=["GET"])
def list_documents():
    """Return a list of currently indexed document filenames."""
    docs = rag_engine.list_documents()
    return jsonify({"documents": docs})


# ── Error handlers ─────────────────────────────────────────────────────────────

@app.errorhandler(413)
def request_entity_too_large(_error):
    return jsonify({"error": "File is too large. Maximum allowed size is 10 MB."}), 413


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Index any PDFs already present in the documents folder on startup
    rag_engine.index_all()
    app.run(debug=True, port=5000)
