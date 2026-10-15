/**
 * script.js — Frontend logic for LateralEntryBot.
 *
 * Handles:
 *  - Chat form submission and message rendering
 *  - FAQ quick-question buttons
 *  - PDF upload with validation
 *  - Indexed document list refresh
 */

"use strict";

// ── DOM references ─────────────────────────────────────────────────────────────
const chatForm      = document.getElementById("chatForm");
const questionInput = document.getElementById("questionInput");
const chatWindow    = document.getElementById("chatWindow");
const sendBtn       = document.getElementById("sendBtn");
const charCount     = document.getElementById("charCount");

const pdfInput      = document.getElementById("pdfInput");
const fileLabel     = document.getElementById("fileLabel");
const uploadBtn     = document.getElementById("uploadBtn");
const uploadStatus  = document.getElementById("uploadStatus");

const docList       = document.getElementById("docList");
const refreshDocsBtn = document.getElementById("refreshDocsBtn");

// ── Character counter ──────────────────────────────────────────────────────────
questionInput.addEventListener("input", () => {
  const len = questionInput.value.length;
  charCount.textContent = `${len} / 1000`;
  charCount.style.color = len > 900 ? "#b91c1c" : "";
});

// Update file-label text when the user picks a file
pdfInput.addEventListener("change", () => {
  fileLabel.textContent = pdfInput.files.length > 0
    ? pdfInput.files[0].name
    : "Choose PDF file…";
});

// Allow sending with Enter (Shift+Enter for new line)
questionInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    chatForm.dispatchEvent(new Event("submit", { cancelable: true, bubbles: true }));
  }
});

// ── Chat form submission ───────────────────────────────────────────────────────
chatForm.addEventListener("submit", async (e) => {
  e.preventDefault();

  const question = questionInput.value.trim();
  if (!question) {
    shakeInput(questionInput);
    return;
  }

  // Render user message
  appendMessage("user", escapeHtml(question));
  questionInput.value = "";
  charCount.textContent = "0 / 1000";

  // Show typing indicator
  const typingId = appendTyping();
  sendBtn.disabled = true;

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });

    const data = await res.json();
    removeTyping(typingId);

    if (!res.ok || data.error) {
      appendError(data.error || "An unexpected error occurred.");
    } else {
      appendBotMessage(data.answer, data.sources || []);
    }
  } catch (err) {
    removeTyping(typingId);
    appendError("Could not reach the server. Please check your connection.");
  } finally {
    sendBtn.disabled = false;
    questionInput.focus();
  }
});

// ── FAQ buttons ────────────────────────────────────────────────────────────────
document.querySelectorAll(".faq-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    questionInput.value = btn.dataset.q;
    charCount.textContent = `${btn.dataset.q.length} / 1000`;
    questionInput.focus();
    chatForm.dispatchEvent(new Event("submit", { cancelable: true, bubbles: true }));
  });
});

// ── PDF upload ─────────────────────────────────────────────────────────────────
uploadBtn.addEventListener("click", async () => {
  const file = pdfInput.files[0];

  if (!file) {
    showUploadStatus("Please choose a PDF file first.", "error");
    return;
  }

  if (!file.name.toLowerCase().endsWith(".pdf")) {
    showUploadStatus("Only PDF files are allowed.", "error");
    return;
  }

  const MAX_MB = 10;
  if (file.size > MAX_MB * 1024 * 1024) {
    showUploadStatus(`File is too large. Maximum size is ${MAX_MB} MB.`, "error");
    return;
  }

  const formData = new FormData();
  formData.append("file", file);

  uploadBtn.disabled = true;
  showUploadStatus("Uploading and indexing…", "");

  try {
    const res = await fetch("/api/upload", {
      method: "POST",
      body: formData,
    });

    const data = await res.json();

    if (!res.ok || data.error) {
      showUploadStatus(data.error || "Upload failed.", "error");
    } else {
      showUploadStatus(data.message, "success");
      pdfInput.value = "";
      fileLabel.textContent = "Choose PDF file…";
      loadDocumentList();
    }
  } catch (err) {
    showUploadStatus("Could not reach the server. Please check your connection.", "error");
  } finally {
    uploadBtn.disabled = false;
  }
});

