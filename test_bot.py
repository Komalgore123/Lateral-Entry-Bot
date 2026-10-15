"""
test_bot.py — Basic automated tests for LateralEntryBot.

Run with:
    python test_bot.py

Tests cover:
  1. Empty question validation (Flask route)
  2. No documents — retrieval returns empty list
  3. PDF upload and indexing (creates a minimal in-memory PDF)
  4. TF-IDF retrieval returns relevant chunks
  5. Source references are returned correctly
  6. Missing API key returns a clear error
"""

import io
import os
import sys
import json
import tempfile
import unittest

# ── Make sure we can import from the project root ─────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))


class TestRAGEngine(unittest.TestCase):
    """Tests for rag.py — no server needed."""

    def setUp(self):
        """Create a temporary folder and a RAGEngine instance."""
        from rag import RAGEngine
        self.tmpdir = tempfile.mkdtemp()
        self.engine = RAGEngine(upload_folder=self.tmpdir)

    # ── Test 2: No documents ───────────────────────────────────────────────────
    def test_retrieve_no_documents(self):
        """Retrieve should return an empty list when no PDFs are indexed."""
        results = self.engine.retrieve("What are the eligibility criteria?")
        self.assertEqual(results, [], "Expected empty list when no documents are indexed.")
        print("  [PASS] test_retrieve_no_documents")

    # ── Test 3: PDF upload & indexing ──────────────────────────────────────────
    def test_index_pdf(self):
        """Upload a minimal PDF and verify chunks are created."""
        pdf_path = self._create_sample_pdf("sample.pdf", "Lateral entry eligibility requires a diploma.")
        chunk_count = self.engine.index_file(pdf_path)
        self.assertGreater(chunk_count, 0, "Expected at least one chunk after indexing a PDF.")
        self.assertIn("sample.pdf", self.engine.list_documents())
        print(f"  [PASS] test_index_pdf — {chunk_count} chunk(s) created")

    # ── Test 4: Relevant retrieval ─────────────────────────────────────────────
    def test_retrieve_relevant_chunk(self):
        """After indexing, retrieve should return the relevant chunk."""
        pdf_path = self._create_sample_pdf(
            "eligibility.pdf",
            "Students who have completed a three-year diploma in engineering are eligible "
            "for lateral entry admission to second year of BE/BTech programs in Maharashtra."
        )
        self.engine.index_file(pdf_path)
        results = self.engine.retrieve("What is the eligibility for lateral entry?")
        self.assertGreater(len(results), 0, "Expected at least one result for a relevant query.")
        # Verify the source filename is tracked
        self.assertEqual(results[0]["filename"], "eligibility.pdf")
        print(f"  [PASS] test_retrieve_relevant_chunk — top result from '{results[0]['filename']}' page {results[0]['page']}")

    # ── Test 5: Source references ──────────────────────────────────────────────
    def test_source_references_structure(self):
        """Source references must have 'filename' and 'page' keys."""
        pdf_path = self._create_sample_pdf(
            "docs_required.pdf",
            "Required documents: diploma marksheet, leaving certificate, birth certificate."
        )
        self.engine.index_file(pdf_path)
        results = self.engine.retrieve("What documents are required?")
        self.assertGreater(len(results), 0, "Expected results for document query.")
        for chunk in results:
            self.assertIn("filename", chunk, "Chunk missing 'filename' key.")
            self.assertIn("page", chunk, "Chunk missing 'page' key.")
            self.assertIn("text", chunk, "Chunk missing 'text' key.")
        print(f"  [PASS] test_source_references_structure — {len(results)} source(s) verified")

    # ── Test 6: Missing API key ────────────────────────────────────────────────
    def test_missing_api_key_raises_value_error(self):
        """answer() must raise ValueError when OPENAI_API_KEY is not set."""
        original = os.environ.pop("OPENAI_API_KEY", None)
        try:
            with self.assertRaises(ValueError) as ctx:
                self.engine.answer("What are the fees?")
            self.assertIn("OPENAI_API_KEY", str(ctx.exception))
            print("  [PASS] test_missing_api_key_raises_value_error")
        finally:
            if original:
                os.environ["OPENAI_API_KEY"] = original

    # ── Helper ─────────────────────────────────────────────────────────────────
    def _create_sample_pdf(self, filename: str, text: str) -> str:
        """Create a minimal real PDF file with the given text and return its path."""
        try:
            import pypdf
            from pypdf import PdfWriter
            writer = PdfWriter()
            page = writer.add_blank_page(width=612, height=792)
            # pypdf doesn't easily write text; use reportlab if available, else fpdf2
            raise ImportError("Force fallback to fpdf2")
        except Exception:
            pass

        # Try fpdf2 first (lighter dependency)
        try:
            from fpdf import FPDF
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Helvetica", size=12)
            pdf.multi_cell(0, 10, text)
            path = os.path.join(self.tmpdir, filename)
            pdf.output(path)
            return path
        except ImportError:
            pass

        # Fallback: write a raw minimal PDF manually
        path = os.path.join(self.tmpdir, filename)
        self._write_minimal_pdf(path, text)
        return path

    @staticmethod
    def _write_minimal_pdf(path: str, text: str) -> None:
        """
        Write a syntactically valid minimal PDF with one page of text.
        Uses correct byte-offset xref table so pypdf reads it cleanly.
        Works without any third-party library beyond pypdf itself.
        """
        safe_text = text.encode("ascii", errors="replace").decode("ascii")
        escaped = (
            safe_text
            .replace("\\", "\\\\")
            .replace("(", "\\(")
            .replace(")", "\\)")
        )
        # Keep each line ≤ 80 chars for readability in the stream
        words = escaped.split()
        lines, current = [], []
        for word in words:
            current.append(word)
            if len(" ".join(current)) > 70:
                lines.append(" ".join(current))
                current = []
        if current:
            lines.append(" ".join(current))

        stream_parts = []
        y = 740
        for line in lines:
            stream_parts.append(f"BT /F1 11 Tf 50 {y} Td ({line}) Tj ET")
            y -= 16
        stream_body = "\n".join(stream_parts) + "\n"
        stream_bytes = stream_body.encode("latin-1")
        stream_len = len(stream_bytes)

        # Build objects as byte strings so we can compute exact offsets
        obj1 = b"1 0 obj\n<</Type /Catalog /Pages 2 0 R>>\nendobj\n"
        obj2 = b"2 0 obj\n<</Type /Pages /Kids [3 0 R] /Count 1>>\nendobj\n"
        obj3 = (
            b"3 0 obj\n"
            b"<</Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]\n"
            b"  /Contents 4 0 R /Resources <</Font <</F1 5 0 R>>>>>>\n"
            b">>\nendobj\n"
        )
        obj4_header = f"4 0 obj\n<</Length {stream_len}>>\nstream\n".encode("latin-1")
        obj4_footer = b"\nendstream\nendobj\n"
        obj5 = (
            b"5 0 obj\n"
            b"<</Type /Font /Subtype /Type1 /BaseFont /Helvetica>>\n"
            b"endobj\n"
        )

        header = b"%PDF-1.4\n"
        offsets = []
        body = header
        offsets.append(len(body)); body += obj1
        offsets.append(len(body)); body += obj2
        offsets.append(len(body)); body += obj3
        offsets.append(len(body)); body += obj4_header + stream_bytes + obj4_footer
        offsets.append(len(body)); body += obj5

        xref_offset = len(body)
        xref = b"xref\n0 6\n0000000000 65535 f \n"
        for off in offsets:
            xref += f"{off:010d} 00000 n \n".encode("latin-1")
        trailer = (
            f"trailer\n<</Size 6 /Root 1 0 R>>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("latin-1")

        with open(path, "wb") as f:
            f.write(body + xref + trailer)


class TestFlaskApp(unittest.TestCase):
    """Tests for app.py routes — uses Flask test client."""

    def setUp(self):
        """Create a Flask test client with a temporary upload folder."""
        import tempfile
        self.tmpdir = tempfile.mkdtemp()
        # Patch the upload folder before importing app
        os.environ.setdefault("OPENAI_API_KEY", "test-key-placeholder")
        import app as flask_app
        flask_app.app.config["UPLOAD_FOLDER"] = self.tmpdir
        flask_app.app.config["TESTING"] = True
        flask_app.rag_engine.upload_folder = self.tmpdir
        self.client = flask_app.app.test_client()

    # ── Test 1: Empty question ─────────────────────────────────────────────────
    def test_empty_question_returns_400(self):
        """POST /api/chat with empty question must return 400."""
        resp = self.client.post(
            "/api/chat",
            json={"question": ""},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertIn("error", data)
        print("  [PASS] test_empty_question_returns_400 —", data["error"])

    def test_whitespace_only_question_returns_400(self):
        """POST /api/chat with whitespace-only question must return 400."""
        resp = self.client.post(
            "/api/chat",
            json={"question": "   "},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        print("  [PASS] test_whitespace_only_question_returns_400")

    def test_missing_json_body_returns_400(self):
        """POST /api/chat with no body must return 400."""
        resp = self.client.post("/api/chat", data="", content_type="application/json")
        self.assertEqual(resp.status_code, 400)
        print("  [PASS] test_missing_json_body_returns_400")

    # ── Upload validation tests ────────────────────────────────────────────────
    def test_upload_no_file_returns_400(self):
        """POST /api/upload with no file must return 400."""
        resp = self.client.post("/api/upload")
        self.assertEqual(resp.status_code, 400)
        print("  [PASS] test_upload_no_file_returns_400")

    def test_upload_wrong_extension_returns_400(self):
        """POST /api/upload with a non-PDF file must return 400."""
        data = {"file": (io.BytesIO(b"hello"), "test.txt")}
        resp = self.client.post("/api/upload", data=data, content_type="multipart/form-data")
        self.assertEqual(resp.status_code, 400)
        body = resp.get_json()
        self.assertIn("PDF", body["error"])
        print("  [PASS] test_upload_wrong_extension_returns_400")

    # ── Index document list ────────────────────────────────────────────────────
    def test_documents_endpoint_returns_list(self):
        """GET /api/documents must return a JSON object with a 'documents' key."""
        resp = self.client.get("/api/documents")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("documents", data)
        self.assertIsInstance(data["documents"], list)
        print("  [PASS] test_documents_endpoint_returns_list")

    # ── Index page ─────────────────────────────────────────────────────────────
    def test_index_page_loads(self):
        """GET / must return HTTP 200 and contain 'LateralEntryBot'."""
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"LateralEntryBot", resp.data)
        print("  [PASS] test_index_page_loads")


# ── Runner ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  LateralEntryBot — Test Suite")
    print("=" * 60 + "\n")
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    # RAG engine tests
    suite.addTests(loader.loadTestsFromTestCase(TestRAGEngine))
    # Flask app tests
    suite.addTests(loader.loadTestsFromTestCase(TestFlaskApp))

    runner = unittest.TextTestRunner(verbosity=0)
    result = runner.run(suite)

    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print(f"  All {result.testsRun} tests PASSED.")
    else:
        print(f"  {len(result.failures)} failure(s), {len(result.errors)} error(s) out of {result.testsRun} tests.")
    print("=" * 60 + "\n")
    sys.exit(0 if result.wasSuccessful() else 1)
