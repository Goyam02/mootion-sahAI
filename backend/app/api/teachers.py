from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_teacher
from app.schemas.auth import UserResponse
from app.schemas.onboarding import (
    ClassSummaryResponse,
    TeacherClassCreateRequest,
    TeacherClassCreateResponse,
    TeacherOnboardingCompleteRequest,
    TeacherOnboardingCompleteResponse,
    TeacherPreferenceOnboardingRequest,
    TeacherPreferenceOnboardingResponse,
)
from app.schemas.student_actions import (
    ClassAnalyticsOverview,
    StudentDoubtResponse,
    TeacherDoubtRespondRequest,
)
from app.services.onboarding_service import (
    create_teacher_class,
    complete_teacher_onboarding,
    list_teacher_classes,
    setup_teacher_preferences,
)
from app.services.student_actions_service import (
    get_class_analytics_overview,
    get_chapter_analytics_drill,
    get_student_analytics_drill,
    list_class_doubts,
    respond_to_doubt,
    resolve_teacher_doubt,
)

router = APIRouter(prefix="/teachers", tags=["teachers"])


@router.get("/me", response_model=UserResponse)
def teacher_me(user=Depends(require_teacher)):
    return UserResponse(
        user_id=str(user.id),
        login_id=user.login_id,
        role=user.role,
        full_name=user.full_name,
        preferred_language=user.preferred_language,
        onboarding_completed=user.onboarding_completed,
    )


@router.post("/onboarding/preferences", response_model=TeacherPreferenceOnboardingResponse)
def teacher_onboarding_preferences(
    request: TeacherPreferenceOnboardingRequest,
    user=Depends(require_teacher),
    db: Session = Depends(get_db),
):
    return setup_teacher_preferences(db, user, request)


@router.post("/classes", response_model=TeacherClassCreateResponse)
def teacher_create_class(
    request: TeacherClassCreateRequest,
    user=Depends(require_teacher),
    db: Session = Depends(get_db),
):
    return create_teacher_class(db, user, request)


@router.get("/classes", response_model=list[ClassSummaryResponse])
def teacher_classes(user=Depends(require_teacher), db: Session = Depends(get_db)):
    return list_teacher_classes(db, user)


@router.post("/onboarding/complete", response_model=TeacherOnboardingCompleteResponse)
def teacher_onboarding_complete(
    request: TeacherOnboardingCompleteRequest,
    user=Depends(require_teacher),
    db: Session = Depends(get_db),
):
    return complete_teacher_onboarding(db, user, request)


@router.get("/classes/{class_id}/analytics/overview", response_model=ClassAnalyticsOverview)
def get_teacher_class_analytics(
    class_id: str,
    user=Depends(require_teacher),
    db: Session = Depends(get_db),
):
    return get_class_analytics_overview(db, user, class_id)


@router.get("/classes/{class_id}/chapters/{chapter_id}/analytics")
def get_teacher_chapter_analytics(
    class_id: str,
    chapter_id: str,
    user=Depends(require_teacher),
    db: Session = Depends(get_db),
):
    return get_chapter_analytics_drill(db, user, class_id, chapter_id)


@router.get("/students/{student_id}/analytics")
def get_teacher_student_analytics(
    student_id: str,
    user=Depends(require_teacher),
    db: Session = Depends(get_db),
):
    return get_student_analytics_drill(db, user, student_id)


@router.get("/classes/{class_id}/doubts", response_model=list[StudentDoubtResponse])
def get_teacher_class_doubts(
    class_id: str,
    user=Depends(require_teacher),
    db: Session = Depends(get_db),
):
    return list_class_doubts(db, class_id)


@router.post("/doubts/{doubt_id}/respond", response_model=StudentDoubtResponse)
def teacher_respond_doubt(
    doubt_id: str,
    request: TeacherDoubtRespondRequest,
    user=Depends(require_teacher),
    db: Session = Depends(get_db),
):
    return respond_to_doubt(
        db=db,
        teacher=user,
        doubt_id=doubt_id,
        response_text=request.response_text,
        voice_note_file_url=request.voice_note_file_url,
    )


