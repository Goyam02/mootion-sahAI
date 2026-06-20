from __future__ import annotations

from app.core.config import settings
from app.core.deps import get_current_user
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.models import Chapter, ChapterAsset, ChapterTopicAsset
from app.repositories.onboarding_repository import get_student_class_membership, get_teacher_class_membership
from app.services.media_service import get_signed_media_url
from app.schemas.media import SignedMediaUrlResponse


router = APIRouter(prefix="/media", tags=["media"])


def _assert_user_can_access_asset(db: Session, user, asset) -> None:
    chapter_id = getattr(asset, "chapter_id", None)
    if chapter_id is None and hasattr(asset, "topic_id"):
        from app.core.models import ChapterTopic
        topic = db.get(ChapterTopic, asset.topic_id)
        if topic:
            chapter_id = topic.chapter_id

    chapter = db.get(Chapter, chapter_id) if chapter_id else None
    if not chapter:
        raise HTTPException(status_code=404, detail="Media asset not found")

    if user.role == "teacher":
        membership = get_teacher_class_membership(db, str(user.id), str(chapter.class_id))
    else:
        membership = get_student_class_membership(db, str(user.id), str(chapter.class_id))

    if not membership:
        raise HTTPException(status_code=403, detail="Forbidden")


@router.get("/assets/{asset_id}")
def asset_media(asset_id: str, db: Session = Depends(get_db)):
    asset = db.get(ChapterAsset, asset_id)
    if not asset:
        asset = db.get(ChapterTopicAsset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Media asset not found")

    if asset.storage_bucket and asset.storage_key:
        return RedirectResponse(get_signed_media_url(asset.storage_bucket, asset.storage_key), status_code=302)

    if asset.external_url:
        return RedirectResponse(asset.external_url, status_code=302)

    raise HTTPException(status_code=404, detail="Media asset not available")


@router.get("/assets/{asset_id}/signed-url", response_model=SignedMediaUrlResponse)
def asset_signed_url(asset_id: str, user=Depends(get_current_user), db: Session = Depends(get_db)):
    asset = db.get(ChapterAsset, asset_id)
    if not asset:
        asset = db.get(ChapterTopicAsset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Media asset not found")

    if not asset.storage_bucket or not asset.storage_key:
        raise HTTPException(status_code=404, detail="Signed media URL not available")

    _assert_user_can_access_asset(db, user, asset)

    return SignedMediaUrlResponse(
        asset_id=str(asset.id),
        signed_url=get_signed_media_url(asset.storage_bucket, asset.storage_key),
        expires_in_minutes=settings.object_storage_signed_url_expiry_minutes,
    )
