import uuid

import structlog
from celery import Celery
from sqlalchemy import delete

from app.config import get_settings
from app.database import SessionLocal
from app.models import Attachment, DocumentChunk, DocumentSection, ProcessingStatus
from app.services.chunking import Paragraph, chunk_paragraphs
from app.services.grobid import GrobidClient, parse_tei
from app.services.providers import get_embedding_provider
from app.services.storage import LocalFilesystemStorage

settings = get_settings()
logger = structlog.get_logger(__name__)
celery_app = Celery("papermind", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(task_track_started=True, task_time_limit=900, worker_prefetch_multiplier=1)


@celery_app.task(
    name="papermind.process_attachment",
    autoretry_for=(ConnectionError,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def process_attachment(attachment_id: str) -> None:
    db = SessionLocal()
    attachment_uuid = uuid.UUID(attachment_id)
    try:
        attachment = db.get(Attachment, attachment_uuid)
        if attachment is None:
            logger.error("attachment_not_found", attachment_id=attachment_id)
            return
        attachment.processing_status = ProcessingStatus.parsing
        attachment.processing_error = None
        db.commit()

        storage = LocalFilesystemStorage(settings.data_root)
        pdf_path = storage.absolute_path(attachment.storage_path)
        tei = GrobidClient(settings.grobid_url, settings.grobid_timeout_seconds).process(pdf_path)
        tei_path = f"papers/{attachment.paper_id}/parsed-{attachment.id}.tei.xml"
        if storage.exists(tei_path):
            storage.delete_file(tei_path)
        from io import BytesIO

        storage.save_file(tei_path, BytesIO(tei))
        parsed_sections = parse_tei(tei)

        db.execute(delete(DocumentChunk).where(DocumentChunk.paper_id == attachment.paper_id))
        db.execute(delete(DocumentSection).where(DocumentSection.paper_id == attachment.paper_id))
        db.flush()
        chunk_index = 0
        chunks: list[DocumentChunk] = []
        for order, parsed in enumerate(parsed_sections):
            pages = [page for _, page in parsed.paragraphs if page is not None]
            section = DocumentSection(
                paper_id=attachment.paper_id,
                heading=parsed.heading,
                section_type=parsed.section_type,
                section_order=order,
                page_start=min(pages) if pages else None,
                page_end=max(pages) if pages else None,
            )
            db.add(section)
            db.flush()
            paragraphs = [Paragraph(text, page, page) for text, page in parsed.paragraphs]
            for part in chunk_paragraphs(
                paragraphs, settings.chunk_target_tokens, settings.chunk_overlap_tokens
            ):
                chunk = DocumentChunk(
                    paper_id=attachment.paper_id,
                    section_id=section.id,
                    text=part.text,
                    chunk_index=chunk_index,
                    page_start=part.page_start,
                    page_end=part.page_end,
                    token_count=part.token_count,
                )
                chunks.append(chunk)
                db.add(chunk)
                chunk_index += 1
        attachment.processing_status = ProcessingStatus.embedding
        db.commit()

        provider = get_embedding_provider(settings)
        for start in range(0, len(chunks), 64):
            batch = chunks[start : start + 64]
            vectors = provider.embed([chunk.text for chunk in batch])
            for chunk, vector in zip(batch, vectors, strict=True):
                chunk.embedding = vector
            db.commit()

        attachment.processing_status = ProcessingStatus.ready
        db.commit()
        logger.info(
            "attachment_processing_complete",
            attachment_id=attachment_id,
            chunks=len(chunks),
        )
    except Exception as exc:
        db.rollback()
        attachment = db.get(Attachment, attachment_uuid)
        if attachment:
            attachment.processing_status = ProcessingStatus.failed
            attachment.processing_error = str(exc)[:2000]
            db.commit()
        logger.exception("attachment_processing_failed", attachment_id=attachment_id)
        raise
    finally:
        db.close()
