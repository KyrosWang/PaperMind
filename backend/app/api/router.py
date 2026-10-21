from fastapi import APIRouter

from app.api.routes import chat, papers, zotero

api_router = APIRouter()
api_router.include_router(papers.router, prefix="/papers", tags=["papers"])
api_router.include_router(chat.router, prefix="/papers", tags=["chat"])
api_router.include_router(zotero.router, prefix="/zotero", tags=["zotero"])
