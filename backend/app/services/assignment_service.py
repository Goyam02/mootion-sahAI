from __future__ import annotations

from datetime import datetime, timezone

import httpx
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.models import Assignment, AssignmentRecipient, Chapter, ChapterAsset, ChapterAssetGenerationJob, User
from app.repositories.assignment_repository import (
    create_assignment,
    create_assignment_recipient,
    create_generation_job,
    get_assignment,
    get_assignment_jobs,
    get_assignment_recipient,
    list_assignments_for_class,
    list_assignments_for_student,
)
from app.repositories.chapter_repository import (
    get_assets_for_chapter,
    get_chapter,
    get_topics_for_chapter,
    get_assets_for_topic,
)
from app.repositories.onboarding_repository import get_student_class_membership, get_student_ids_for_class, get_teacher_class_membership
from app.schemas.assignment import (
    AssignmentCreateRequest,
    AssignmentJobResponse,
    AssignmentListItem,
    AssignmentRecipientResponse,
    AssignmentResponse,
    StudentAssignmentListItem,
    StudentAssignmentResponse,
)
from app.services.media_queue import enqueue_media_generation_job
from app.services.media_service import store_generated_manim_video
from app.services.model_finder import find_model, query_llm
import json


class GenerationParsingError(Exception):
    """Raised when LLM output fails to parse after all retry attempts."""
    def __init__(self, message: str, raw_text: str = ""):
        self.raw_text = raw_text
        super().__init__(message)


GENERATIONABLE_PROVIDERS = {"manim", "model_finder", "quiz_generator", "simulation", "mootion_ai"}
ALLOWED_ASSIGNMENT_TYPES = {
    "video",
    "simulation",
    "model",
    "quiz",
    "explain_ai",
    "predict_ai",
    "spot_it",
    "connect_it",
    "EXPLAIN_IT",
    "PREDICT_IT",
    "SPOT_IT",
    "INTERACTIVE_QUIZ",
    "explain_it",
    "predict_it",
    "interactive_quiz",
}
ASSIGNMENT_TYPE_TO_ASSET_TYPE = {
    "video": "concept_video",
    "simulation": "simulation",
    "model": "three_d_model",
    "quiz": "quiz",
    "explain_ai": "explain_it",
    "predict_ai": "predict_it",
    "spot_it": "spot_it",
    "connect_it": "connect_it",
    "EXPLAIN_IT": "explain_it",
    "PREDICT_IT": "predict_it",
    "SPOT_IT": "spot_it",
    "INTERACTIVE_QUIZ": "interactive_quiz",
    "explain_it": "explain_it",
    "predict_it": "predict_it",
    "interactive_quiz": "interactive_quiz",
}

INTERACTIVE_ASSIGNMENT_TYPES = {
    "explain_ai", "predict_ai", "spot_it", "connect_it", "interactive_quiz",
    "EXPLAIN_IT", "PREDICT_IT", "SPOT_IT", "INTERACTIVE_QUIZ",
    "explain_it", "predict_it",
}


def _ensure_teacher_has_access(db: Session, user: User, class_id: str) -> None:
    membership = get_teacher_class_membership(db, str(user.id), class_id)
    if not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


def _chapter_asset_to_job_response(job: ChapterAssetGenerationJob) -> AssignmentJobResponse:
    return AssignmentJobResponse(
        job_id=str(job.id),
        asset_id=str(job.chapter_asset_id),
        asset_type=job.asset_type,
        provider=job.provider,
        integration_target=job.integration_target,
        status=job.status,
        result_json=job.result_json,
        error_message=job.error_message,
    )


def _assignment_to_response(db: Session, assignment: Assignment) -> AssignmentResponse:
    recipients = [
        AssignmentRecipientResponse(student_id=str(recipient.student_id))
        for recipient in db.query(AssignmentRecipient).filter(AssignmentRecipient.assignment_id == assignment.id).all()
    ]
    jobs = [_chapter_asset_to_job_response(job) for job in get_assignment_jobs(db, str(assignment.id))]
    return AssignmentResponse(
        assignment_id=str(assignment.id),
        class_id=str(assignment.class_id),
        chapter_id=str(assignment.chapter_id),
        assignment_type=assignment.assignment_type,
        title=assignment.title,
        instructions=assignment.instructions,
        content_json=assignment.content_json,
        status=assignment.status,
        recipients=recipients,
        jobs=jobs,
    )


