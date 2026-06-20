from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class TeacherPreferenceOnboardingRequest(BaseModel):
    preferred_language: str = Field(default="english")


class TeacherPreferenceOnboardingResponse(BaseModel):
    preferred_language: str


class TeacherClassCreateRequest(BaseModel):
    grade: str = Field(min_length=1, max_length=16)
    subject: str = Field(min_length=1, max_length=255)

    @field_validator("grade")
    @classmethod
    def validate_grade(cls, value: str) -> str:
        clean_val = value.strip()
        import re
        match = re.search(r"\d+", clean_val)
        if not match:
            raise ValueError("Grade must contain a valid number")
        grade_num = int(match.group(0))
        if grade_num < 6 or grade_num > 12:
            raise ValueError(f"Unsupported grade: {value}. Product only supports grades 6-12.")
        return str(grade_num)


class TeacherClassCreateResponse(BaseModel):
    class_id: str
    class_code: str
    display_name: str
    grade: str
    subject: str


class ClassSummaryResponse(BaseModel):
    class_id: str
    class_code: str
    display_name: str
    grade: str
    subject: str


class TeacherOnboardingCompleteRequest(BaseModel):
    load_ncert: bool = True


class TeacherOnboardingCompleteResponse(BaseModel):
    onboarding_completed: bool
    ncert_requested: bool


class StudentJoinClassRequest(BaseModel):
    class_code: str = Field(min_length=3, max_length=32)


class StudentJoinClassResponse(BaseModel):
    class_id: str
    class_code: str
    display_name: str
    joined: bool


class StudentLanguageRequest(BaseModel):
    preferred_language: str = Field(default="english")


class StudentLanguageResponse(BaseModel):
    preferred_language: str
