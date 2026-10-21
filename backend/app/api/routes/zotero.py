from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import get_db
from app.schemas import SyncResult
from app.services.zotero import ZoteroError, sync_zotero

router = APIRouter()


@router.post("/sync", response_model=SyncResult)
def synchronize(
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> SyncResult:
    try:
        return sync_zotero(db, settings)
    except ZoteroError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