def _create_generation_jobs(db: Session, assignment: Assignment, chapter: Chapter) -> int:
    created = 0

    if assignment.assignment_type in INTERACTIVE_ASSIGNMENT_TYPES:
        return created

    expected_asset_type = ASSIGNMENT_TYPE_TO_ASSET_TYPE.get(assignment.assignment_type)

    # Collect all assets (chapter + topics) and check which are ready
    chapter_assets = get_assets_for_chapter(db, str(chapter.id))
    topics = get_topics_for_chapter(db, str(chapter.id))
    ready_by_type: dict[str, any] = {}   # asset_type -> one ready asset (chapter or topic)

    # Check chapter assets
    for asset in chapter_assets:
        if asset.generation_status == "ready":
            if expected_asset_type and asset.asset_type == expected_asset_type:
                ready_by_type[asset.asset_type] = asset
            elif expected_asset_type in ("interactive_quiz", "quiz") and asset.asset_type in ("interactive_quiz", "quiz"):
                ready_by_type[asset.asset_type] = asset

    # Check topic assets
    for topic in topics:
        topic_assets = get_assets_for_topic(db, str(topic.id))
        for asset in topic_assets:
            if asset.generation_status == "ready":
                if expected_asset_type and asset.asset_type == expected_asset_type:
                    if asset.asset_type not in ready_by_type:
                        ready_by_type[asset.asset_type] = asset
                elif expected_asset_type in ("interactive_quiz", "quiz") and asset.asset_type in ("interactive_quiz", "quiz"):
                    if asset.asset_type not in ready_by_type:
                        ready_by_type[asset.asset_type] = asset

    # Now iterate over chapter assets and create jobs only if no ready asset exists for that type
    for asset in chapter_assets:
        match = False
        if expected_asset_type:
            if asset.asset_type == expected_asset_type:
                match = True
            elif expected_asset_type in ("interactive_quiz", "quiz") and asset.asset_type in ("interactive_quiz", "quiz"):
                match = True
        else:
            match = True

        if not match:
            continue
        if asset.provider not in GENERATIONABLE_PROVIDERS:
            continue
        # If there is already a ready asset of this type (from chapter or topic), skip job creation
        if ready_by_type.get(asset.asset_type):
            continue
        if asset.generation_status in ("ready", "queued", "processing"):
            continue

        existing_job = (
            db.query(ChapterAssetGenerationJob)
            .filter(
                ChapterAssetGenerationJob.assignment_id == assignment.id,
                ChapterAssetGenerationJob.chapter_asset_id == asset.id,
            )
            .one_or_none()
        )
        if existing_job:
            continue

        payload_json = {
            "assignment_id": str(assignment.id),
            "class_id": str(assignment.class_id),
            "chapter_id": str(chapter.id),
            "assignment_type": assignment.assignment_type,
            "chapter_title": chapter.title,
            "assignment_title": assignment.title,
            "instructions": assignment.instructions,
            "asset_type": asset.asset_type,
            "provider": asset.provider,
            "integration_target": asset.integration_target,
            "payload_json": asset.payload_json,
        }

        generation_job = create_generation_job(
            db,
            ChapterAssetGenerationJob(
                assignment_id=assignment.id,
                chapter_asset_id=asset.id,
                asset_type=asset.asset_type,
                provider=asset.provider,
                integration_target=asset.integration_target,
                status="queued",
                payload_json=payload_json,
            ),
        )
        asset.generation_status = "queued"
        try:
            enqueue_media_generation_job(str(generation_job.id))
        except Exception:
            # The DB row is the source of truth; the queue can be rebuilt on startup.
            pass
        created += 1

    db.commit()
    return created


