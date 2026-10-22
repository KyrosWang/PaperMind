from io import BytesIO
from pathlib import Path
from unittest.mock import Mock

from app.api.routes import papers as paper_routes
from app.config import Settings
from app.dependencies import require_api_key
from app.models import Paper
from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session


def make_settings(tmp_path: Path) -> Settings:
    return Settings(
        environment="test",
        database_url="sqlite+pysqlite:///:memory:",
        app_api_key="test-key",
        data_root=tmp_path,
    )


def test_upload_rejects_non_pdf(db: Session, tmp_path: Path) -> None:
    paper = Paper(title="Upload test")
    db.add(paper)
    db.commit()
    file = UploadFile(
        filename="bad.txt",
        file=BytesIO(b"not a pdf"),
        headers={"content-type": "text/plain"},
    )
    try:
        paper_routes.upload_attachment(paper.id, db, make_settings(tmp_path), file)
    except HTTPException as exc:
        assert exc.status_code == 415
    else:
        raise AssertionError("Expected a non-PDF upload to fail")


def test_upload_accepts_pdf_and_enqueues(db: Session, tmp_path: Path, monkeypatch) -> None:
    paper = Paper(title="Upload test")
    db.add(paper)
    db.commit()
    delay = Mock()
    monkeypatch.setattr(paper_routes.process_attachment, "delay", delay)
    file = UploadFile(
        filename="paper.pdf",
        file=BytesIO(b"%PDF-1.4\n%%EOF"),
        headers={"content-type": "application/pdf"},
    )
    attachment = paper_routes.upload_attachment(paper.id, db, make_settings(tmp_path), file)
    assert attachment.processing_status == "pending"
    db.refresh(paper)
    assert paper.active_attachment_id == attachment.id
    delay.assert_called_once()


def test_second_pdf_stays_inactive_unless_replacement_is_explicit(
    db: Session, tmp_path: Path, monkeypatch
) -> None:
    paper = Paper(title="Replacement test")
    db.add(paper)
    db.commit()
    delay = Mock()
    monkeypatch.setattr(paper_routes.process_attachment, "delay", delay)

    first = paper_routes.upload_attachment(
        paper.id,
        db,
        make_settings(tmp_path),
        UploadFile(
            filename="first.pdf",
            file=BytesIO(b"%PDF-1.4\nfirst\n%%EOF"),
            headers={"content-type": "application/pdf"},
        ),
    )
    second = paper_routes.upload_attachment(
        paper.id,
        db,
        make_settings(tmp_path),
        UploadFile(
            filename="second.pdf",
            file=BytesIO(b"%PDF-1.4\nsecond\n%%EOF"),
            headers={"content-type": "application/pdf"},
        ),
    )
    db.refresh(paper)
    assert paper.active_attachment_id == first.id
    assert delay.call_count == 1

    replacement = paper_routes.upload_attachment(
        paper.id,
        db,
        make_settings(tmp_path),
        UploadFile(
            filename="replacement.pdf",
            file=BytesIO(b"%PDF-1.4\nreplacement\n%%EOF"),
            headers={"content-type": "application/pdf"},
        ),
        replace_active=True,
    )
    db.refresh(paper)
    assert paper.active_attachment_id == replacement.id
    assert delay.call_count == 2

    paper_routes.activate_attachment(paper.id, second.id, db)
    db.refresh(paper)
    assert paper.active_attachment_id == second.id
    assert delay.call_count == 3


def test_api_requires_key(tmp_path: Path) -> None:
    try:
        require_api_key(make_settings(tmp_path), "wrong")
    except HTTPException as exc:
        assert exc.status_code == 401
    else:
        raise AssertionError("Expected an invalid API key to fail")
