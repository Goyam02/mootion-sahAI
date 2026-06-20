from __future__ import annotations

import collections
import json
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_student, require_teacher, require_teacher_or_student
from app.core.models import (
    ConceptScore,
    User,
    ClassRoom,
    Chapter,
    TeacherClassMembership,
    StudentClassMembership,
    StudentTopicCluster,
)
from app.services.chat_ai_service import _get_client, _extract_json
from app.services.clustering_service import compute_clusters
from app.core.config import settings

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


class ExplanationSubmitRequest(BaseModel):
    chapter_id: str
    class_id: str
    transcript: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "chapter_id": "8cebb50b-b149-41d1-8329-22f97208fda7",
                "class_id": "e367f530-a63e-4caa-8942-105fad01378d",
                "transcript": "Cell division is the process by which a parent cell divides into two or more daughter cells. It usually occurs as part of a larger cell cycle."
            }
        }
    }


@router.post(
    "/submit-explanation",
    responses={
        200: {
            "description": "Explanation successfully submitted and graded",
            "content": {
                "application/json": {
                    "example": {
                        "concept_score_id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
                        "clarity_score": 8.5,
                        "accuracy_score": 9.0,
                        "depth_score": 7.0,
                        "overall_score": 8.2,
                        "llm_feedback": "The explanation of cell division is clear and accurate. It covers the basic definition well, though it could expand slightly on the phases of the cell cycle.",
                        "attempt_number": 1,
                        "created_at": "2026-06-19T21:55:00Z"
                    }
                }
            }
        }
    }
)
def submit_explanation(
    request: ExplanationSubmitRequest,
    user=Depends(require_student),
    db: Session = Depends(get_db),
):
    # Verify chapter and classroom exist
    classroom = db.get(ClassRoom, UUID(request.class_id))
    if not classroom:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Classroom not found")

    chapter = db.get(Chapter, UUID(request.chapter_id))
    if not chapter:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chapter not found")

    # Determine attempt number
    existing_count = db.query(func.count(ConceptScore.id)).filter(
        ConceptScore.student_id == user.id,
        ConceptScore.chapter_id == UUID(request.chapter_id),
        ConceptScore.class_id == UUID(request.class_id)
    ).scalar() or 0
    attempt_number = existing_count + 1

    # Call LLM
    client = _get_client()
    try:
        response = client.chat.completions.create(
            model=settings.azure_openai_deployment,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an education evaluator. A student explained a science concept. "
                        "Score their explanation on: clarity (0-10), accuracy (0-10), depth (0-10). "
                        "Also give a 2-sentence feedback. Return JSON only: "
                        "{ \"clarity_score\": ..., \"accuracy_score\": ..., \"depth_score\": ..., \"overall_score\": ..., \"llm_feedback\": \"...\" }"
                    )
                },
                {
                    "role": "user",
                    "content": request.transcript
                }
            ],
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        data = _extract_json(content)
        if not data or not isinstance(data, dict):
            raise ValueError("Invalid LLM response format")
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to generate score from LLM: {str(exc)}"
        )

    # Save to database
    concept_score = ConceptScore(
        student_id=user.id,
        chapter_id=UUID(request.chapter_id),
        class_id=UUID(request.class_id),
        transcript=request.transcript,
        clarity_score=float(data.get("clarity_score", 0)),
        accuracy_score=float(data.get("accuracy_score", 0)),
        depth_score=float(data.get("depth_score", 0)),
        overall_score=float(data.get("overall_score", 0)),
        llm_feedback=data.get("llm_feedback", ""),
        attempt_number=attempt_number
    )
    db.add(concept_score)
    db.commit()
    db.refresh(concept_score)

    return {
        "concept_score_id": str(concept_score.id),
        "clarity_score": concept_score.clarity_score,
        "accuracy_score": concept_score.accuracy_score,
        "depth_score": concept_score.depth_score,
        "overall_score": concept_score.overall_score,
        "llm_feedback": concept_score.llm_feedback,
        "attempt_number": concept_score.attempt_number,
        "created_at": concept_score.created_at
    }