def _is_content_placeholder(content_json: dict) -> bool:
    """Return True if content_json is still a placeholder (no actual media URL)."""
    if not content_json:
        return True
    # If any of these keys exist with a non-null value, it's not a placeholder.
    if content_json.get("external_url") or content_json.get("embedUrl") or content_json.get("quiz"):
        return False
    # Also check if the placeholder flag is explicitly set
    if content_json.get("placeholder") is True:
        return True
    # Fallback: if there's no media, treat as placeholder.
    return True


def _build_content_json_from_chapter(db: Session, chapter_id: str, assignment_type: str) -> dict | None:
    """Builds content_json from the newest ready asset (chapter or topic) of the matching type.
    Returns None if no ready asset is found.
    """
    expected_asset_type = ASSIGNMENT_TYPE_TO_ASSET_TYPE.get(assignment_type)
    chapter_assets = get_assets_for_chapter(db, chapter_id)
    topics = get_topics_for_chapter(db, chapter_id)

    # Collect all ready assets of the matching type
    ready_assets = []
    for asset in chapter_assets:
        if asset.generation_status != "ready":
            continue
        if expected_asset_type and asset.asset_type == expected_asset_type:
            ready_assets.append(asset)
        elif expected_asset_type in ("interactive_quiz", "quiz") and asset.asset_type in ("interactive_quiz", "quiz"):
            ready_assets.append(asset)

    for topic in topics:
        for asset in get_assets_for_topic(db, str(topic.id)):
            if asset.generation_status != "ready":
                continue
            if expected_asset_type and asset.asset_type == expected_asset_type:
                ready_assets.append(asset)
            elif expected_asset_type in ("interactive_quiz", "quiz") and asset.asset_type in ("interactive_quiz", "quiz"):
                ready_assets.append(asset)

    if not ready_assets:
        return None

    # Sort by last_generated_at descending (newest first). If None, use created_at.
    ready_assets.sort(
        key=lambda a: (a.last_generated_at or a.created_at),
        reverse=True
    )
    asset = ready_assets[0]

    content_json = {
        "assignment_type": assignment_type,
        "activity": assignment_type,
        "chapter_id": str(chapter_id),
    }
    if asset.asset_type in ("quiz", "interactive_quiz"):
        content_json["quiz"] = (asset.payload_json or {}).get("quiz")
    elif asset.asset_type == "three_d_model":
        content_json["embedUrl"] = asset.external_url
    elif asset.asset_type in ("concept_video", "simulation"):
        content_json["external_url"] = asset.external_url
    else:
        payload = asset.payload_json or {}
        for key in ("system_prompt", "initial_question", "student_persona", "scenario"):
            if key in payload:
                content_json[key] = payload[key]
    return content_json


def _refresh_assignment_status(db: Session, assignment_id: str) -> None:
    jobs = get_assignment_jobs(db, assignment_id)
    assignment = get_assignment(db, assignment_id)
    if not assignment:
        return

    # If there are no jobs, assignment status is ready (if content is ready, or can be built)
    if not jobs:
        # If content is still placeholder, try to build from ready assets.
        if _is_content_placeholder(assignment.content_json):
            new_content = _build_content_json_from_chapter(db, str(assignment.chapter_id), assignment.assignment_type)
            if new_content:
                assignment.content_json = new_content
                assignment.status = "ready"
            else:
                # No ready asset found – keep queued
                assignment.status = "queued"
        else:
            # Already has content, keep ready
            assignment.status = "ready"
        db.commit()
        return

    statuses = {job.status for job in jobs}

    if statuses <= {"ready"}:
        # All jobs are ready – update content if still placeholder
        if _is_content_placeholder(assignment.content_json):
            new_content = _build_content_json_from_chapter(db, str(assignment.chapter_id), assignment.assignment_type)
            if new_content:
                assignment.content_json = new_content
        assignment.status = "ready"
    elif "failed" in statuses:
        assignment.status = "failed"
    elif "processing" in statuses:
        assignment.status = "processing"
    else:
        assignment.status = "queued"
    db.commit()


