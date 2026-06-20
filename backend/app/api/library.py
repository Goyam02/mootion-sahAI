"""Content Library API — browse & adopt existing generated assets."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_teacher
from app.services.library_service import adopt_library_asset, list_library_assets


router = APIRouter(prefix="/teachers/library", tags=["library"])


@router.get("/assets")
def browse_library(
    asset_type: str = Query(default="concept_video"),
    grade: str | None = Query(default=None),
    subject: str | None = Query(default=None),
    search: str | None = Query(default=None),
    topic_title: str | None = Query(default=None),
    limit: int = Query(default=100, le=200),
    user=Depends(require_teacher),
    db: Session = Depends(get_db),
):
    """
    Return all ready assets of a given type across all classrooms.
    Supports optional grade, subject, and free-text search filters.
    """
    return list_library_assets(
        db,
        asset_type=asset_type,
        grade=grade,
        subject=subject,
        search=search,
        topic_title=topic_title,
        limit=limit,
    )


@router.post("/classes/{class_id}/chapters/{chapter_id}/assets/{asset_id}/adopt")
def adopt_asset(
    class_id: str,
    chapter_id: str,
    asset_id: str,
    body: dict,
    user=Depends(require_teacher),
    db: Session = Depends(get_db),
):
    """
    Adopt (reuse) an existing library asset into a target chapter asset slot.
    Body: { "source_asset_id": "<uuid>" }
    No generation cost — copies the URL immediately.
    """
    source_asset_id = body.get("source_asset_id") or body.get("library_asset_id")
    if not source_asset_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="source_asset_id is required")

    return adopt_library_asset(db, user, class_id, chapter_id, asset_id, source_asset_id)
