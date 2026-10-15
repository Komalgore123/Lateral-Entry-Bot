# LateralEntryBot — Implementation Plan

## Top-Level Overview

Build a complete, greenfield Flask web application called **LateralEntryBot** — an AI-powered chatbot that answers questions about Direct Second Year (Lateral Entry) Engineering admission in Maharashtra. The bot uses Retrieval-Augmented Generation (RAG): it extracts text from uploaded official PDF brochures, splits it into chunks, retrieves the most relevant passages using TF-IDF, and passes those passages as context to the OpenAI API. Answers are grounded in the supplied documents, and source filenames + page numbers are always displayed. The UI is English-only, responsive, blue-and-white, and requires no JavaScript framework.

**Non-goals:**
- No database (in-memory document store only).
- No user authentication.
- No fine-tuning or embeddings (TF-IDF only).
- No collection of personal student data.

---

## Sub-Tasks

---

### Sub-Task 1 — Project Skeleton and Configuration Files

**Intent**
Create the folder structure, dependency manifest, environment configuration, Git hygiene files, and the README so that every subsequent sub-task has a stable scaffold to build on.

**Expected Outcomes**
- `requirements.txt` lists all runtime dependencies.
- `.env.example` documents every required/optional environment variable.
- `.gitignore` excludes `.env`, `__pycache__`, `venv/`, `data/documents/`, and `*.pyc`.
- `README.md` contains Windows PowerShell setup steps and run instructions.
- Empty `data/documents/` directory exists (with a `.gitkeep`).

**Todo List**
1. Create `requirements.txt` with: `flask`, `python-dotenv`, `pypdf`, `scikit-learn`, `openai`, `werkzeug`.
2. Create `.env.example` with placeholders for `OPENAI_API_KEY`, `OPENAI_MODEL` (default `gpt-4o-mini`), `FLASK_SECRET_KEY`, `MAX_UPLOAD_MB`.
3. Create `.gitignore`.
4. Create `data/documents/.gitkeep`.
5. Write `README.md` with: project description, PowerShell setup commands, how to configure `.env`, how to run, and usage notes.

**Relevant Context**
- No existing files; pure greenfield.
- Windows PowerShell is the target shell for all commands.

**Status:** [ ] pending

---

### Sub-Task 2 — RAG Engine (`rag.py`)

**Intent**
Implement all document-processing and AI-answer logic in a single, well-commented module that `app.py` will import. This is the core intelligence of the bot.

**Expected Outcomes**
- `extract_text_from_pdf(filepath)` returns a list of `{"page": int, "text": str}` dicts using `pypdf`.
- `chunk_text(pages, chunk_size=500, overlap=50)` splits page text into overlapping word-level chunks, each carrying `page` and `source` (filename) metadata.
- `DocumentStore` class holds all chunks in memory, exposes `add_document(filename, filepath)` and `search(query, top_k=5)`.
- `search` builds a TF-IDF matrix over all stored chunks and returns the top-k most relevant chunks with their `source` and `page`.
- `generate_answer(query, chunks)` calls the OpenAI Chat Completions API with a strict system prompt that: instructs the model to answer only from the provided excerpts; tells it to say it cannot verify the information and link to `https://cetcell.mahacet.org/` if the answer is not in the excerpts; forbids inventing dates, fees, cutoffs, or eligibility criteria; includes a disclaimer that uploaded PDFs are not verified official documents.
- `generate_answer` returns `{"answer": str, "sources": [{"source": filename, "page": int}]}`.
- If no documents are loaded, `search` returns an empty list and `generate_answer` returns a clear "no documents uploaded" message without calling the API.
- The OpenAI API key is read from the environment; if missing, a descriptive `ValueError` is raised at call time (not at import time).

**Todo List**
1. Implement `extract_text_from_pdf` using `pypdf.PdfReader`.
2. Implement `chunk_text` with configurable `chunk_size` and `overlap`.
3. Implement `DocumentStore` with in-memory list and `add_document` / `search` methods.
4. Implement TF-IDF search using `sklearn.feature_extraction.text.TfidfVectorizer` + cosine similarity via `linear_kernel`.
5. Implement `generate_answer` with the strict RAG system prompt.
6. Handle the "no documents" and "missing API key" edge cases explicitly.

**Relevant Context**
- `pypdf` (not `PyPDF2`) is the modern package; use `PdfReader.pages[i].extract_text()`.
- `TfidfVectorizer` must be re-fitted on every search call because documents are added incrementally.
- OpenAI SDK v1+: use `openai.OpenAI(api_key=...)` client pattern.

