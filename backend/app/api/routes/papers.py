import hashlib
import tempfile
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.config import Settings, get_settings
from app.database import get_db
from app.models import Attachment, Author, Collection, Paper, ProcessingStatus, Tag
from app.schemas import AttachmentRead, FacetRead, LibraryFacets, PaperDetail, PaperRead
from app.services.storage import LocalFilesystemStorage
from app.worker import process_attachment

router = APIRouter()


def _paper_query():
    return select(Paper).options(
        selectinload(Paper.authors),
        selectinload(Paper.attachments),
        selectinload(Paper.sections),
    )


@router.get("", response_model=list[PaperRead])
def list_papers(
    db: Annotated[Session, Depends(get_db)],
    q: str | None = None,
    collection: uuid.UUID | None = None,
    tag: uuid.UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[Paper]:
    statement = _paper_query().where(Paper.zotero_deleted_at.is_(None))
    if q:
        pattern = f"%{q}%"
        statement = statement.outerjoin(Paper.authors).where(
            or_(
                Paper.title.ilike(pattern),
                Paper.abstract.ilike(pattern),
                Paper.doi.ilike(pattern),
                Paper.journal.ilike(pattern),
                Author.normalized_name.ilike(pattern),
            )
        )
    if collection:
        statement = statement.join(Paper.collections).where(Collection.id == collection)
    if tag:
        statement = statement.join(Paper.tags).where(Tag.id == tag)
    return list(db.scalars(statement.distinct().offset(offset).limit(limit)).all())


@router.get("/facets", response_model=LibraryFacets)
def library_facets(db: Annotated[Session, Depends(get_db)]) -> LibraryFacets:
    collections = db.scalars(select(Collection).order_by(Collection.name)).all()
    tags = db.scalars(select(Tag).order_by(Tag.name)).all()
    return LibraryFacets(
        collections=[FacetRead.model_validate(item) for item in collections],
        tags=[FacetRead.model_validate(item) for item in tags],
    )


@router.get("/{paper_id}", response_model=PaperDetail)
def get_paper(paper_id: uuid.UUID, db: Annotated[Session, Depends(get_db)]) -> Paper:
    paper = db.scalar(_paper_query().where(Paper.id == paper_id))
    if paper is None:
        raise HTTPException(status_code=404, detail="Paper not found")
    return paper


@router.post(
    "/{paper_id}/attachments", response_model=AttachmentRead, status_code=status.HTTP_201_CREATED
)
def upload_attachment(
    paper_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    file: Annotated[UploadFile, File()],
) -> Attachment:
    if db.get(Paper, paper_id) is None:
        raise HTTPException(status_code=404, detail="Paper not found")
    if file.content_type not in {"application/pdf", "application/octet-stream"}:
        raise HTTPException(status_code=415, detail="Only PDF uploads are accepted")

    size = 0
    checksum = hashlib.sha256()
    with tempfile.SpooledTemporaryFile(max_size=8 * 1024 * 1024) as temporary:
        while content := file.file.read(1024 * 1024):
            size += len(content)
            if size > settings.max_upload_bytes:
                raise HTTPException(status_code=413, detail="PDF exceeds configured size limit")
            checksum.update(content)
            temporary.write(content)
        if size < 5:
            raise HTTPException(status_code=422, detail="PDF is empty or malformed")
        temporary.seek(0)
        if temporary.read(5) != b"%PDF-":
            raise HTTPException(status_code=422, detail="File does not have a valid PDF signature")
        digest = checksum.hexdigest()
        duplicate = db.scalar(
            select(Attachment).where(Attachment.paper_id == paper_id, Attachment.checksum == digest)
        )
        if duplicate:
            raise HTTPException(status_code=409, detail="This PDF is already attached")

        attachment_id = uuid.uuid4()
        relative_path = f"papers/{paper_id}/{attachment_id}/original.pdf"
        temporary.seek(0)
        storage = LocalFilesystemStorage(settings.data_root)
        storage.save_file(relative_path, temporary)

    attachment = Attachment(
        id=attachment_id,
        paper_id=paper_id,
        filename="original.pdf",
        original_filename=file.filename or "upload.pdf",
        storage_path=relative_path,
        mime_type="application/pdf",
        checksum=digest,
        file_size=size,
        processing_status=ProcessingStatus.pending,
    )
    db.add(attachment)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        storage.delete_file(relative_path)
        raise HTTPException(status_code=409, detail="This PDF is already attached") from exc
    db.refresh(attachment)
    process_attachment.delay(str(attachment.id))
    return attachment


@router.get("/{paper_id}/attachments/{attachment_id}/file")
def download_attachment(
    paper_id: uuid.UUID,
    attachment_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> FileResponse:
    attachment = db.scalar(
        select(Attachment).where(Attachment.id == attachment_id, Attachment.paper_id == paper_id)
    )
    if attachment is None:
        raise HTTPException(status_code=404, detail="PDF not found")
    path = LocalFilesystemStorage(settings.data_root).absolute_path(attachment.storage_path)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="PDF file is missing from storage")
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=attachment.original_filename,
        content_disposition_type="inline",
    )