def create_teacher_assignment(
    db: Session,
    user: User,
    class_id: str,
    request: AssignmentCreateRequest,
) -> AssignmentResponse:
    _ensure_teacher_has_access(db, user, class_id)

    if request.assignment_type not in ALLOWED_ASSIGNMENT_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid assignment type")

    chapter = get_chapter(db, request.chapter_id)
    if not chapter or str(chapter.class_id) != class_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chapter not found")

    recipient_ids = get_student_ids_for_class(db, class_id)

    content_json = {
        "placeholder": True,
        "assignment_type": request.assignment_type,
        "activity": request.assignment_type,
        "chapter_id": str(chapter.id),
        "chapter_title": chapter.title,
    }

    assignment = create_assignment(
        db,
        Assignment(
            class_id=chapter.class_id,
            chapter_id=chapter.id,
            created_by_teacher_id=user.id,
            assignment_type=request.assignment_type,
            title=request.title,
            instructions=request.instructions,
            content_json=content_json,
            status="queued",
        ),
    )

    for student_id in recipient_ids:
        if not get_assignment_recipient(db, str(assignment.id), student_id):
            create_assignment_recipient(
                db,
                AssignmentRecipient(
                    assignment_id=assignment.id,
                    student_id=student_id,
                ),
            )

    _create_generation_jobs(db, assignment, chapter)
    # Refresh status will set content if jobs are skipped (fast path)
    _refresh_assignment_status(db, str(assignment.id))
    db.refresh(assignment)
    return _assignment_to_response(db, assignment)


def list_teacher_assignments(db: Session, user: User, class_id: str) -> list[AssignmentListItem]:
    from sqlalchemy import func
    _ensure_teacher_has_access(db, user, class_id)
    assignments = list_assignments_for_class(db, class_id)
    if not assignments:
        return []

    assignment_ids = [assignment.id for assignment in assignments]

    # Batch retrieve job and recipient counts using group_by
    job_counts = dict(
        db.query(ChapterAssetGenerationJob.assignment_id, func.count(ChapterAssetGenerationJob.id))
        .filter(ChapterAssetGenerationJob.assignment_id.in_(assignment_ids))
        .group_by(ChapterAssetGenerationJob.assignment_id)
        .all()
    )

    recipient_counts = dict(
        db.query(AssignmentRecipient.assignment_id, func.count(AssignmentRecipient.id))
        .filter(AssignmentRecipient.assignment_id.in_(assignment_ids))
        .group_by(AssignmentRecipient.assignment_id)
        .all()
    )

    response: list[AssignmentListItem] = []
    for assignment in assignments:
        response.append(
            AssignmentListItem(
                assignment_id=str(assignment.id),
                class_id=str(assignment.class_id),
                chapter_id=str(assignment.chapter_id),
                assignment_type=assignment.assignment_type,
                title=assignment.title,
                status=assignment.status,
                recipient_count=recipient_counts.get(assignment.id, 0),
                job_count=job_counts.get(assignment.id, 0),
            )
        )
    return response


def get_teacher_assignment(db: Session, user: User, class_id: str, assignment_id: str) -> AssignmentResponse:
    _ensure_teacher_has_access(db, user, class_id)
    assignment = get_assignment(db, assignment_id)
    if not assignment or str(assignment.class_id) != class_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    return _assignment_to_response(db, assignment)


def _student_assignment_to_response(db: Session, assignment: Assignment) -> StudentAssignmentResponse:
    jobs = [_chapter_asset_to_job_response(job) for job in get_assignment_jobs(db, str(assignment.id))]
    return StudentAssignmentResponse(
        assignment_id=str(assignment.id),
        class_id=str(assignment.class_id),
        chapter_id=str(assignment.chapter_id),
        assignment_type=assignment.assignment_type,
        title=assignment.title,
        instructions=assignment.instructions,
        content_json=assignment.content_json,
        status=assignment.status,
        jobs=jobs,
    )