@router.get(
    "/student/{student_id}/scores",
    responses={
        200: {
            "description": "Student score history grouped by chapter",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "chapter_id": "8cebb50b-b149-41d1-8329-22f97208fda7",
                            "scores": [
                                {
                                    "id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
                                    "transcript": "Cell division is the process by which a parent cell divides...",
                                    "clarity_score": 8.5,
                                    "accuracy_score": 9.0,
                                    "depth_score": 7.0,
                                    "overall_score": 8.2,
                                    "llm_feedback": "The explanation of cell division is clear and accurate.",
                                    "attempt_number": 1,
                                    "created_at": "2026-06-19T21:55:00Z"
                                }
                            ],
                            "trend": "stable"
                        }
                    ]
                }
            }
        }
    }
)
def get_student_scores(
    student_id: str,
    user=Depends(require_teacher_or_student),
    db: Session = Depends(get_db),
):
    # Authorization checks
    if user.role == "student":
        if str(user.id) != student_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    elif user.role == "teacher":
        # Check if teacher shares a classroom membership with the student
        shared = db.query(TeacherClassMembership.class_id).join(
            StudentClassMembership,
            StudentClassMembership.class_id == TeacherClassMembership.class_id
        ).filter(
            TeacherClassMembership.teacher_id == user.id,
            StudentClassMembership.student_id == UUID(student_id)
        ).first()
        if not shared:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    # Retrieve all scores ordered by chapter and attempt
    scores = db.query(ConceptScore).filter(
        ConceptScore.student_id == UUID(student_id)
    ).order_by(ConceptScore.chapter_id, ConceptScore.attempt_number.asc()).all()

    # Group scores by chapter
    grouped = collections.defaultdict(list)
    for s in scores:
        grouped[str(s.chapter_id)].append({
            "id": str(s.id),
            "transcript": s.transcript,
            "clarity_score": s.clarity_score,
            "accuracy_score": s.accuracy_score,
            "depth_score": s.depth_score,
            "overall_score": s.overall_score,
            "llm_feedback": s.llm_feedback,
            "attempt_number": s.attempt_number,
            "created_at": s.created_at
        })

    result = []
    for chap_id, chap_scores in grouped.items():
        if len(chap_scores) < 2:
            trend = "stable"
        else:
            first_score = chap_scores[0]["overall_score"] or 0
            last_score = chap_scores[-1]["overall_score"] or 0
            diff = last_score - first_score
            if diff > 0.5:
                trend = "improving"
            elif diff < -0.5:
                trend = "declining"
            else:
                trend = "stable"

        result.append({
            "chapter_id": chap_id,
            "scores": chap_scores,
            "trend": trend
        })

    return result


@router.get(
    "/class/{class_id}/overview",
    responses={
        200: {
            "description": "Class overview of conceptual understanding per chapter",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "chapter_id": "8cebb50b-b149-41d1-8329-22f97208fda7",
                            "avg_score": 7.8,
                            "student_count": 12,
                            "weakest_students": [
                                {
                                    "student_id": "f5e4d3c2-b1a0-9e8d-7c6b-5a4f3e2d1c0b",
                                    "full_name": "Jane Doe",
                                    "score": 4.5
                                },
                                {
                                    "student_id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
                                    "full_name": "John Smith",
                                    "score": 5.2
                                }
                            ]
                        }
                    ]
                }
            }
        }
    }
)
def get_class_overview(
    class_id: str,
    user=Depends(require_teacher),
    db: Session = Depends(get_db),
):
    # Verify class access
    membership = db.query(TeacherClassMembership).filter(
        TeacherClassMembership.teacher_id == user.id,
        TeacherClassMembership.class_id == UUID(class_id)
    ).first()
    if not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    # Fetch all concept scores for this class
    scores = db.query(ConceptScore).filter(
        ConceptScore.class_id == UUID(class_id)
    ).all()

    # Group scores by chapter
    chap_map = collections.defaultdict(list)
    for s in scores:
        chap_map[str(s.chapter_id)].append(s)

    result = []
    for chap_id, chap_scores in chap_map.items():
        all_overall_scores = [cs.overall_score for cs in chap_scores if cs.overall_score is not None]
        avg_score = sum(all_overall_scores) / len(all_overall_scores) if all_overall_scores else 0

        # Group by student to calculate average scores per student
        student_scores = collections.defaultdict(list)
        for cs in chap_scores:
            if cs.overall_score is not None:
                student_scores[str(cs.student_id)].append(cs.overall_score)

        student_count = len(student_scores)

        student_avgs = []
        for st_id, st_s in student_scores.items():
            st_avg = sum(st_s) / len(st_s)
            st_user = db.get(User, UUID(st_id))
            student_avgs.append({
                "student_id": st_id,
                "full_name": st_user.full_name if st_user else "Unknown Student",
                "score": round(st_avg, 2)
            })

        # Sort ascending by score to find the weakest students
        student_avgs.sort(key=lambda x: x["score"])
        weakest_students = student_avgs[:3]

        result.append({
            "chapter_id": chap_id,
            "avg_score": round(avg_score, 2),
            "student_count": student_count,
            "weakest_students": weakest_students
        })

    return result


