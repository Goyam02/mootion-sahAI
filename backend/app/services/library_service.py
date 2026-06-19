"""Content Library service — query ready videos across all classrooms."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.models import Chapter, ChapterAsset, ClassRoom
from app.repositories.onboarding_repository import get_teacher_class_membership


# ─────────────────────────────────────────────────────────────────────────────
# Schemas (inline, lightweight)
# ─────────────────────────────────────────────────────────────────────────────

def _asset_to_library_item(asset: ChapterAsset, chapter: Chapter, classroom: ClassRoom) -> dict[str, Any]:
    return {
        "asset_id": str(asset.id),
        "asset_type": asset.asset_type,
        "title": asset.title,
        "description": asset.description,
        "external_url": asset.external_url,
        "generation_status": asset.generation_status,
        "chapter_id": str(chapter.id),
        "chapter_title": chapter.title,
        "class_id": str(classroom.id),
        "class_display_name": classroom.display_name,
        "grade": classroom.grade,
        "subject": classroom.subject,
        "last_generated_at": asset.last_generated_at.isoformat() if asset.last_generated_at else None,
        "created_at": asset.created_at.isoformat(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Queries
# ─────────────────────────────────────────────────────────────────────────────

def list_library_assets(
    db: Session,
    asset_type: str = "concept_video",
    grade: str | None = None,
    subject: str | None = None,
    search: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """
    Return all ready chapter assets of a given type across ALL classrooms.
    Optionally filter by grade, subject, or a text search on title/chapter.
    """
    stmt = (
        select(ChapterAsset, Chapter, ClassRoom)
        .join(Chapter, ChapterAsset.chapter_id == Chapter.id)
        .join(ClassRoom, Chapter.class_id == ClassRoom.id)
        .where(
            ChapterAsset.asset_type == asset_type,
            ChapterAsset.generation_status == "ready",
            ChapterAsset.external_url.isnot(None),
        )
        .order_by(ChapterAsset.last_generated_at.desc().nullslast(), ChapterAsset.created_at.desc())
        .limit(limit)
    )

    rows = db.execute(stmt).all()
    results: list[dict[str, Any]] = []

    for asset, chapter, classroom in rows:
        item = _asset_to_library_item(asset, chapter, classroom)

        # Filter by grade
        if grade:
            import re
            g_digits = re.sub(r"\D", "", str(grade))
            item_digits = re.sub(r"\D", "", str(item["grade"]))
            if g_digits and item_digits and g_digits != item_digits:
                continue

        # Filter by subject (loose match)
        if subject:
            sub_lower = subject.lower().strip()
            item_sub = item["subject"].lower().strip()
            if sub_lower not in item_sub and item_sub not in sub_lower:
                continue

        # Full-text search on title + chapter title
        if search:
            needle = search.lower()
            haystack = f"{item['title']} {item['chapter_title']} {item['subject']}".lower()
            if needle not in haystack:
                continue

        results.append(item)

    return results


# ─────────────────────────────────────────────────────────────────────────────
# Adopt (reuse) an existing library asset into a target chapter asset slot
# ─────────────────────────────────────────────────────────────────────────────

def adopt_library_asset(
    db: Session,
    teacher,
    class_id: str,
    chapter_id: str,
    target_asset_id: str,
    source_asset_id: str,
) -> dict[str, Any]:
    """
    Copy the external_url + metadata from a library (source) asset into
    a target chapter asset slot, marking it ready immediately — no generation cost.
    """
    # Verify teacher has access to the target class
    membership = get_teacher_class_membership(db, str(teacher.id), class_id)
    if not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    # Verify target asset belongs to the right chapter
    target = db.get(ChapterAsset, target_asset_id)
    if not target or str(target.chapter_id) != chapter_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target asset not found")

    # Fetch source asset
    source = db.get(ChapterAsset, source_asset_id)
    if not source or source.generation_status != "ready" or not source.external_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source asset is not ready or has no media URL",
        )

    # Copy fields
    target.external_url = source.external_url
    target.storage_bucket = source.storage_bucket
    target.storage_key = source.storage_key
    target.generation_status = "ready"
    target.last_generated_at = datetime.now(timezone.utc)
    target.payload_json = {
        **(target.payload_json or {}),
        "adopted_from_asset_id": source_asset_id,
        "adopted_from_chapter_id": str(source.chapter_id),
    }

    db.commit()
    db.refresh(target)

    source_chapter = db.get(Chapter, source.chapter_id)
    source_class = db.get(ClassRoom, source_chapter.class_id) if source_chapter else None

    return {
        "asset_id": str(target.id),
        "asset_type": target.asset_type,
        "title": target.title,
        "description": target.description,
        "generation_status": target.generation_status,
        "external_url": target.external_url,
        "payload_json": target.payload_json,
        "adopted_from": {
            "asset_id": source_asset_id,
            "chapter_title": source_chapter.title if source_chapter else None,
            "class_display_name": source_class.display_name if source_class else None,
        },
    }