def list_student_assignments(db: Session, user: User, class_id: str) -> list[StudentAssignmentListItem]:
    from sqlalchemy import func
    membership = get_student_class_membership(db, str(user.id), class_id)
    if not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    # Direct DB filtering by class_id
    assignments = db.query(Assignment).filter(Assignment.class_id == class_id).order_by(Assignment.created_at.desc()).all()
    if not assignments:
        return []

    assignment_ids = [assignment.id for assignment in assignments]

    # Batch retrieve job counts
    job_counts = dict(
        db.query(ChapterAssetGenerationJob.assignment_id, func.count(ChapterAssetGenerationJob.id))
        .filter(ChapterAssetGenerationJob.assignment_id.in_(assignment_ids))
        .group_by(ChapterAssetGenerationJob.assignment_id)
        .all()
    )

    return [
        StudentAssignmentListItem(
            assignment_id=str(assignment.id),
            class_id=str(assignment.class_id),
            chapter_id=str(assignment.chapter_id),
            assignment_type=assignment.assignment_type,
            title=assignment.title,
            status=assignment.status,
            job_count=job_counts.get(assignment.id, 0),
        )
        for assignment in assignments
    ]


def get_student_assignment(db: Session, user: User, class_id: str, assignment_id: str) -> StudentAssignmentResponse:
    membership = get_student_class_membership(db, str(user.id), class_id)
    if not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    assignment = get_assignment(db, assignment_id)
    if not assignment or str(assignment.class_id) != class_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")

    return _student_assignment_to_response(db, assignment)


def _get_rag_context_for_asset(asset, query: str) -> str:
    grade = None
    subject = None
    
    from app.core.database import SessionLocal
    from app.core.models import Chapter, ClassRoom
    from app.services.rag_service import retrieve_context
    
    local_db = SessionLocal()
    try:
        chapter_id = getattr(asset, "chapter_id", None)
        if chapter_id is None and hasattr(asset, "topic_id"):
            from app.core.models import ChapterTopic
            topic = local_db.get(ChapterTopic, asset.topic_id)
            if topic:
                chapter_id = topic.chapter_id

        if chapter_id:
            chapter = local_db.get(Chapter, chapter_id)
            if chapter:
                classroom = local_db.get(ClassRoom, chapter.class_id)
                if classroom:
                    grade = classroom.grade
                    subject = classroom.subject
    except Exception as e:
        print(f"[media-worker] Failed to resolve classroom context for RAG: {e}", flush=True)
    finally:
        local_db.close()
        
    return retrieve_context(query, grade, subject)


def _run_manim_generation(asset, payload_json: dict) -> dict[str, object]:
    topic = payload_json.get("chapter_title") or payload_json.get("generation_prompt") or asset.title
    notes = str(payload_json.get("teacher_notes") or payload_json.get("instructions") or "").strip()
    prompt = topic if not notes else f"{topic}. Teacher notes: {notes}"
    
    rag_context = _get_rag_context_for_asset(asset, prompt)
    
    print(f"[media-worker] Sending render request to Manim Service URL: {settings.manim_service_url} for prompt: '{prompt}'", flush=True)
    response = httpx.post(
        settings.manim_service_url,
        params={
            "topic": prompt,
            "level": "school",
            "persona": "teacher",
            "face_enabled": False,
            "rag_context": rag_context,
            "language": payload_json.get("language") or "english",
        },
        timeout=300.0,
    )
    response.raise_for_status()
    result = response.json()
    print(f"[media-worker] Manim render call complete. Response payload: {result}", flush=True)
    return result


def _run_model_finder_generation(asset: ChapterAsset, payload_json: dict) -> dict[str, object]:
    query = payload_json.get("chapter_title") or payload_json.get("generation_prompt") or asset.title
    return find_model(str(query))


