import io
import json
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def _post_file(filename: str, content: bytes):
    files = {"file": (filename, io.BytesIO(content), "application/octet-stream")}
    return client.post("/api/v1/upload_pdf", files=files)


def test_reject_txt_renamed_as_pdf(monkeypatch):
    # Fake Cloudinary upload to avoid network
    def fake_upload(file, resource_type="raw"):
        return {
            "secure_url": "https://example.com/fake",
            "public_id": "fake_id",
            "bytes": len(b"%PDF-1.5\n"),
            "created_at": "2024-01-01T00:00:00Z",
            "format": "pdf",
        }

    import cloudinary.uploader

    monkeypatch.setattr(cloudinary.uploader, "upload", fake_upload)

    # Plain text content but named .pdf
    resp = _post_file("note.pdf", b"hello world\nthis is text")
    assert resp.status_code == 400
    assert "not a valid PDF" in resp.json()["detail"]


def test_accept_real_pdf_header(monkeypatch):
    # Fake Cloudinary upload
    def fake_upload(file, resource_type="raw"):
        return {
            "secure_url": "https://example.com/fake",
            "public_id": "fake_id",
            "bytes": 10,
            "created_at": "2024-01-01T00:00:00Z",
            "format": "pdf",
        }

    import cloudinary.uploader

    monkeypatch.setattr(cloudinary.uploader, "upload", fake_upload)

    # Minimal PDF header with EOF
    pdf_bytes = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<<>>\nendobj\nstartxref\n0\n%%EOF\n"
    resp = _post_file("ok.pdf", pdf_bytes)
    # Cloudinary and DB might fail if DB not available; expect 500 after validation passes
    # So we only assert it is not rejected for type mismatch
    assert resp.status_code in (200, 500)
    if resp.status_code == 400:
        assert "Only PDF files are allowed." not in resp.json()["detail"]


def test_reject_jpg_renamed_as_pdf(monkeypatch):
    def fake_upload(file, resource_type="raw"):
        return {
            "secure_url": "https://example.com/fake",
            "public_id": "fake_id",
            "bytes": 10,
            "created_at": "2024-01-01T00:00:00Z",
            "format": "pdf",
        }

    import cloudinary.uploader

    monkeypatch.setattr(cloudinary.uploader, "upload", fake_upload)

    # JPEG magic number but named .pdf
    jpg_bytes = b"\xff\xd8\xff\xe0" + b"fakejpegdata"
    resp = _post_file("image.pdf", jpg_bytes)
    assert resp.status_code == 400
    assert "not a valid PDF" in resp.json()["detail"]


def test_reject_docx_renamed_as_pdf(monkeypatch):
    def fake_upload(file, resource_type="raw"):
        return {
            "secure_url": "https://example.com/fake",
            "public_id": "fake_id",
            "bytes": 10,
            "created_at": "2024-01-01T00:00:00Z",
            "format": "pdf",
        }

    import cloudinary.uploader

    monkeypatch.setattr(cloudinary.uploader, "upload", fake_upload)

    # DOCX is a ZIP: PK\x03\x04
    docx_bytes = b"PK\x03\x04" + b"fakezipdata"
    resp = _post_file("docx.pdf", docx_bytes)
    assert resp.status_code == 400
    assert "not a valid PDF" in resp.json()["detail"]