class ComputeClustersRequest(BaseModel):
    chapter_id: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "chapter_id": "cea832b6-2f2f-4f2c-94bc-fdddc21884b1"
            }
        }
    }


@router.post(
    "/class/{class_id}/compute-clusters",
    responses={
        200: {
            "description": "Computed clusters successfully",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
                            "class_id": "050979fb-d6d2-4389-8f32-bb6fc3e33dd8",
                            "chapter_id": "cea832b6-2f2f-4f2c-94bc-fdddc21884b1",
                            "cluster_label": "strong",
                            "student_ids": ["c77841e3-cbc6-4869-9f7e-42d5d0e0b79b"],
                            "avg_score": 8.5,
                            "computed_at": "2026-06-19T22:14:00Z"
                        }
                    ]
                }
            }
        }
    }
)
def compute_class_clusters(
    class_id: str,
    request: ComputeClustersRequest,
    user=Depends(require_teacher),
    db: Session = Depends(get_db)
):
    # Verify teacher class access
    membership = db.query(TeacherClassMembership).filter(
        TeacherClassMembership.teacher_id == user.id,
        TeacherClassMembership.class_id == UUID(class_id)
    ).first()
    if not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    # Call compute_clusters
    results = compute_clusters(class_id, request.chapter_id, db)
    if results is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least 3 students with scores are required to compute clusters."
        )

    return [
        {
            "id": str(r.id),
            "class_id": str(r.class_id),
            "chapter_id": str(r.chapter_id),
            "cluster_label": r.cluster_label,
            "student_ids": r.student_ids,
            "avg_score": r.avg_score,
            "computed_at": r.computed_at
        }
        for r in results
    ]


@router.get(
    "/class/{class_id}/clusters",
    responses={
        200: {
            "description": "Retrieved all student clusters for this class with student names",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
                            "class_id": "050979fb-d6d2-4389-8f32-bb6fc3e33dd8",
                            "chapter_id": "cea832b6-2f2f-4f2c-94bc-fdddc21884b1",
                            "cluster_label": "strong",
                            "avg_score": 8.5,
                            "students": [
                                {
                                    "student_id": "c77841e3-cbc6-4869-9f7e-42d5d0e0b79b",
                                    "full_name": "Default Student"
                                }
                            ],
                            "computed_at": "2026-06-19T22:14:00Z"
                        }
                    ]
                }
            }
        }
    }
)
def get_class_clusters(
    class_id: str,
    user=Depends(require_teacher),
    db: Session = Depends(get_db)
):
    # Verify teacher class access
    membership = db.query(TeacherClassMembership).filter(
        TeacherClassMembership.teacher_id == user.id,
        TeacherClassMembership.class_id == UUID(class_id)
    ).first()
    if not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    # Fetch all StudentTopicCluster rows for this class
    clusters = db.query(StudentTopicCluster).filter(
        StudentTopicCluster.class_id == UUID(class_id)
    ).all()

    result = []
    for c in clusters:
        student_list = []
        for sid in (c.student_ids or []):
            student_user = db.get(User, UUID(sid))
            student_list.append({
                "student_id": sid,
                "full_name": student_user.full_name if student_user else "Unknown Student"
            })
        result.append({
            "id": str(c.id),
            "class_id": str(c.class_id),
            "chapter_id": str(c.chapter_id),
            "cluster_label": c.cluster_label,
            "avg_score": c.avg_score,
            "students": student_list,
            "computed_at": c.computed_at
        })
    return result