def _apply_generation_result(db: Session, job: ChapterAssetGenerationJob, result: dict[str, object], status: str) -> None:
    asset = db.get(ChapterAsset, job.chapter_asset_id)
    if not asset:
        raise RuntimeError("Chapter asset not found")

    job.result_json = result
    job.status = status
    job.finished_at = datetime.now(timezone.utc)

    if status == "ready":
        asset.generation_status = "ready"
        asset.last_generated_at = datetime.now(timezone.utc)
        asset.payload_json = {**asset.payload_json, "placeholder": False, "generated": True, "result": result}

        if job.provider == "manim":
            video_id = str(result.get("video_id") or "").strip()
            if not video_id:
                raise RuntimeError("Manim generation did not return a video_id")
            storage_result = store_generated_manim_video(asset, str(job.id), video_id)
            job.result_json = {**result, **storage_result}
            asset.payload_json = {**asset.payload_json, "storage": storage_result}
        elif job.provider == "model_finder":
            asset.external_url = str(result.get("embedUrl") or result.get("viewerUrl") or "") or None
        elif job.provider == "quiz_generator":
            asset.payload_json = {**asset.payload_json, "quiz": result.get("questions", [])}
        elif job.provider == "simulation":
            simulation_id = str(result.get("simulation_id") or "").strip()
            asset.external_url = (
                f"{settings.backend_public_url.rstrip('/')}/simulations/{simulation_id}/html"
                if simulation_id
                else None
            )
        elif job.provider == "mootion_ai":
            if asset.asset_type in ("interactive_quiz", "quiz"):
                asset.payload_json = {**asset.payload_json, "quiz": result.get("quiz") or result.get("questions", [])}
            else:
                asset.payload_json = {
                    **asset.payload_json,
                    "system_prompt": result.get("system_prompt"),
                    "initial_question": result.get("initial_question"),
                    "student_persona": result.get("student_persona"),
                    "scenario": result.get("scenario"),
                }
    else:
        asset.generation_status = "failed"
        asset.payload_json = {**asset.payload_json, "generated": False, "result": result}

    db.commit()
    print("[media-worker] Asset update committed to DB", flush=True)


def _run_quiz_generation(asset: ChapterAsset, payload_json: dict) -> dict[str, object]:
    topic = payload_json.get("chapter_title") or asset.title
    rag_context = _get_rag_context_for_asset(asset, topic)
    def _generate():
        prompt = f"""
        You are a science teacher. Generate a quiz containing exactly 3 multiple-choice questions for school students on the topic: "{topic}".
        For each question, provide 4 options and specify the index of the correct option (0-based).
        Return ONLY a valid JSON array of objects with the following keys:
        - "question" (string)
        - "options" (array of 4 strings)
        - "correctAnswer" (integer, 0 to 3)

        Do not include markdown tags like ```json or any other text. Output exactly the raw JSON array.
        """
        if rag_context:
            prompt = f"{prompt}\n\nUse the following verified NCERT/curriculum reference context to base the quiz questions on:\n{rag_context}"
        res = query_llm(prompt)
        text = res.get("response", "").strip()
        data = _extract_json_helper(text)
        if isinstance(data, list):
            return {"questions": data}
        if isinstance(data, dict) and "questions" in data:
            return {"questions": data["questions"]}
        raise GenerationParsingError("LLM response did not contain expected quiz format", raw_text=text)
    try:
        return _generation_retry(_generate)
    except GenerationParsingError as e:
        return {"error": f"Quiz generation failed after retries: {str(e)}", "parse_error": True}


def _run_simulation_generation(asset: ChapterAsset, payload_json: dict) -> dict[str, object]:
    from app.simulation_engine.pipeline import SimulationPipeline

    topic = payload_json.get("generation_prompt") or payload_json.get("instructions") or payload_json.get("chapter_title") or asset.title
    instructions = payload_json.get("instructions") or ""
    prompt = f"Teach me {topic}. {instructions}".strip()

    rag_context = _get_rag_context_for_asset(asset, topic)
    if rag_context:
        prompt = f"{prompt}\n\nUse the following verified NCERT/curriculum reference context to structure the simulation components, parameters, and pedagogical feedback:\n{rag_context}"

    pipeline = SimulationPipeline()
    result = pipeline.run(prompt)

    return {
        "simulation_id": result.simulation_id,
        "html": result.html,
        "phase": result.phase.value,
        "quality_score": result.quality_score,
        "error": result.error,
    }


def _extract_json_helper(text: str) -> any:
    cleaned = text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()
    try:
        return json.loads(cleaned)
    except Exception:
        pass
    import re
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass
    match_arr = re.search(r"\[.*\]", cleaned, re.DOTALL)
    if match_arr:
        try:
            return json.loads(match_arr.group(0))
        except Exception:
            pass
    raise GenerationParsingError("Failed to extract valid JSON from LLM response", raw_text=text)