**Status:** [ ] pending

---

### Sub-Task 3 — Flask Backend (`app.py`)

**Intent**
Wire HTTP routes that serve the frontend, accept chat questions, and handle PDF uploads. All secrets stay server-side.

**Expected Outcomes**
- `GET /` serves `templates/index.html`.
- `POST /chat` accepts JSON `{"question": str}`, validates non-empty input, calls `rag.py` search + generate, returns JSON `{"answer": str, "sources": [...]}`. Returns HTTP 400 for empty/missing question.
- `POST /upload` accepts a multipart file, validates extension (`.pdf` only) and size (`MAX_UPLOAD_MB`, default 10 MB), saves to `data/documents/`, calls `store.add_document()`, returns JSON `{"message": str, "filename": str}`. Returns HTTP 400/413 for invalid input.
- `GET /documents` returns JSON list of currently loaded document names.
- App loads `.env` via `python-dotenv` at startup.
- `FLASK_SECRET_KEY` is used for the Flask secret key.
- No API key or sensitive config is ever returned to the client.

**Todo List**
1. Create `app.py` importing `rag.DocumentStore` and initialising a module-level `store` instance.
2. Load `.env` with `load_dotenv()` at top of file.
3. Implement `GET /` route.
4. Implement `POST /chat` with input validation and error handling.
5. Implement `POST /upload` with file-type and size validation; save with `werkzeug.utils.secure_filename`.
6. Implement `GET /documents` helper route.
7. Set `app.config["MAX_CONTENT_LENGTH"]` from `MAX_UPLOAD_MB` env var.

**Relevant Context**
- Use `werkzeug.utils.secure_filename` to sanitise uploaded filenames.
- `app.config["MAX_CONTENT_LENGTH"]` enforces the upload size limit at the Flask layer.
- The `store` object is shared across requests (single-process dev server is sufficient).

**Status:** [ ] pending

---

### Sub-Task 4 — Frontend HTML (`templates/index.html`)

**Intent**
Create a complete single-page chatbot UI with FAQ quick-buttons, a chat window, a message input, and a PDF upload section. No JavaScript framework, no inline secrets.

**Expected Outcomes**
- Page title and heading: "LateralEntryBot — Lateral Entry Admission Assistant".
- Chat window displays bot and user messages with distinct styling.
- FAQ buttons (at minimum): Eligibility, Required Documents, CAP Rounds, Option Form, Admission Process, Important Dates.
- Text input + Send button for free-text questions.
- PDF upload section with a file picker and Upload button.
- Loaded documents list panel showing filenames returned by `GET /documents`.
- Disclaimer banner: "Always verify information against the official CET Cell website: cetcell.mahacet.org".
- All chat API calls go to `/chat`; all upload calls go to `/upload` — no API keys in JS.
- Links external CSS (`/static/style.css`) and JS (`/static/script.js`).

**Todo List**
1. Write the full HTML skeleton with `<head>` meta viewport for responsiveness.
2. Add the disclaimer banner at the top.
3. Add the FAQ button row.
4. Add the chat window `<div>` and message input row.
5. Add the PDF upload section.
6. Add the loaded-documents list panel.
7. Link stylesheet and script.

**Relevant Context**
- Jinja2 templating is available but not required for this static page.
- The script must be linked at the bottom of `<body>` so DOM is ready.

**Status:** [ ] pending

---

### Sub-Task 5 — Stylesheet (`static/style.css`)

**Intent**
Provide a clean, professional, blue-and-white responsive design that works on both desktop and mobile.

**Expected Outcomes**
- Primary colour: `#1a73e8` (blue); accent white/light grey backgrounds.
- Chat bubbles: user messages right-aligned blue, bot messages left-aligned white with a border.
- FAQ buttons styled as pill chips, wrapping on small screens.
- Upload section visually separated.
- Responsive layout: single-column on mobile (`max-width: 768px`).
- Disclaimer banner: yellow/amber background, clearly visible.
- Smooth scroll on the chat window.
- Loading indicator style (spinner or "…" bubble) for while the bot is thinking.

**Todo List**
1. Define CSS variables for brand colours.
2. Style the page layout (flexbox column).
3. Style the chat window and message bubbles.
4. Style FAQ buttons.
5. Style the upload section and document list.
6. Style the disclaimer banner.
7. Add media query for mobile.
8. Add `.typing` animation class for the loading indicator.

