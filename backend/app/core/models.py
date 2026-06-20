from __future__ import annotations

import uuid

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.types import TypeDecorator, CHAR
from sqlalchemy.dialects.postgresql import UUID as pgUUID

class GUID(TypeDecorator):
    impl = CHAR
    cache_ok = True

    def __init__(self, as_uuid=True):
        super().__init__()

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(pgUUID(as_uuid=True))
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if not isinstance(value, uuid.UUID):
            try:
                return str(uuid.UUID(value))
            except ValueError:
                return value
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if not isinstance(value, uuid.UUID):
            try:
                return uuid.UUID(value)
            except ValueError:
                return value
        return value

UUID = GUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    login_id = Column(String(64), unique=True, index=True, nullable=False)
    role = Column(String(20), nullable=False)
    full_name = Column(String(255), nullable=False)

    password_hash = Column(Text, nullable=False)

    preferred_language = Column(
        String(20),
        nullable=False,
        default="english",
    )

    onboarding_completed = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    oauth_accounts = relationship(
        "OAuthAccount",
        backref="user",
        cascade="all, delete-orphan",
    )

    sessions = relationship(
        "Session",
        backref="user",
        cascade="all, delete-orphan",
    )


class OAuthAccount(Base):
    __tablename__ = "oauth_accounts"

    __table_args__ = (
        UniqueConstraint(
            "provider",
            "provider_user_id",
            name="uq_provider_user",
        ),
    )

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    provider = Column(String(32), nullable=False, index=True)

    provider_user_id = Column(
        String(255),
        nullable=False,
    )

    email = Column(String(255), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class OAuthState(Base):
    __tablename__ = "oauth_states"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    provider = Column(String(32), nullable=False)

    requested_role = Column(String(20), nullable=False)

    state = Column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    expires_at = Column(
        DateTime(timezone=True),
        nullable=False,
    )


class Session(Base):
    __tablename__ = "sessions"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    refresh_token_hash = Column(
        String(128),
        nullable=False,
        unique=True,
        index=True,
    )

    expires_at = Column(
        DateTime(timezone=True),
        nullable=False,
    )

    revoked_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class School(Base):
    __tablename__ = "schools"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    code = Column(String(32), unique=True, index=True, nullable=False)
    created_by_teacher_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class TeacherSchoolMembership(Base):
    __tablename__ = "teacher_school_memberships"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    teacher_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    school_id = Column(UUID(as_uuid=True), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ClassRoom(Base):
    __tablename__ = "classes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id = Column(UUID(as_uuid=True), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True)
    grade = Column(String(16), nullable=False)
    subject = Column(String(255), nullable=False)
    class_code = Column(String(32), unique=True, index=True, nullable=False)
    display_name = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class TeacherClassMembership(Base):
    __tablename__ = "teacher_class_memberships"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    teacher_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    class_id = Column(UUID(as_uuid=True), ForeignKey("classes.id", ondelete="CASCADE"), nullable=False, index=True)
    is_primary = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class StudentClassMembership(Base):
    __tablename__ = "student_class_memberships"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    class_id = Column(UUID(as_uuid=True), ForeignKey("classes.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class CurriculumPlan(Base):
    __tablename__ = "curriculum_plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    class_id = Column(UUID(as_uuid=True), ForeignKey("classes.id", ondelete="CASCADE"), nullable=False, index=True)
    created_by_teacher_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    version = Column(Integer, nullable=False, default=1)
    title = Column(String(255), nullable=False)
    source_type = Column(String(32), nullable=False, default="manual")
    source_text = Column(Text, nullable=True)
    source_subject = Column(String(255), nullable=True)
    document_id = Column(String(255), nullable=True)
    curriculum_data = Column(JSON, nullable=False)
    status = Column(String(20), nullable=False, default="draft")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class CurriculumSnapshot(Base):
    __tablename__ = "curriculum_snapshots"

    __table_args__ = (
        UniqueConstraint("curriculum_id", "version", name="uq_curriculum_snapshot_version"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    curriculum_id = Column(UUID(as_uuid=True), ForeignKey("curriculum_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    version = Column(Integer, nullable=False)
    patch_operation = Column(String(32), nullable=False, default="create")
    patch_payload = Column(JSON, nullable=False)
    curriculum_data = Column(JSON, nullable=False)
    created_by_teacher_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Chapter(Base):
    __tablename__ = "chapters"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    class_id = Column(UUID(as_uuid=True), ForeignKey("classes.id", ondelete="CASCADE"), nullable=False, index=True)
    curriculum_id = Column(UUID(as_uuid=True), ForeignKey("curriculum_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    source_node_id = Column(String(255), nullable=True)
    sequence_number = Column(Integer, nullable=False, default=0)
    title = Column(String(255), nullable=False)
    status = Column(String(20), nullable=False, default="unset")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    topics = relationship("ChapterTopic", backref="chapter", cascade="all, delete-orphan")


class ChapterAsset(Base):
    __tablename__ = "chapter_assets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chapter_id = Column(UUID(as_uuid=True), ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False, index=True)
    asset_type = Column(String(32), nullable=False)
    provider = Column(String(32), nullable=False, default="placeholder")
    integration_target = Column(String(64), nullable=False, default="placeholder")
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    payload_json = Column(JSON, nullable=False)
    generation_status = Column(String(20), nullable=False, default="placeholder")
    external_url = Column(String(500), nullable=True)
    storage_bucket = Column(String(128), nullable=True)
    storage_key = Column(String(512), nullable=True)
    last_generated_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ChapterTopic(Base):
    __tablename__ = "chapter_topics"

    __table_args__ = (
        UniqueConstraint("chapter_id", "sequence_number", name="uq_chapter_topic_sequence"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chapter_id = Column(UUID(as_uuid=True), ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False, index=True)
    source_node_id = Column(String(255), nullable=True)
    sequence_number = Column(Integer, nullable=False, default=0)
    title = Column(String(255), nullable=False)
    source_text = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="unset")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    assets = relationship("ChapterTopicAsset", backref="topic", cascade="all, delete-orphan")


class ChapterTopicAsset(Base):
    __tablename__ = "chapter_topic_assets"

    __table_args__ = (
        UniqueConstraint("topic_id", "asset_type", name="uq_topic_asset_type"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    topic_id = Column(UUID(as_uuid=True), ForeignKey("chapter_topics.id", ondelete="CASCADE"), nullable=False, index=True)
    asset_type = Column(String(32), nullable=False)
    provider = Column(String(32), nullable=False, default="placeholder")
    integration_target = Column(String(64), nullable=False, default="placeholder")
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    payload_json = Column(JSON, nullable=False)
    generation_status = Column(String(20), nullable=False, default="placeholder")
    external_url = Column(String(500), nullable=True)
    storage_bucket = Column(String(128), nullable=True)
    storage_key = Column(String(512), nullable=True)
    last_generated_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Assignment(Base):
    __tablename__ = "assignments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    class_id = Column(UUID(as_uuid=True), ForeignKey("classes.id", ondelete="CASCADE"), nullable=False, index=True)
    chapter_id = Column(UUID(as_uuid=True), ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False, index=True)
    created_by_teacher_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    assignment_type = Column(String(32), nullable=False)
    title = Column(String(255), nullable=False)
    instructions = Column(Text, nullable=True)
    content_json = Column(JSON, nullable=False, default=dict)
    status = Column(String(20), nullable=False, default="queued")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class AssignmentRecipient(Base):
    __tablename__ = "assignment_recipients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assignment_id = Column(UUID(as_uuid=True), ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ChapterAssetGenerationJob(Base):
    __tablename__ = "chapter_asset_generation_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assignment_id = Column(UUID(as_uuid=True), ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False, index=True)
    chapter_asset_id = Column(UUID(as_uuid=True), ForeignKey("chapter_assets.id", ondelete="CASCADE"), nullable=False, index=True)
    asset_type = Column(String(32), nullable=False)
    provider = Column(String(32), nullable=False)
    integration_target = Column(String(64), nullable=False)
    status = Column(String(20), nullable=False, default="queued")
    attempt_count = Column(Integer, nullable=False, default=0)
    payload_json = Column(JSON, nullable=False)
    result_json = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    queued_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)


class StudentAttempt(Base):
    __tablename__ = "student_attempts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    assignment_id = Column(UUID(as_uuid=True), ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False, index=True)
    score_understanding = Column(Integer, nullable=False, default=0)
    score_reasoning = Column(Integer, nullable=False, default=0)
    score_expression = Column(Integer, nullable=False, default=0)
    transcription_text = Column(Text, nullable=True)
    ai_feedback = Column(Text, nullable=True)
    attempt_language = Column(String(20), nullable=False, default="english")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class StudentDoubt(Base):
    __tablename__ = "student_doubts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    class_id = Column(UUID(as_uuid=True), ForeignKey("classes.id", ondelete="CASCADE"), nullable=False, index=True)
    topic = Column(String(255), nullable=False)
    query_text = Column(Text, nullable=False)
    tried_before = Column(Boolean, nullable=False, default=False)
    attempt_text = Column(Text, nullable=True)
    clarification_video_url = Column(String(500), nullable=True)
    status = Column(String(20), nullable=False, default="pending")  # "pending", "resolved", "responded"
    response_text = Column(Text, nullable=True)
    response_audio_url = Column(String(500), nullable=True)
    messages = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class UserQuota(Base):
    __tablename__ = "user_quotas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    doubt_videos_used_today = Column(Integer, nullable=False, default=0)
    playground_items_used_week = Column(Integer, nullable=False, default=0)
    last_doubt_reset = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_playground_reset = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class SimulationRecord(Base):
    __tablename__ = "simulation_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    simulation_id = Column(String(64), unique=True, index=True, nullable=False)
    prompt = Column(Text, nullable=True)
    spec_json = Column(JSON, nullable=True)
    html = Column(Text, nullable=False, default="")
    validation_json = Column(JSON, nullable=True)
    quality_score = Column(Integer, nullable=False, default=0)
    assessments_json = Column(JSON, nullable=True)
    phase = Column(String(32), nullable=False, default="pending")
    error = Column(Text, nullable=True)
    duration_ms = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class StudentAiChatThread(Base):
    __tablename__ = "student_ai_chat_threads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    class_id = Column(UUID(as_uuid=True), ForeignKey("classes.id", ondelete="SET NULL"), nullable=True, index=True)
    chapter_id = Column(UUID(as_uuid=True), ForeignKey("chapters.id", ondelete="SET NULL"), nullable=True, index=True)
    assignment_id = Column(UUID(as_uuid=True), ForeignKey("assignments.id", ondelete="SET NULL"), nullable=True, index=True)
    title = Column(String(255), nullable=True)
    status = Column(String(20), nullable=False, default="active")
    context_json = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class StudentAiChatMessage(Base):
    __tablename__ = "student_ai_chat_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chat_id = Column(UUID(as_uuid=True), ForeignKey("student_ai_chat_threads.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    tool_name = Column(String(64), nullable=True)
    tool_input_json = Column(JSON, nullable=True)
    tool_output_json = Column(JSON, nullable=True)
    asset_type = Column(String(32), nullable=True)
    asset_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ConceptScore(Base):
    __tablename__ = "concept_scores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    chapter_id = Column(UUID(as_uuid=True), ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False, index=True)
    class_id = Column(UUID(as_uuid=True), ForeignKey("classes.id", ondelete="CASCADE"), nullable=False, index=True)
    transcript = Column(Text, nullable=True)
    clarity_score = Column(Float, nullable=True)
    accuracy_score = Column(Float, nullable=True)
    depth_score = Column(Float, nullable=True)
    overall_score = Column(Float, nullable=True)
    llm_feedback = Column(Text, nullable=True)
    attempt_number = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    student = relationship("User", foreign_keys=[student_id])
    chapter = relationship("Chapter", foreign_keys=[chapter_id])
    classroom = relationship("ClassRoom", foreign_keys=[class_id])


class StudentTopicCluster(Base):
    __tablename__ = "student_topic_clusters"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    class_id = Column(UUID(as_uuid=True), ForeignKey("classes.id", ondelete="CASCADE"), nullable=False, index=True)
    chapter_id = Column(UUID(as_uuid=True), ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False, index=True)
    cluster_label = Column(String(50), nullable=False)
    student_ids = Column(JSON, nullable=False)
    avg_score = Column(Float, nullable=False)
    computed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    classroom = relationship("ClassRoom", foreign_keys=[class_id])
    chapter = relationship("Chapter", foreign_keys=[chapter_id])
