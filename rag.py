"""
rag.py — Retrieval-Augmented Generation (RAG) engine.

Responsibilities:
  1. Extract text from PDF files (with page numbers).
  2. Split text into overlapping chunks.
  3. Build a TF-IDF index over all chunks.
  4. Retrieve the most relevant chunks for a user question.
  5. Call the OpenAI API with retrieved context to generate an answer.
  6. Return source references (filename + page number).
"""

import os
import re
from typing import List, Tuple, Dict, Any

import pypdf
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import openai
from dotenv import load_dotenv

load_dotenv()

# ── Constants ──────────────────────────────────────────────────────────────────
CHUNK_SIZE = 400          # approximate number of words per chunk
CHUNK_OVERLAP = 80        # words of overlap between consecutive chunks
TOP_K = 5                 # number of chunks to retrieve
MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OFFICIAL_URL = "https://cetcell.mahacet.org/"

SYSTEM_PROMPT = """You are LateralEntryBot, a helpful assistant for students seeking
information about Direct Second Year (DSY / Lateral Entry) Engineering admission
in Maharashtra, India.

Rules you MUST follow:
1. Answer ONLY using the document excerpts provided in the user message.
2. Do NOT invent, guess, or assume any dates, eligibility criteria, cutoffs,
   fees, seat availability, or required documents.
3. If the answer cannot be found in the excerpts, say clearly:
   "I could not find verified information about this in the uploaded documents.
    Please check the official CET Cell website: https://cetcell.mahacet.org/"
4. Always remind students to verify important details against the official
   CET Cell website: https://cetcell.mahacet.org/
5. Be concise, friendly, and easy to understand for undergraduate students.
6. Never claim that an uploaded PDF is an official document — only the CET Cell
   website is the authoritative source.
"""


class RAGEngine:
    """Manages the document index and answers user questions."""

    def __init__(self, upload_folder: str) -> None:
        self.upload_folder = upload_folder
        # Each chunk is stored as a dict with keys: text, filename, page
        self._chunks: List[Dict[str, Any]] = []
        self._vectorizer: TfidfVectorizer | None = None
        self._matrix = None  # sparse TF-IDF matrix

    # ── Indexing ───────────────────────────────────────────────────────────────

    def index_all(self) -> None:
        """Index every PDF found in the upload folder."""
        if not os.path.isdir(self.upload_folder):
            return
        for fname in os.listdir(self.upload_folder):
            if fname.lower().endswith(".pdf"):
                path = os.path.join(self.upload_folder, fname)
                try:
                    self.index_file(path)
                except Exception as exc:  # pylint: disable=broad-except
                    print(f"[RAG] Could not index '{fname}': {exc}")

    def index_file(self, filepath: str) -> int:
        """
        Extract text from a PDF, split into chunks, and rebuild the TF-IDF index.
        Returns the number of chunks created for this file.
        """
        filename = os.path.basename(filepath)
        # Remove any existing chunks for this file (supports re-indexing)
        self._chunks = [c for c in self._chunks if c["filename"] != filename]

        new_chunks = self._extract_chunks(filepath, filename)
        self._chunks.extend(new_chunks)
        self._rebuild_index()
        return len(new_chunks)

    def _extract_chunks(self, filepath: str, filename: str) -> List[Dict[str, Any]]:
        """Read a PDF and return a list of chunk dicts."""
        chunks: List[Dict[str, Any]] = []
        try:
            reader = pypdf.PdfReader(filepath)
        except Exception as exc:
            raise ValueError(f"Cannot read PDF '{filename}': {exc}") from exc

        for page_num, page in enumerate(reader.pages, start=1):
            raw_text = page.extract_text() or ""
            cleaned = self._clean_text(raw_text)
            if not cleaned.strip():
                continue
            words = cleaned.split()
            start = 0
            while start < len(words):
                chunk_words = words[start: start + CHUNK_SIZE]
                chunk_text = " ".join(chunk_words)
                chunks.append({
                    "text": chunk_text,
                    "filename": filename,
                    "page": page_num,
                })
                start += CHUNK_SIZE - CHUNK_OVERLAP
        return chunks

    @staticmethod
    def _clean_text(text: str) -> str:
        """Normalise whitespace in extracted PDF text."""
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _rebuild_index(self) -> None:
        """Rebuild the TF-IDF matrix from all current chunks."""
        if not self._chunks:
            self._vectorizer = None
            self._matrix = None
            return
        texts = [c["text"] for c in self._chunks]
        self._vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            max_features=20000,
        )
        self._matrix = self._vectorizer.fit_transform(texts)

    # ── Retrieval ──────────────────────────────────────────────────────────────

    def retrieve(self, question: str, top_k: int = TOP_K) -> List[Dict[str, Any]]:
        """
        Return up to top_k chunks most relevant to *question*.
        Returns an empty list if no documents have been indexed.
        """
        if self._vectorizer is None or self._matrix is None:
            return []

        query_vec = self._vectorizer.transform([question])
        scores = cosine_similarity(query_vec, self._matrix).flatten()
        # Pick indices with highest scores (descending)
        top_indices = np.argsort(scores)[::-1][:top_k]
        results = []
        for idx in top_indices:
            if scores[idx] > 0:  # ignore zero-score chunks
                results.append(self._chunks[idx])
        return results

    # ── Answer generation ──────────────────────────────────────────────────────

    def answer(self, question: str) -> Tuple[str, List[Dict[str, str]]]:
        """
        Generate an answer for *question* using retrieved context.

        Returns:
            answer  — the AI-generated response string
            sources — list of {"filename": ..., "page": ...} dicts
        """
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise ValueError(
                "The OPENAI_API_KEY environment variable is not set. "
                "Please add it to your .env file and restart the server."
            )

        retrieved = self.retrieve(question)

        if retrieved:
            context_parts = []
            for i, chunk in enumerate(retrieved, start=1):
                context_parts.append(
                    f"[Excerpt {i} — {chunk['filename']}, page {chunk['page']}]\n"
                    f"{chunk['text']}"
                )
            context_block = "\n\n".join(context_parts)
            user_message = (
                f"Use ONLY the following excerpts from uploaded admission documents "
                f"to answer the question. If the excerpts do not contain the answer, "
                f"say so and refer the student to {OFFICIAL_URL}.\n\n"
                f"--- DOCUMENT EXCERPTS ---\n{context_block}\n"
                f"--- END OF EXCERPTS ---\n\n"
                f"Question: {question}"
            )
        else:
            user_message = (
                f"No admission documents have been uploaded yet.\n\n"
                f"Question: {question}"
            )

        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.2,
            max_tokens=800,
        )

        answer_text = response.choices[0].message.content.strip()

        # Build unique source list preserving order
        sources: List[Dict[str, str]] = []
        seen = set()
        for chunk in retrieved:
            key = (chunk["filename"], chunk["page"])
            if key not in seen:
                seen.add(key)
                sources.append({"filename": chunk["filename"], "page": str(chunk["page"])})

        return answer_text, sources

    # ── Utilities ──────────────────────────────────────────────────────────────

    def list_documents(self) -> List[str]:
        """Return a sorted list of unique filenames in the index."""
        return sorted({c["filename"] for c in self._chunks})
