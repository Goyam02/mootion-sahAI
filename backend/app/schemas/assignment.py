from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

INTERACTIVE_ASSIGNMENT_TYPES = Literal[
    "video", "simulation", "model", "quiz",
    "explain_ai", "predict_ai", "spot_it", "connect_it",
    "EXPLAIN_IT", "PREDICT_IT", "SPOT_IT", "INTERACTIVE_QUIZ",
    "explain_it", "predict_it", "interactive_quiz",
]


class AssignmentCreateRequest(BaseModel):
    chapter_id: str
    assignment_type: str
    title: str
    instructions: str | None = None


class AssignmentRecipientResponse(BaseModel):
    student_id: str


class AssignmentJobResponse(BaseModel):
    job_id: str
    asset_id: str
    asset_type: str
    provider: str
    integration_target: str
    status: str
    result_json: dict[str, Any] | None = None
    error_message: str | None = None


class AssignmentResponse(BaseModel):
    assignment_id: str
    class_id: str
    chapter_id: str
    assignment_type: str
    title: str
    instructions: str | None
    content_json: dict[str, Any]
    status: str
    recipients: list[AssignmentRecipientResponse] = Field(default_factory=list)
    jobs: list[AssignmentJobResponse] = Field(default_factory=list)


class AssignmentListItem(BaseModel):
    assignment_id: str
    class_id: str
    chapter_id: str
    assignment_type: str
    title: str
    status: str
    recipient_count: int
    job_count: int


class StudentAssignmentListItem(BaseModel):
    assignment_id: str
    class_id: str
    chapter_id: str
    assignment_type: str
    title: str
    status: str
    job_count: int


class StudentAssignmentResponse(BaseModel):
    assignment_id: str
    class_id: str
    chapter_id: str
    assignment_type: str
    title: str
    instructions: str | None
    content_json: dict[str, Any]
    status: str
    jobs: list[AssignmentJobResponse] = Field(default_factory=list)


ASSIGNMENT_TYPE_DISPLAY_NAMES: dict[str, str] = {
    "video": "Watch Video",
    "simulation": "Simulation",
    "model": "3D Model",
    "quiz": "Quiz",
    "explain_ai": "Explain It",
    "predict_ai": "Predict It",
    "spot_it": "Spot It",
    "connect_it": "Connect It",
    "EXPLAIN_IT": "Explain It",
    "PREDICT_IT": "Predict It",
    "SPOT_IT": "Spot It",
    "INTERACTIVE_QUIZ": "Interactive Quiz",
    "explain_it": "Explain It",
    "predict_it": "Predict It",
    "interactive_quiz": "Interactive Quiz",
}
