import re
from datetime import UTC, datetime
from typing import Any

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import Author, Collection, Paper, Tag, ZoteroSyncState
from app.schemas import SyncResult

logger = structlog.get_logger(__name__)


class ZoteroError(RuntimeError):
    pass


def normalize_author(first_name: str | None, last_name: str | None) -> str:
    return " ".join(filter(None, [first_name, last_name])).casefold().strip()


def _date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _year(value: str | None) -> int | None:
    match = re.search(r"(?:18|19|20|21)\d{2}", value or "")
    return int(match.group()) if match else None


def _identifier(extra: str | None, name: str) -> str | None:
    match = re.search(rf"(?im)^\s*{re.escape(name)}\s*:\s*(.+?)\s*$", extra or "")
    return match.group(1).strip() if match else None


def map_item_fields(payload: dict[str, Any]) -> dict[str, Any]:
    """Map a Zotero item without treating locally processed data as authoritative metadata."""
    data = payload.get("data", payload)
    return {
        "zotero_item_key": data.get("key") or payload.get("key"),
        "zotero_version": data.get("version") or payload.get("version"),
        "title": data.get("title") or "Untitled",
        "abstract": data.get("abstractNote") or None,
        "doi": data.get("DOI") or None,
        "pmid": _identifier(data.get("extra"), "PMID"),
        "arxiv_id": _identifier(data.get("extra"), "arXiv"),
        "journal": data.get("publicationTitle") or data.get("proceedingsTitle") or None,
        "publication_year": _year(data.get("date")),
        "url": data.get("url") or None,
        "date_added": _date(data.get("dateAdded")),
        "date_modified": _date(data.get("dateModified")),
    }


class ZoteroClient:
    api_root = "https://api.zotero.org"

    def __init__(self, api_key: str, library_type: str, library_id: str) -> None:
        self.library_type = f"{library_type}s"
        self.library_id = library_id
        self.client = httpx.Client(
            base_url=self.api_root,
            headers={"Zotero-API-Key": api_key, "Zotero-API-Version": "3"},
            timeout=30,
        )

    @property
    def base_path(self) -> str:
        return f"/{self.library_type}/{self.library_id}"

    def _pages(self, endpoint: str, since: int) -> tuple[list[dict[str, Any]], int]:
        start = 0
        records: list[dict[str, Any]] = []
        version = since
        while True:
            try:
                response = self.client.get(
                    f"{self.base_path}/{endpoint}",
                    params={"since": since, "start": start, "limit": 100, "format": "json"},
                )
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code in {401, 403}:
                    raise ZoteroError("Zotero rejected the API credentials") from exc
                raise ZoteroError(f"Zotero API returned {exc.response.status_code}") from exc
            except httpx.HTTPError as exc:
                raise ZoteroError(f"Zotero is unavailable: {exc}") from exc
            batch = response.json()
            if not isinstance(batch, list):
                raise ZoteroError("Unexpected Zotero response")
            records.extend(batch)
            version = max(version, int(response.headers.get("Last-Modified-Version", version)))
            if len(batch) < 100:
                break
            start += len(batch)
        return records, version

    def changed_items(self, since: int) -> tuple[list[dict[str, Any]], int]:
        return self._pages("items/top", since)

    def changed_collections(self, since: int) -> tuple[list[dict[str, Any]], int]:
        return self._pages("collections", since)

    def deleted(self, since: int) -> tuple[dict[str, list[str]], int]:
        try:
            response = self.client.get(f"{self.base_path}/deleted", params={"since": since})
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ZoteroError(f"Unable to read Zotero deletions: {exc}") from exc
        version = int(response.headers.get("Last-Modified-Version", since))
        return response.json(), version


def _get_or_create_author(db: Session, creator: dict[str, Any]) -> Author:
    first = creator.get("firstName") or None
    last = creator.get("lastName") or creator.get("name") or None
    normalized = normalize_author(first, last) or "unknown"
    author = db.scalar(select(Author).where(Author.normalized_name == normalized))
    if author is None:
        author = Author(first_name=first, last_name=last, normalized_name=normalized)
        db.add(author)
    return author


def sync_zotero(db: Session, settings: Settings) -> SyncResult:
    if not settings.zotero_api_key or not settings.zotero_user_id:
        raise ZoteroError("ZOTERO_API_KEY and ZOTERO_USER_ID must be configured")
    state = db.get(ZoteroSyncState, (settings.zotero_library_type, settings.zotero_user_id))
    if state is None:
        state = ZoteroSyncState(
            library_type=settings.zotero_library_type,
            library_id=settings.zotero_user_id,
            library_version=0,
        )
        db.add(state)
        db.flush()
    previous = state.library_version
    client = ZoteroClient(
        settings.zotero_api_key, settings.zotero_library_type, settings.zotero_user_id
    )
    collections, collection_version = client.changed_collections(previous)
    collection_map: dict[str, Collection] = {
        item.zotero_collection_key: item for item in db.scalars(select(Collection)).all()
    }
    for payload in collections:
        data = payload.get("data", payload)
        key = data["key"]
        collection = collection_map.get(key)
        if collection is None:
            collection = Collection(zotero_collection_key=key, name=data.get("name", "Untitled"))
            db.add(collection)
            collection_map[key] = collection
        collection.name = data.get("name", collection.name)
    db.flush()
    for payload in collections:
        data = payload.get("data", payload)
        parent_key = data.get("parentCollection")
        collection_map[data["key"]].parent = collection_map.get(parent_key)

    items, item_version = client.changed_items(previous)
    papers_upserted = 0
    for payload in items:
        data = payload.get("data", payload)
        if data.get("itemType") in {"attachment", "note", "annotation"}:
            continue
        fields = map_item_fields(payload)
        key = fields["zotero_item_key"]
        paper = db.scalar(select(Paper).where(Paper.zotero_item_key == key))
        if paper is None:
            paper = Paper(**fields)
            db.add(paper)
        else:
            for name, value in fields.items():
                setattr(paper, name, value)
        paper.zotero_deleted_at = None
        paper.authors = [
            _get_or_create_author(db, creator)
            for creator in data.get("creators", [])
            if creator.get("creatorType") == "author"
        ]
        paper.collections = [
            collection_map[key] for key in data.get("collections", []) if key in collection_map
        ]
        tags: list[Tag] = []
        for item in data.get("tags", []):
            name = item.get("tag", "").strip()
            if not name:
                continue
            tag = db.scalar(select(Tag).where(Tag.name == name))
            if tag is None:
                tag = Tag(name=name)
                db.add(tag)
            tags.append(tag)
        paper.tags = tags
        papers_upserted += 1

    deleted, deleted_version = client.deleted(previous)
    now = datetime.now(UTC)
    for key in deleted.get("items", []):
        paper = db.scalar(select(Paper).where(Paper.zotero_item_key == key))
        if paper:
            paper.zotero_deleted_at = now
    for key in deleted.get("collections", []):
        collection = collection_map.get(key)
        if collection:
            for possible_child in collection_map.values():
                if possible_child.parent_collection_id == collection.id:
                    possible_child.parent = None
            db.delete(collection)

    state.library_version = max(collection_version, item_version, deleted_version)
    state.synced_at = now
    db.commit()
    logger.info(
        "zotero_sync_complete",
        previous_version=previous,
        library_version=state.library_version,
        papers=papers_upserted,
    )
    return SyncResult(
        previous_version=previous,
        library_version=state.library_version,
        papers_upserted=papers_upserted,
        collections_upserted=len(collections),
        deleted_items=len(deleted.get("items", [])),
    )
