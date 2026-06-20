"""Content Library service — query ready videos across all classrooms."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.models import Chapter, ChapterAsset, ClassRoom
from app.repositories.onboarding_repository import get_teacher_class_membership

from app.services.media_service import resolve_asset_media_url


# ─────────────────────────────────────────────────────────────────────────────
# Schemas (inline, lightweight)
# ─────────────────────────────────────────────────────────────────────────────

def _asset_to_library_item(asset: ChapterAsset, chapter: Chapter, classroom: ClassRoom) -> dict[str, Any]:
    return {
        "asset_id": str(asset.id),
        "asset_type": asset.asset_type,
        "title": asset.title,
        "description": asset.description,
        "external_url": resolve_asset_media_url(asset),
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
    topic_title: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """
    Return all ready chapter and topic assets of a given type across ALL classrooms.
    Optionally filter by grade, subject, topic_title, or a text search.
    """
    # 1. Query ready ChapterAsset
    stmt_chapter = (
        select(ChapterAsset, Chapter, ClassRoom)
        .join(Chapter, ChapterAsset.chapter_id == Chapter.id)
        .join(ClassRoom, Chapter.class_id == ClassRoom.id)
        .where(
            ChapterAsset.asset_type == asset_type,
            ChapterAsset.generation_status == "ready",
            ChapterAsset.external_url.isnot(None),
        )
    )
    rows_chapter = db.execute(stmt_chapter).all()

    # 2. Query ready ChapterTopicAsset
    from app.core.models import ChapterTopicAsset, ChapterTopic
    stmt_topic = (
        select(ChapterTopicAsset, ChapterTopic, Chapter, ClassRoom)
        .join(ChapterTopic, ChapterTopicAsset.topic_id == ChapterTopic.id)
        .join(Chapter, ChapterTopic.chapter_id == Chapter.id)
        .join(ClassRoom, Chapter.class_id == ClassRoom.id)
        .where(
            ChapterTopicAsset.asset_type == asset_type,
            ChapterTopicAsset.generation_status == "ready",
            ChapterTopicAsset.external_url.isnot(None),
        )
    )
    rows_topic = db.execute(stmt_topic).all()

    items: list[dict[str, Any]] = []

    for asset, chapter, classroom in rows_chapter:
        if asset.payload_json and "adopted_from_asset_id" in asset.payload_json:
            continue
        item = _asset_to_library_item(asset, chapter, classroom)
        item["topic_title"] = chapter.title
        items.append(item)

    for asset, topic, chapter, classroom in rows_topic:
        if asset.payload_json and "adopted_from_asset_id" in asset.payload_json:
            continue
        item = _asset_to_library_item(asset, chapter, classroom)
        item["topic_title"] = topic.title
        items.append(item)

    # Filtering helper
    def normalize_title(t: str | None) -> str:
        if not t:
            return ""
        import re
        return re.sub(r'[\s\-_]+', ' ', t.lower().strip())

    filtered_results: list[dict[str, Any]] = []
    
    for item in items:
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

        # Filter by topic_title (scoped topic filtering)
        if topic_title:
            t1 = normalize_title(item["topic_title"])
            t2 = normalize_title(topic_title)
            if t1 != t2 and t1 not in t2 and t2 not in t1:
                continue

        # Full-text search on title + chapter title + topic title
        if search:
            needle = search.lower()
            haystack = f"{item['title']} {item['chapter_title']} {item['topic_title']} {item['subject']}".lower()
            if needle not in haystack:
                continue

        filtered_results.append(item)

    # Sort results by last_generated_at/created_at descending
    def sort_key(x):
        gen = x.get("last_generated_at")
        cr = x.get("created_at")
        return (gen or "", cr or "")

    filtered_results.sort(key=sort_key, reverse=True)
    return filtered_results[:limit]


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
    a target asset slot (ChapterAsset or ChapterTopicAsset), marking it ready immediately — no generation cost.
    """
    if target_asset_id == source_asset_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot adopt an asset into itself",
        )

    # Verify teacher has access to the target class
    membership = get_teacher_class_membership(db, str(teacher.id), class_id)
    if not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    from app.core.models import ChapterTopicAsset, ChapterTopic

    # 1. Fetch target asset (could be ChapterAsset or ChapterTopicAsset)
    target = db.get(ChapterAsset, target_asset_id)
    target_chapter_id = None
    if target:
        target_chapter_id = target.chapter_id
    else:
        target = db.get(ChapterTopicAsset, target_asset_id)
        if target:
            # Topic asset: get parent topic to find chapter_id
            topic = db.get(ChapterTopic, target.topic_id)
            if topic:
                target_chapter_id = topic.chapter_id

    if not target or str(target_chapter_id) != chapter_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target asset not found")

    # 2. Fetch source asset (could be ChapterAsset or ChapterTopicAsset)
    source = db.get(ChapterAsset, source_asset_id)
    source_chapter_id = None
    if source:
        source_chapter_id = source.chapter_id
    else:
        source = db.get(ChapterTopicAsset, source_asset_id)
        if source:
            topic = db.get(ChapterTopic, source.topic_id)
            if topic:
                source_chapter_id = topic.chapter_id

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
        "placeholder": False,
        "generated": True,
        "adopted_from_asset_id": source_asset_id,
        "adopted_from_chapter_id": str(source_chapter_id) if source_chapter_id else None,
    }

    db.commit()
    db.refresh(target)

    source_chapter = db.get(Chapter, source_chapter_id) if source_chapter_id else None
    source_class = db.get(ClassRoom, source_chapter.class_id) if source_chapter else None

    asset_data = {
        "asset_id": str(target.id),
        "asset_type": target.asset_type,
        "provider": target.provider,
        "integration_target": target.integration_target,
        "title": target.title,
        "description": target.description,
        "generation_status": target.generation_status,
        "external_url": resolve_asset_media_url(target),
        "payload_json": target.payload_json,
    }

    res = {
        **asset_data,
        "adopted_from": {
            "asset_id": source_asset_id,
            "chapter_title": source_chapter.title if source_chapter else None,
            "class_display_name": source_class.display_name if source_class else None,
        },
        "asset": asset_data,
    }
    return res