**Relevant Context**
- No CSS framework — pure vanilla CSS.
- Use `overflow-y: auto` on the chat window to enable scrolling.

**Status:** [ ] pending

---

### Sub-Task 6 — Frontend JavaScript (`static/script.js`)

**Intent**
Handle all user interactions: sending questions, displaying messages, uploading PDFs, showing sources, and managing the FAQ buttons — all via `fetch` calls to the Flask backend.

**Expected Outcomes**
- `sendMessage(text)` POSTs to `/chat`, shows a typing indicator while waiting, then renders the answer and source list.
- Sources displayed as "📄 filename.pdf, page N" badges below the answer.
- FAQ buttons call `sendMessage` with their predefined question text.
- Send button and Enter key both trigger `sendMessage`.
- Empty input is rejected client-side with a visible message (not just disabled button).
- `uploadPDF()` POSTs to `/upload` as `multipart/form-data`, shows success/error, then refreshes the documents list.
- `loadDocuments()` fetches `GET /documents` and renders filenames in the panel.
- `loadDocuments()` is called on page load.
- All errors from the server are displayed to the user in plain English.
- No API keys anywhere in this file.

**Todo List**
1. Implement `addMessage(role, html)` to append a message bubble to the chat window and scroll to bottom.
2. Implement `sendMessage(text)` with fetch, typing indicator, and error handling.
3. Implement source-badge rendering from the `sources` array.
4. Wire FAQ buttons via `querySelectorAll`.
5. Wire Send button click and Enter keypress.
6. Implement `uploadPDF()` with file validation feedback.
7. Implement `loadDocuments()` and call it on `DOMContentLoaded`.

**Relevant Context**
- `fetch` with `method: "POST"`, `Content-Type: application/json`, and `JSON.stringify` body for `/chat`.
- `fetch` with `FormData` (no explicit Content-Type header) for `/upload`.
- Use `innerHTML` carefully — only bot-generated HTML from the server's answer text after escaping.

**Status:** [ ] pending

---

### Sub-Task 7 — Validation, Testing, and Documentation

**Intent**
Verify correctness of all files, run the described test scenarios, report results honestly, fix any errors found, and provide final run instructions.

**Expected Outcomes**
- Python syntax check: `python -m py_compile app.py rag.py` passes with no errors.
- Import check: all imports in both `.py` files resolve to packages in `requirements.txt`.
- Manual test scenarios documented with actual outcomes:
  1. Empty question → HTTP 400, error shown in UI.
  2. No documents loaded → bot says it has no documents, no API call made.
  3. PDF upload → file appears in documents list.
  4. Relevant retrieval → uploaded PDF text is retrieved for a matching question.
  5. Source references → answer displays filename + page badges.
  6. Missing API key → descriptive error shown, app does not crash.
- Any test that cannot be run (e.g., live OpenAI call without a key) is clearly marked "cannot run without credentials" rather than fabricated.
- README updated if setup commands need adjustment based on test findings.

**Todo List**
1. Read all generated files and check for syntax errors and mismatched imports.
2. Run `python -m py_compile app.py rag.py` (via execute_command).
3. Document test scenario results honestly.
4. Fix any errors found.
5. Confirm final PowerShell run instructions.

**Relevant Context**
- Tests are static/dry-run where live credentials are unavailable.
- Do not invent passing results for tests that require a live OpenAI key.

**Status:** [ ] pending

---

## Architecture Diagram

```
Browser
  │
  ├─ GET /          → index.html
  ├─ POST /chat     → app.py → rag.py (TF-IDF search + OpenAI) → JSON response
  ├─ POST /upload   → app.py → rag.py (PDF extract + chunk + store)
  └─ GET /documents → app.py → DocumentStore list
```

---

## File Map

| File | Purpose |
|---|---|
| `app.py` | Flask routes, request validation, secret loading |
| `rag.py` | PDF extraction, chunking, TF-IDF search, OpenAI call |
| `templates/index.html` | Single-page chatbot UI |
| `static/style.css` | Blue-and-white responsive design |
| `static/script.js` | Chat, FAQ, upload, source display logic |
| `requirements.txt` | Runtime Python dependencies |
| `.env.example` | Environment variable documentation |
| `.gitignore` | Excludes secrets, venv, pycache |
| `README.md` | Setup and run instructions |
| `data/documents/.gitkeep` | Ensures upload folder exists in repo |