@router.post("/doubts/{doubt_id}/resolve", response_model=StudentDoubtResponse)
def teacher_resolve_student_doubt(
    doubt_id: str,
    user=Depends(require_teacher),
    db: Session = Depends(get_db),
):
    return resolve_teacher_doubt(db, user, doubt_id)


@router.get("/classes/{class_id}/students/analytics")
def get_class_students_analytics(
    class_id: str,
    user=Depends(require_teacher),
    db: Session = Depends(get_db),
):
    from fastapi import HTTPException
    from app.core.models import (
        TeacherClassMembership,
        StudentClassMembership,
        Assignment,
        StudentAttempt,
        User,
        Chapter,
    )

    # Verify teacher class access
    membership = db.query(TeacherClassMembership).filter(
        TeacherClassMembership.teacher_id == user.id,
        TeacherClassMembership.class_id == class_id,
    ).first()
    if not membership:
        raise HTTPException(status_code=403, detail="Forbidden")

    # Fetch all students in the class
    students_membership = db.query(StudentClassMembership).filter(
        StudentClassMembership.class_id == class_id
    ).all()

    # Fetch all assignments in this class
    assignments = db.query(Assignment).filter(Assignment.class_id == class_id).all()
    assign_ids = [str(a.id) for a in assignments]
    total_assignments = len(assign_ids)

    result = []
    for sm in students_membership:
        student = db.query(User).filter(User.id == sm.student_id).first()
        if not student:
            continue

        # Get attempts for these assignments
        if assign_ids:
            attempts = db.query(StudentAttempt).filter(
                StudentAttempt.student_id == student.id,
                StudentAttempt.assignment_id.in_(assign_ids)
            ).all()
        else:
            attempts = []

        completed_count = len(set(str(att.assignment_id) for att in attempts))
        progress = round(completed_count / total_assignments * 100) if total_assignments > 0 else 0

        # Calculate averages and gather completed chapters
        completed_chapters = []
        recent_misconceptions = []
        latest_attempt = None

        if attempts:
            u_avg = sum(att.score_understanding for att in attempts) / len(attempts)
            r_avg = sum(att.score_reasoning for att in attempts) / len(attempts)
            e_avg = sum(att.score_expression for att in attempts) / len(attempts)
            
            # Sort attempts by created_at desc to find latest
            sorted_attempts = sorted(attempts, key=lambda x: x.created_at, reverse=True)
            latest_attempt = sorted_attempts[0]
            
            for att in attempts:
                assign = db.query(Assignment).filter(Assignment.id == att.assignment_id).first()
                if assign and assign.chapter_id:
                    chapter = db.query(Chapter).filter(Chapter.id == assign.chapter_id).first()
                    if chapter and chapter.title not in completed_chapters:
                        completed_chapters.append(chapter.title)
                
                # Check for misconceptions in AI feedback
                if att.ai_feedback and ("misconception" in att.ai_feedback.lower() or "incorrectly" in att.ai_feedback.lower()):
                    import re
                    sentences = re.split(r'[.!?]', att.ai_feedback)
                    for s in sentences:
                        if "misconception" in s.lower() or "believe" in s.lower() or "think" in s.lower():
                            snippet = s.strip()
                            if snippet and snippet not in recent_misconceptions:
                                recent_misconceptions.append(snippet)
        else:
            u_avg, r_avg, e_avg = 0.0, 0.0, 0.0

        ai_result = None
        if latest_attempt:
            assign = db.query(Assignment).filter(Assignment.id == latest_attempt.assignment_id).first()
            prompt_text = assign.instructions if assign else "Explain the concept"
            ai_result = {
                "prompt": prompt_text,
                "answer": latest_attempt.transcription_text or "",
                "feedback": latest_attempt.ai_feedback or "",
                "score": f"{round((latest_attempt.score_understanding + latest_attempt.score_reasoning + latest_attempt.score_expression) / 3, 1)} / 3.0"
            }

        result.append({
            "student_id": str(student.id),
            "name": student.full_name,
            "understanding": round(u_avg, 1),
            "reasoning": round(r_avg, 1),
            "expression": round(e_avg, 1),
            "progress": progress,
            "completedChapters": completed_chapters,
            "recentMisconceptions": recent_misconceptions[:2],
            "recentAiResult": ai_result
        })

    return result