def _generation_retry(callback, max_retries: int = 3) -> dict[str, object]:
    last_exception = None
    for attempt in range(max_retries):
        try:
            return callback()
        except GenerationParsingError as e:
            last_exception = e
            print(f"[generation-retry] Attempt {attempt + 1}/{max_retries} failed: {e}", flush=True)
        except Exception as e:
            last_exception = e
            print(f"[generation-retry] Attempt {attempt + 1}/{max_retries} failed with unexpected error: {e}", flush=True)
    raise GenerationParsingError(
        f"Generation failed after {max_retries} retries: {str(last_exception)}",
        raw_text=getattr(last_exception, 'raw_text', '')
    )


def _run_explain_it_generation(asset: ChapterAsset, payload_json: dict) -> dict[str, object]:
    topic = payload_json.get("chapter_title") or asset.title
    def _generate():
        prompt = f"""
        You are an AI study partner assistant. Generate a prompt context for the activity "Explain It" (where the student explains a science topic to a 10-year-old child).
        Topic: "{topic}"

        Generate a JSON object with:
        1. "system_prompt": Detailed instruction for the AI. It must guide the AI to act as Mootion, a curious 10-year-old student who asks naive but smart questions to check user's understanding of "{topic}".
        2. "initial_question": The first question the child asks to start the session.
        3. "student_persona": A brief description of the student's profile.

        Output format must be a raw JSON object with these three keys.
        Do not include markdown code block tags like ```json.
        """
        res = query_llm(prompt)
        text = res.get("response", "").strip()
        data = _extract_json_helper(text)
        if not isinstance(data, dict):
            raise GenerationParsingError("LLM response was not a valid JSON object", raw_text=text)
        return data
    try:
        return _generation_retry(_generate)
    except GenerationParsingError as e:
        return {"error": f"Explain It generation failed after retries: {str(e)}", "parse_error": True}


def _run_predict_it_generation(asset: ChapterAsset, payload_json: dict) -> dict[str, object]:
    topic = payload_json.get("chapter_title") or asset.title
    def _generate():
        prompt = f"""
        You are an AI study partner assistant. Generate a prompt context for the activity "Predict It" (where the student predicts the outcome of an experiment).
        Topic: "{topic}"

        Generate a JSON object with:
        1. "system_prompt": Detailed instruction for the AI to act as Mootion, a curious 10-year-old student doing a prediction game about "{topic}".
        2. "scenario": A scientific experiment or prediction scenario related to "{topic}".
        3. "initial_question": The first question the child asks to get the student's prediction.
        4. "student_persona": A brief description of the student's profile.

        Output format must be a raw JSON object with these four keys.
        Do not include markdown code block tags like ```json.
        """
        res = query_llm(prompt)
        text = res.get("response", "").strip()
        data = _extract_json_helper(text)
        if not isinstance(data, dict):
            raise GenerationParsingError("LLM response was not a valid JSON object", raw_text=text)
        return data
    try:
        return _generation_retry(_generate)
    except GenerationParsingError as e:
        return {"error": f"Predict It generation failed after retries: {str(e)}", "parse_error": True}


def _run_spot_it_generation(asset: ChapterAsset, payload_json: dict) -> dict[str, object]:
    topic = payload_json.get("chapter_title") or asset.title
    def _generate():
        prompt = f"""
        You are an AI study partner assistant. Generate a prompt context for the activity "Spot It" (where the student spots a real-world concept or riddle).
        Topic: "{topic}"

        Generate a JSON object with:
        1. "system_prompt": Detailed instruction for the AI to act as Mootion, a curious 10-year-old student discussing a real-world puzzle or connection of "{topic}".
        2. "scenario": A real-world scenario or riddle related to "{topic}".
        3. "initial_question": The first question the child asks to start the discussion.
        4. "student_persona": A brief description of the student's profile.

        Output format must be a raw JSON object with these four keys.
        Do not include markdown code block tags like ```json.
        """
        res = query_llm(prompt)
        text = res.get("response", "").strip()
        data = _extract_json_helper(text)
        if not isinstance(data, dict):
            raise GenerationParsingError("LLM response was not a valid JSON object", raw_text=text)
        return data
    try:
        return _generation_retry(_generate)
    except GenerationParsingError as e:
        return {"error": f"Spot It generation failed after retries: {str(e)}", "parse_error": True}