// ── Document list ──────────────────────────────────────────────────────────────
refreshDocsBtn.addEventListener("click", loadDocumentList);

async function loadDocumentList() {
  try {
    const res = await fetch("/api/documents");
    const data = await res.json();
    renderDocList(data.documents || []);
  } catch (_err) {
    // Silently ignore network errors for the doc list refresh
  }
}

function renderDocList(docs) {
  docList.innerHTML = "";
  if (!docs || docs.length === 0) {
    const li = document.createElement("li");
    li.className = "empty-msg";
    li.textContent = "No documents uploaded yet.";
    docList.appendChild(li);
    return;
  }
  docs.forEach((name) => {
    const li = document.createElement("li");
    li.textContent = name;
    docList.appendChild(li);
  });
}

// Load the doc list on page load
loadDocumentList();

// ── Message rendering helpers ──────────────────────────────────────────────────

/**
 * Append a simple user or bot text message.
 * @param {"user"|"bot"} role
 * @param {string} htmlContent — already-escaped HTML string
 */
function appendMessage(role, htmlContent) {
  const div = document.createElement("div");
  div.className = `message ${role === "user" ? "user-message" : "bot-message"}`;
  const bubble = document.createElement("div");
  bubble.className = "message-bubble";
  bubble.innerHTML = `<p>${htmlContent}</p>`;
  div.appendChild(bubble);
  chatWindow.appendChild(div);
  scrollToBottom();
  return div;
}

/**
 * Append a bot message with optional source references.
 * @param {string} text — raw text from the API (may contain newlines)
 * @param {Array<{filename:string, page:string}>} sources
 */
function appendBotMessage(text, sources) {
  const div = document.createElement("div");
  div.className = "message bot-message";
  const bubble = document.createElement("div");
  bubble.className = "message-bubble";

  // Convert newlines to <p> tags for readability
  const paragraphs = text
    .split(/\n+/)
    .filter((p) => p.trim())
    .map((p) => `<p>${escapeHtml(p)}</p>`)
    .join("");
  bubble.innerHTML = paragraphs;

  // Append sources block if present
  if (sources && sources.length > 0) {
    const srcBlock = document.createElement("div");
    srcBlock.className = "sources-block";
    srcBlock.innerHTML =
      "<strong>Sources from uploaded documents:</strong><ul>" +
      sources
        .map(
          (s) =>
            `<li>${escapeHtml(s.filename)} — page ${escapeHtml(s.page)}</li>`
        )
        .join("") +
      "</ul>";
    bubble.appendChild(srcBlock);
  }

  div.appendChild(bubble);
  chatWindow.appendChild(div);
  scrollToBottom();
}

/** Append a red error message bubble. */
function appendError(message) {
  const div = document.createElement("div");
  div.className = "message bot-message error-message";
  const bubble = document.createElement("div");
  bubble.className = "message-bubble";
  bubble.innerHTML = `<p>⚠ ${escapeHtml(message)}</p>`;
  div.appendChild(bubble);
  chatWindow.appendChild(div);
  scrollToBottom();
}

/** Show a "typing…" indicator and return its DOM id for later removal. */
function appendTyping() {
  const id = `typing-${Date.now()}`;
  const div = document.createElement("div");
  div.className = "message bot-message typing-indicator";
  div.id = id;
  const bubble = document.createElement("div");
  bubble.className = "message-bubble";
  bubble.textContent = "Thinking…";
  div.appendChild(bubble);
  chatWindow.appendChild(div);
  scrollToBottom();
  return id;
}

/** Remove the typing indicator by its id. */
function removeTyping(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

// ── Utility helpers ────────────────────────────────────────────────────────────

function scrollToBottom() {
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

/** Briefly shake an input element to signal a validation error. */
function shakeInput(el) {
  el.style.borderColor = "#b91c1c";
  el.focus();
  setTimeout(() => { el.style.borderColor = ""; }, 1200);
}

/** Set the upload status message with an optional CSS class. */
function showUploadStatus(msg, type) {
  uploadStatus.textContent = msg;
  uploadStatus.className = `status-msg ${type}`;
}

/**
 * Escape a string for safe insertion into HTML.
 * Prevents XSS from server-returned content or file names.
 */
function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}