def _run_interactive_quiz_generation(asset: ChapterAsset, payload_json: dict) -> dict[str, object]:
    topic = payload_json.get("chapter_title") or asset.title
    def _generate():
        prompt = f"""
        You are a science teacher. Generate an interactive quiz containing exactly 3 multiple-choice questions for school students on the topic: "{topic}".
        For each question, provide 4 options and specify the index of the correct option (0-based).
        Return ONLY a valid JSON array of objects (or object containing the questions array) with the following keys:
        - "question" (string)
        - "options" (array of 4 strings)
        - "correctAnswer" (integer, 0 to 3)

        Do not include markdown tags like ```json or any other text. Output exactly the raw JSON.
        """
        res = query_llm(prompt)
        text = res.get("response", "").strip()
        data = _extract_json_helper(text)
        if isinstance(data, list):
            return {"questions": data}
        if isinstance(data, dict) and "questions" in data:
            return {"questions": data["questions"]}
        raise GenerationParsingError("LLM response did not contain expected quiz format", raw_text=text)
    try:
        return _generation_retry(_generate)
    except GenerationParsingError as e:
        return {"error": f"Interactive Quiz generation failed after retries: {str(e)}", "parse_error": True}


def _run_mootion_ai_generation(asset: ChapterAsset, payload_json: dict) -> dict[str, object]:
    asset_type = asset.asset_type
    if asset_type == "explain_it":
        return _run_explain_it_generation(asset, payload_json)
    elif asset_type == "predict_it":
        return _run_predict_it_generation(asset, payload_json)
    elif asset_type == "spot_it":
        return _run_spot_it_generation(asset, payload_json)
    elif asset_type in ("interactive_quiz", "quiz"):
        return _run_interactive_quiz_generation(asset, payload_json)
    else:
        return {"error": f"Unsupported asset type for mootion_ai: {asset_type}"}


def process_generation_job(db: Session, job: ChapterAssetGenerationJob) -> None:
    asset = db.get(ChapterAsset, job.chapter_asset_id)
    if not asset:
        job.status = "failed"
        job.error_message = "Chapter asset not found"
        job.finished_at = datetime.now(timezone.utc)
        db.commit()
        return

    job.status = "processing"
    job.started_at = datetime.now(timezone.utc)
    job.attempt_count += 1
    db.commit()

    try:
        if job.provider == "manim":
            result = _run_manim_generation(asset, job.payload_json)
        elif job.provider == "model_finder":
            result = _run_model_finder_generation(asset, job.payload_json)
        elif job.provider == "quiz_generator":
            result = _run_quiz_generation(asset, job.payload_json)
        elif job.provider == "simulation":
            result = _run_simulation_generation(asset, job.payload_json)
        elif job.provider == "mootion_ai":
            result = _run_mootion_ai_generation(asset, job.payload_json)
        else:
            raise RuntimeError(f"Unsupported provider: {job.provider}")

        if result.get("parse_error"):
            job.error_message = str(result.get("error", "LLM output failed to parse after retries"))
            job.status = "failed"
            job.finished_at = datetime.now(timezone.utc)
            asset.generation_status = "failed"
            asset.payload_json = {**asset.payload_json, "generated": False, "error": job.error_message}
            db.commit()
            print(f"[media-worker] FAILED_TO_GRADE for job {job.id}: {job.error_message}", flush=True)
        elif result.get("error"):
            job.error_message = str(result.get("error"))
            _apply_generation_result(db, job, result, "failed")
        elif result.get("message") in {"No models found.", "No suitable model found."}:
            job.error_message = str(result.get("message"))
            _apply_generation_result(db, job, result, "failed")
        else:
            _apply_generation_result(db, job, result, "ready")
    except Exception as exc:
        job.error_message = str(exc)
        job.status = "failed"
        job.finished_at = datetime.now(timezone.utc)
        asset.generation_status = "failed"
        asset.payload_json = {**asset.payload_json, "generated": False, "error": str(exc)}
        db.commit()
        print("[media-worker] Asset update committed to DB", flush=True)