# Mootion Backend — API Endpoints & Data Models

> Generated from `backend/` source. Covers routes, request/response schemas, ORM models, and frontend ↔ backend consistency.

---

## Table of Contents
1. [Health](#1-health)
2. [Auth](#2-auth)
3. [Teachers / Onboarding](#3-teachers--onboarding)
4. [Students / Onboarding](#4-students--onboarding)
5. [Curriculum](#5-curriculum)
6. [Chapters](#6-chapters)
7. [Assignments (Teacher)](#7-assignments-teacher)
8. [Assignments (Student)](#8-assignments-student)
9. [Doubts](#9-doubts)
10. [Library](#10-library)
11. [Media](#11-media)
12. [Chat with AI](#12-chat-with-ai)
13. [Simulations](#13-simulations)
14. [Analytics](#14-analytics)
15. [ORM Models](#15-orm-models)
16. [Pydantic Schemas](#16-pydantic-schemas)
17. [Inconsistencies & Flags](#17-inconsistencies--flags)
18. [Open Questions / Risks](#18-open-questions--risks)

---

## 1. Health

| Method | Path | Auth | Request | Response | File |
|--------|------|------|---------|----------|------|
| `GET` | `/` | None | — | `{"status": "ok"}` (ad-hoc dict) | [health.py:6-8](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/api/health.py#L6-L8) |

> [!NOTE]
> `HealthResponse` schema exists in [core/schemas.py:6-7](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/core/schemas.py#L6-L7) but is **not used** by the endpoint.

---

## 2. Auth

Router prefix: `/auth` — [api/auth.py](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/api/auth.py)

| Method | Path | Auth | Request Body | Response Model | Line |
|--------|------|------|-------------|----------------|------|
| `POST` | `/auth/register` | None | `RegisterRequest` | `TokenResponse` | L31-33 |
| `POST` | `/auth/login` | None | `LoginRequest` | `TokenResponse` | L36-38 |
| `POST` | `/auth/refresh` | None | `RefreshRequest` | `TokenResponse` | L41-43 |
| `POST` | `/auth/logout` | None | `RefreshRequest` | ad-hoc dict | L46-48 |
| `POST` | `/auth/google/start` | None | `OAuthStartRequest` | `OAuthStartResponse` | L51-53 |
| `GET` | `/auth/google/callback` | None | query: `code`, `state` | `OAuthCallbackResponse` | L56-58 |
| `GET` | `/auth/me` | Bearer (any role) | — | `UserResponse` | L61-70 |

### Auth Schemas ([schemas/auth.py](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/schemas/auth.py))

| Schema | Fields |
|--------|--------|
| `RegisterRequest` | `login_id: str`, `full_name: str`, `role: str` (teacher\|student), `password: str`, `preferred_language: str = "english"` |
| `LoginRequest` | `login_id: str`, `password: str` |
| `TokenResponse` | `access_token: str`, `refresh_token: str`, `token_type: str = "bearer"`, `role: str`, `user_id: str` |
| `RefreshRequest` | `refresh_token: str` |
| `OAuthStartRequest` | `role: str` (teacher\|student) |
| `OAuthStartResponse` | `authorization_url: str` |
| `OAuthCallbackResponse` | extends `TokenResponse` |
| `UserResponse` | `user_id: str`, `login_id: str`, `role: str`, `full_name: str`, `preferred_language: str`, `onboarding_completed: bool` |

### Auth Dependency ([core/deps.py](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/core/deps.py))

- `get_current_user` — JWT Bearer, returns `User` ORM object (L16-59)
- `require_teacher` — wraps `get_current_user`, checks `role == "teacher"` (L70)
- `require_student` — checks `role == "student"` (L71)
- `require_teacher_or_student` — allows both (L72)

---

## 3. Teachers / Onboarding

Router prefix: `/teachers` — [api/teachers.py](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/api/teachers.py)

| Method | Path | Auth | Request Body | Response Model | Line |
|--------|------|------|-------------|----------------|------|
| `GET` | `/teachers/me` | teacher | — | `UserResponse` | L39-48 |
| `POST` | `/teachers/onboarding/preferences` | teacher | `TeacherPreferenceOnboardingRequest` | `TeacherPreferenceOnboardingResponse` | L51-57 |
| `POST` | `/teachers/classes` | teacher | `TeacherClassCreateRequest` | `TeacherClassCreateResponse` | L60-66 |
| `GET` | `/teachers/classes` | teacher | — | `list[ClassSummaryResponse]` | L69-71 |
| `POST` | `/teachers/onboarding/complete` | teacher | `TeacherOnboardingCompleteRequest` | `TeacherOnboardingCompleteResponse` | L74-80 |
| `GET` | `/teachers/classes/{class_id}/analytics/overview` | teacher | — | `ClassAnalyticsOverview` | L83-89 |
| `GET` | `/teachers/classes/{class_id}/chapters/{chapter_id}/analytics` | teacher | — | ad-hoc dict (untyped) | L92-99 |
| `GET` | `/teachers/students/{student_id}/analytics` | teacher | — | ad-hoc dict (untyped) | L102-108 |
| `GET` | `/teachers/classes/{class_id}/doubts` | teacher | — | `list[StudentDoubtResponse]` | L111-117 |
| `POST` | `/teachers/doubts/{doubt_id}/respond` | teacher | `TeacherDoubtRespondRequest` | `StudentDoubtResponse` | L120-133 |
| `POST` | `/teachers/doubts/{doubt_id}/resolve` | teacher | — | `StudentDoubtResponse` | L136-142 |
| `GET` | `/teachers/classes/{class_id}/students/analytics` | teacher | — | ad-hoc list[dict] (inline logic) | L145-253 |

> [!WARNING]
> **`GET /teachers/classes/{class_id}/students/analytics`** (L145-253) contains ~110 lines of inline business logic with raw ORM queries directly in the route handler. No Pydantic response model. Returns ad-hoc dicts with keys like `completedChapters`, `recentMisconceptions`, `recentAiResult`.

### Teacher Onboarding Schemas ([schemas/onboarding.py](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/schemas/onboarding.py))

| Schema | Fields |
|--------|--------|
| `TeacherPreferenceOnboardingRequest` | `preferred_language: str = "english"` |
| `TeacherPreferenceOnboardingResponse` | `preferred_language: str` |
| `TeacherClassCreateRequest` | `grade: str`, `subject: str` |
| `TeacherClassCreateResponse` | `class_id`, `class_code`, `display_name`, `grade`, `subject` |
| `ClassSummaryResponse` | `class_id`, `class_code`, `display_name`, `grade`, `subject` |
| `TeacherOnboardingCompleteRequest` | `load_ncert: bool = True` |
| `TeacherOnboardingCompleteResponse` | `onboarding_completed: bool`, `ncert_requested: bool` |

---

## 4. Students / Onboarding

Router prefix: `/students` — [api/students.py](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/api/students.py)

| Method | Path | Auth | Request Body | Response Model | Line |
|--------|------|------|-------------|----------------|------|
| `GET` | `/students/me` | student | — | `UserResponse` | L38-47 |
| `POST` | `/students/join-class` | student | `StudentJoinClassRequest` | `StudentJoinClassResponse` | L50-56 |
| `GET` | `/students/classes` | student | — | `list[ClassSummaryResponse]` | L59-61 |
| `POST` | `/students/language` | student | `StudentLanguageRequest` | `StudentLanguageResponse` | L64-70 |
| `POST` | `/students/doubts` | student | `StudentDoubtCreateRequest` | `StudentDoubtResponse` | L73-87 |
| `GET` | `/students/quotas` | student | — | `QuotaResponse` | L90-99 |
| `POST` | `/students/playground/generate` | student | `PlaygroundGenerateRequest` | `PlaygroundGenerateResponse` | L102-113 |
| `GET` | `/students/doubts` | student | — | `list[StudentDoubtResponse]` | L116-121 |
| `POST` | `/students/doubts/{doubt_id}/resolve` | student | — | `StudentDoubtResponse` | L124-130 |
| `POST` | `/students/doubts/{doubt_id}/reply` | student | `StudentDoubtReplyRequest` | `StudentDoubtResponse` | L133-140 |
| `POST` | `/students/doubts/{doubt_id}/reopen` | student | — | `StudentDoubtResponse` | L143-149 |
| `GET` | `/students/classes/{class_id}/chapters` | student | — | `list[ChapterListItem]` | L152-154 |
| `GET` | `/students/classes/{class_id}/chapters/{chapter_id}` | student | — | `ChapterResponse` | L157-159 |

### Student Onboarding Schemas ([schemas/onboarding.py](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/schemas/onboarding.py))

| Schema | Fields |
|--------|--------|
| `StudentJoinClassRequest` | `class_code: str` |
| `StudentJoinClassResponse` | `class_id`, `class_code`, `display_name`, `joined: bool` |
| `StudentLanguageRequest` | `preferred_language: str = "english"` |
| `StudentLanguageResponse` | `preferred_language: str` |

---

## 5. Curriculum

Router prefix: `/teachers/classes/{class_id}/curriculum` — [api/curriculum.py](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/api/curriculum.py)

| Method | Path | Auth | Request Body | Response Model | Line |
|--------|------|------|-------------|----------------|------|
| `POST` | `/teachers/classes/{class_id}/curriculum` | teacher | `CurriculumCreateRequest` | `CurriculumResponse` | L15-17 |
| `POST` | `/teachers/classes/{class_id}/curriculum/bootstrap` | teacher | — | `CurriculumResponse` | L20-22 |
| `POST` | `/teachers/classes/{class_id}/curriculum/bootstrap-bulk` | teacher | — | `CurriculumResponse` | L25-27 |
| `GET` | `/teachers/classes/{class_id}/curriculum` | teacher | — | `list[CurriculumListItem]` | L30-32 |
| `GET` | `/teachers/classes/{class_id}/curriculum/{curriculum_id}` | teacher | — | `CurriculumResponse` | L35-37 |
| `PUT` | `/teachers/classes/{class_id}/curriculum/{curriculum_id}` | teacher | `CurriculumUpdateRequest` | `CurriculumResponse` | L40-42 |
| `PATCH` | `/teachers/classes/{class_id}/curriculum/{curriculum_id}` | teacher | `CurriculumPatchRequest` | `CurriculumPatchResponse` | L45-47 |

### Curriculum Schemas ([schemas/curriculum.py](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/schemas/curriculum.py))

| Schema | Fields |
|--------|--------|
| `CurriculumTreeNode` | `id`, `title`, `kind` (module\|unit\|topic\|subtopic\|lesson), `order`, `metadata`, `children: list[CurriculumTreeNode]` |
| `CurriculumGraphNode` | `id`, `title`, `kind`, `order`, `metadata` |
| `CurriculumGraphEdge` | `id`, `source`, `target`, `kind` (contains\|prerequisite\|related_to) |
| `CurriculumRoadmapData` | `version`, `title`, `subject`, `grade`, `source_type`, `source_text`, `source_subject`, `document_id`, `root: CurriculumTreeNode`, `nodes: list[CurriculumGraphNode]`, `edges: list[CurriculumGraphEdge]` |
| `CurriculumCreateRequest` | `title`, `curriculum_data: CurriculumRoadmapData`, `status` |
| `CurriculumUpdateRequest` | `title?`, `curriculum_data?`, `status?` |
| `CurriculumPatchRequest` | `operation` (add_node\|update_node\|delete_node\|move_node), `expected_version`, `target_node_id?`, `parent_node_id?`, `position?`, `payload` |
| `CurriculumResponse` | `curriculum_id`, `class_id`, `version`, `title`, `source_type`, `source_text`, `source_subject`, `document_id`, `curriculum_data: CurriculumRoadmapData`, `status` |
| `CurriculumPatchResponse` | Same fields as `CurriculumResponse` |
| `CurriculumListItem` | `curriculum_id`, `class_id`, `version`, `title`, `source_type`, `status` |

---

## 6. Chapters

Router prefix: `/teachers/classes/{class_id}/chapters` — [api/chapters.py](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/api/chapters.py)

| Method | Path | Auth | Request Body | Response Model | Line |
|--------|------|------|-------------|----------------|------|
| `POST` | `/teachers/classes/{class_id}/chapters/bootstrap` | teacher | `ChapterBootstrapRequest` (inline) | `ChapterBootstrapResponse` | L28-35 |
| `GET` | `/teachers/classes/{class_id}/chapters` | teacher | — | `list[ChapterListItem]` | L38-40 |
| `GET` | `/teachers/classes/{class_id}/chapters/{chapter_id}` | teacher | — | `ChapterResponse` | L43-45 |
| `POST` | `/teachers/classes/{class_id}/chapters/{chapter_id}/assets/{asset_id}/generate` | teacher | `ChapterAssetGenerateRequest` | `ChapterAssetGenerateResponse` | L48-57 |
| `POST` | `/teachers/classes/{class_id}/chapters/{chapter_id}/topics/{topic_id}/assets/{asset_id}/generate` | teacher | `ChapterTopicAssetGenerateRequest` | `ChapterTopicAssetGenerateResponse` | L60-70 |

> [!NOTE]
> `ChapterBootstrapRequest` is defined **inline** in the route file (L24-25) rather than in `schemas/chapter.py`. Contains single field `curriculum_id: str`.

### Chapter Schemas ([schemas/chapter.py](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/schemas/chapter.py))

| Schema | Fields |
|--------|--------|
| `ChapterAssetResponse` | `asset_id`, `asset_type`, `provider`, `integration_target`, `title`, `description?`, `generation_status`, `external_url?`, `payload_json` |
| `ChapterTopicAssetResponse` | Same shape as `ChapterAssetResponse` |
| `ChapterTopicResponse` | `topic_id`, `chapter_id`, `source_node_id?`, `sequence_number`, `title`, `source_text?`, `status`, `assets: list[ChapterTopicAssetResponse]` |
| `ChapterResponse` | `chapter_id`, `class_id`, `curriculum_id`, `source_node_id?`, `sequence_number`, `title`, `status`, `assets`, `topics`, `subtopics: list[SubtopicResponse]` |
| `ChapterListItem` | `chapter_id`, `class_id`, `sequence_number`, `title`, `status`, `asset_count`, `topic_count` |
| `ChapterBootstrapResponse` | `class_id`, `curriculum_id`, `created_chapters`, `created_topics` |
| `ChapterAssetGenerateRequest` | `instructions?` |
| `ChapterAssetGenerateResponse` | `chapter_id`, `estimated_seconds`, `asset: ChapterAssetResponse` |
| `ChapterTopicAssetGenerateRequest` | `instructions?` |
| `ChapterTopicAssetGenerateResponse` | `chapter_id`, `topic_id`, `estimated_seconds`, `asset: ChapterTopicAssetResponse` |
| `SubtopicResponse` | `subtopic_id`, `title`, `order`, `kind`, `metadata` |

---

## 7. Assignments (Teacher)

Router prefix: `/teachers/classes/{class_id}/assignments` — [api/assignments.py](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/api/assignments.py)

| Method | Path | Auth | Request Body | Response Model | Line |
|--------|------|------|-------------|----------------|------|
| `POST` | `/teachers/classes/{class_id}/assignments` | teacher | `AssignmentCreateRequest` | `AssignmentResponse` | L15-22 |
| `GET` | `/teachers/classes/{class_id}/assignments` | teacher | — | `list[AssignmentListItem]` | L25-27 |
| `GET` | `/teachers/classes/{class_id}/assignments/{assignment_id}` | teacher | — | `AssignmentResponse` | L30-32 |

### Assignment Schemas ([schemas/assignment.py](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/schemas/assignment.py))

| Schema | Fields |
|--------|--------|
| `AssignmentCreateRequest` | `chapter_id`, `assignment_type`, `title`, `instructions?` |
| `AssignmentResponse` | `assignment_id`, `class_id`, `chapter_id`, `assignment_type`, `title`, `instructions?`, `content_json`, `status`, `recipients: list[AssignmentRecipientResponse]`, `jobs: list[AssignmentJobResponse]` |
| `AssignmentListItem` | `assignment_id`, `class_id`, `chapter_id`, `assignment_type`, `title`, `status`, `recipient_count`, `job_count` |
| `AssignmentRecipientResponse` | `student_id` |
| `AssignmentJobResponse` | `job_id`, `asset_id`, `asset_type`, `provider`, `integration_target`, `status`, `result_json?`, `error_message?` |

---

## 8. Assignments (Student)

Router prefix: `/students/classes/{class_id}/assignments` — [api/student_assignments.py](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/api/student_assignments.py)

| Method | Path | Auth | Request Body | Response Model | Line |
|--------|------|------|-------------|----------------|------|
| `GET` | `/students/classes/{class_id}/assignments` | student | — | `list[StudentAssignmentListItem]` | L17-19 |
| `GET` | `/students/classes/{class_id}/assignments/{assignment_id}` | student | — | `StudentAssignmentResponse` | L22-24 |
| `POST` | `/students/classes/{class_id}/assignments/{assignment_id}/submit` | student | `StudentAttemptSubmitRequest` | `StudentAttemptResponse` | L27-41 |

### Student Assignment Schemas ([schemas/assignment.py](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/schemas/assignment.py))

| Schema | Fields |
|--------|--------|
| `StudentAssignmentListItem` | `assignment_id`, `class_id`, `chapter_id`, `assignment_type`, `title`, `status`, `job_count` |
| `StudentAssignmentResponse` | `assignment_id`, `class_id`, `chapter_id`, `assignment_type`, `title`, `instructions?`, `content_json`, `status`, `jobs` |

### Student Attempt Schemas ([schemas/student_actions.py](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/schemas/student_actions.py))

| Schema | Fields |
|--------|--------|
| `StudentAttemptSubmitRequest` | `transcription_text: str`, `language: str = "english"` |
| `StudentAttemptResponse` | `attempt_id`, `score_understanding`, `score_reasoning`, `score_expression`, `ai_feedback` |

---

## 9. Doubts

Doubts are split across **two routers**:

### Student-side (in [api/students.py](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/api/students.py))

| Method | Path | Auth | Request Body | Response Model | Line |
|--------|------|------|-------------|----------------|------|
| `POST` | `/students/doubts` | student | `StudentDoubtCreateRequest` | `StudentDoubtResponse` | L73-87 |
| `GET` | `/students/doubts` | student | — | `list[StudentDoubtResponse]` | L116-121 |
| `POST` | `/students/doubts/{doubt_id}/resolve` | student | — | `StudentDoubtResponse` | L124-130 |
| `POST` | `/students/doubts/{doubt_id}/reply` | student | `StudentDoubtReplyRequest` | `StudentDoubtResponse` | L133-140 |
| `POST` | `/students/doubts/{doubt_id}/reopen` | student | — | `StudentDoubtResponse` | L143-149 |

### Teacher-side (in [api/teachers.py](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/api/teachers.py))

| Method | Path | Auth | Request Body | Response Model | Line |
|--------|------|------|-------------|----------------|------|
| `GET` | `/teachers/classes/{class_id}/doubts` | teacher | — | `list[StudentDoubtResponse]` | L111-117 |
| `POST` | `/teachers/doubts/{doubt_id}/respond` | teacher | `TeacherDoubtRespondRequest` | `StudentDoubtResponse` | L120-133 |
| `POST` | `/teachers/doubts/{doubt_id}/resolve` | teacher | — | `StudentDoubtResponse` | L136-142 |

### Doubt Schemas ([schemas/student_actions.py](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/schemas/student_actions.py))

| Schema | Fields |
|--------|--------|
| `StudentDoubtCreateRequest` | `class_id`, `query_text`, `topic?`, `tried_before: bool = False`, `attempt_text?` |
| `StudentDoubtResponse` | `doubt_id`, `student_id`, `student_name`, `class_id`, `topic`, `query_text`, `tried_before`, `attempt_text?`, `clarification_video_url?`, `status`, `response_text?`, `response_audio_url?`, `messages: list[dict]?`, `created_at`, `teacher_name?`, `subject?` |
| `TeacherDoubtRespondRequest` | `response_text`, `voice_note_file_url?` |
| `StudentDoubtReplyRequest` | `response_text` |

---

## 10. Library

Router prefix: `/teachers/library` — [api/library.py](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/api/library.py)

| Method | Path | Auth | Request Body | Response Model | Line |
|--------|------|------|-------------|----------------|------|
| `GET` | `/teachers/library/assets` | teacher | query: `asset_type`, `grade?`, `subject?`, `search?`, `limit` | ad-hoc (no model) | L15-29 |
| `POST` | `/teachers/library/classes/{class_id}/chapters/{chapter_id}/assets/{asset_id}/adopt` | teacher | `{"source_asset_id": "..."}` (raw dict) | ad-hoc (no model) | L32-51 |

> [!WARNING]
> **Adopt endpoint** accepts a raw `dict` body instead of a Pydantic model. No response model defined.

---

## 11. Media

Router prefix: `/media` — [api/media.py](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/api/media.py)

| Method | Path | Auth | Request Body | Response Model | Line |
|--------|------|------|-------------|----------------|------|
| `GET` | `/media/assets/{asset_id}` | **None** | — | `RedirectResponse` (302) | L33-45 |
| `GET` | `/media/assets/{asset_id}/signed-url` | Bearer (any) | — | `SignedMediaUrlResponse` | L48-63 |

> [!CAUTION]
> **`GET /media/assets/{asset_id}`** has **no auth check** — anyone with an asset ID can access the redirect. The signed-url variant does enforce auth via `_assert_user_can_access_asset`.

### Media Schema ([schemas/media.py](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/schemas/media.py))

| Schema | Fields |
|--------|--------|
| `SignedMediaUrlResponse` | `asset_id`, `signed_url`, `expires_in_minutes` |

---

## 12. Chat with AI

Router prefix: `/chat-with-ai` — [api/chat_ai.py](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/api/chat_ai.py)

| Method | Path | Auth | Request Body | Response Model | Line |
|--------|------|------|-------------|----------------|------|
| `POST` | `/chat-with-ai/chats` | student | `ChatThreadCreateRequest` | `ChatThreadResponse` | L29-35 |
| `GET` | `/chat-with-ai/chats` | student | — | `list[ChatThreadListItem]` | L38-40 |
| `GET` | `/chat-with-ai/chats/{chat_id}` | student | — | `ChatThreadResponse` | L43-49 |
| `GET` | `/chat-with-ai/chats/{chat_id}/messages` | student | — | `list[ChatMessageResponse]` | L52-58 |
| `POST` | `/chat-with-ai/chats/{chat_id}/messages` | student | `ChatSendMessageRequest` | `ChatSendMessageResponse` | L61-68 |
| `DELETE` | `/chat-with-ai/chats/{chat_id}` | student | — | `{"deleted": True}` (ad-hoc) | L71-78 |

### Chat AI Schemas ([schemas/chat_ai.py](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/schemas/chat_ai.py))

| Schema | Fields |
|--------|--------|
| `ChatThreadCreateRequest` | `title?`, `class_id?`, `chapter_id?`, `assignment_id?` |
| `ChatSendMessageRequest` | `content: str` |
| `ChatThreadResponse` | `chat_id`, `student_id`, `class_id?`, `chapter_id?`, `assignment_id?`, `title?`, `status`, `context_json`, `message_count`, `created_at`, `updated_at` |
| `ChatThreadListItem` | `chat_id`, `title?`, `class_id?`, `chapter_id?`, `assignment_id?`, `status`, `message_count`, `last_message_preview?`, `created_at`, `updated_at` |
| `ChatMessageResponse` | `message_id`, `chat_id`, `role`, `content`, `tool_name?`, `tool_input_json?`, `tool_output_json?`, `asset_type?`, `asset_json?`, `created_at` |
| `ChatSendMessageResponse` | `chat: ChatThreadResponse`, `user_message: ChatMessageResponse`, `assistant_message: ChatMessageResponse`, `tool_calls: list[ChatToolCallResponse]`, `generated_assets: list[ChatGeneratedAssetResponse]` |
| `ChatToolCallResponse` | `tool_name`, `status`, `reason?`, `output_json?` |
| `ChatGeneratedAssetResponse` | `asset_type`, `title?`, `description?`, `external_url?`, `payload_json` |

---

## 13. Simulations

Router prefix: `/simulations` — [api/simulation.py](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/api/simulation.py)

| Method | Path | Auth | Request Body | Response Model | Line |
|--------|------|------|-------------|----------------|------|
| `POST` | `/simulations/generate` | Bearer (any) | `GenerateRequest` | `SimulationResponse` | L123-138 |
| `POST` | `/simulations/generate-from-spec` | Bearer (any) | `SpecGenerateRequest` | `SimulationResponse` | L141-158 |
| `POST` | `/simulations/resolve` | Bearer (any) | `ResolveRequest` | `ResolveResponse` | L161-204 |
| `GET` | `/simulations/supported-subjects` | **None** | — | ad-hoc list | L207-209 |
| `GET` | `/simulations/example-prompts` | **None** | — | `{"prompts": [...]}` | L212-214 |
| `GET` | `/simulations/{simulation_id}` | **None** | — | `SimulationResponse` | L217-230 |
| `GET` | `/simulations/{simulation_id}/html` | **None** | — | `HTMLResponse` | L233-253 |
| `POST` | `/simulations/{simulation_id}/assess` | **None** | — | ad-hoc dict | L256-276 |

> [!WARNING]
> The last 4 endpoints (`supported-subjects`, `example-prompts`, `/{simulation_id}`, `/{simulation_id}/html`, `/{simulation_id}/assess`) have **no auth** at all.

### Simulation Schemas (inline in [api/simulation.py](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/api/simulation.py))

All defined **inline** rather than in `schemas/`:

| Schema | Fields | Line |
|--------|--------|------|
| `ResolveRequest` | `topic`, `grade_level?` | L32-34 |
| `ResolveResponse` | `type`, `url?`, `simulation_id?`, `html?`, `title?` | L36-41 |
| `GenerateRequest` | `prompt` | L44-45 |
| `SpecGenerateRequest` | `spec: dict` | L48-49 |
| `SimulationResponse` | `simulation_id`, `status`, `html`, `spec?`, `validation?`, `quality_score`, `assessments`, `error?`, `duration_ms` | L52-61 |

---

## 14. Analytics

Router prefix: `/api/analytics` — [api/analytics.py](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/api/analytics.py)

> [!IMPORTANT]
> This is the **only** router using `/api/` prefix. All others mount directly under `/auth/`, `/teachers/`, `/students/`, etc.

| Method | Path | Auth | Request Body | Response Model | Line |
|--------|------|------|-------------|----------------|------|
| `POST` | `/api/analytics/submit-explanation` | student | `ExplanationSubmitRequest` | ad-hoc dict | L45-147 |
| `GET` | `/api/analytics/student/{student_id}/scores` | teacher\|student | — | ad-hoc list[dict] | L150-243 |
| `GET` | `/api/analytics/class/{class_id}/overview` | teacher | — | ad-hoc list[dict] | L246-334 |
| `POST` | `/api/analytics/class/{class_id}/compute-clusters` | teacher | `ComputeClustersRequest` | ad-hoc list[dict] | L349-405 |
| `GET` | `/api/analytics/class/{class_id}/clusters` | teacher | — | ad-hoc list[dict] | L408-472 |

### Analytics Schemas (inline in [api/analytics.py](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/api/analytics.py))

| Schema | Fields | Line |
|--------|--------|------|
| `ExplanationSubmitRequest` | `chapter_id`, `class_id`, `transcript` | L29-42 |
| `ComputeClustersRequest` | `chapter_id` | L337-346 |

> [!WARNING]
> All 5 analytics endpoints return **ad-hoc dicts** with no Pydantic response models. Business logic is embedded directly in route handlers (especially `submit-explanation` at ~100 lines).

---

## 15. ORM Models

All defined in [core/models.py](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/core/models.py) (557 lines).

| Model | Table | PK | Key Relationships | Line |
|-------|-------|----|--------------------|------|
| `User` | `users` | UUID | → OAuthAccount, Session | L60-111 |
| `OAuthAccount` | `oauth_accounts` | UUID | → User (FK) | L113-151 |
| `OAuthState` | `oauth_states` | UUID | — | L153-182 |
| `Session` | `sessions` | UUID | → User (FK) | L185-223 |
| `School` | `schools` | UUID | → User (created_by) | L225-232 |
| `TeacherSchoolMembership` | `teacher_school_memberships` | UUID | → User, School | L235-241 |
| `ClassRoom` | `classes` | UUID | → School | L244-253 |
| `TeacherClassMembership` | `teacher_class_memberships` | UUID | → User, ClassRoom | L256-263 |
| `StudentClassMembership` | `student_class_memberships` | UUID | → User, ClassRoom | L266-272 |
| `CurriculumPlan` | `curriculum_plans` | UUID | → ClassRoom, User | L275-290 |
| `CurriculumSnapshot` | `curriculum_snapshots` | UUID | → CurriculumPlan, User | L293-307 |
| `Chapter` | `chapters` | UUID | → ClassRoom, CurriculumPlan; has many ChapterTopic | L310-323 |
| `ChapterAsset` | `chapter_assets` | UUID | → Chapter | L326-342 |
| `ChapterTopic` | `chapter_topics` | UUID | → Chapter; has many ChapterTopicAsset | L345-362 |
| `ChapterTopicAsset` | `chapter_topic_assets` | UUID | → ChapterTopic | L365-385 |
| `Assignment` | `assignments` | UUID | → ClassRoom, Chapter, User | L388-401 |
| `AssignmentRecipient` | `assignment_recipients` | UUID | → Assignment, User | L404-410 |
| `ChapterAssetGenerationJob` | `chapter_asset_generation_jobs` | UUID | → Assignment, ChapterAsset | L413-429 |
| `StudentAttempt` | `student_attempts` | UUID | → User, Assignment | L432-444 |
| `StudentDoubt` | `student_doubts` | UUID | → User, ClassRoom | L447-462 |
| `UserQuota` | `user_quotas` | UUID | → User (unique) | L465-473 |
| `SimulationRecord` | `simulation_records` | UUID | — (standalone) | L476-490 |
| `StudentAiChatThread` | `student_ai_chat_threads` | UUID | → User, ClassRoom, Chapter, Assignment | L493-505 |
| `StudentAiChatMessage` | `student_ai_chat_messages` | UUID | → StudentAiChatThread | L508-520 |
| `ConceptScore` | `concept_scores` | UUID | → User, Chapter, ClassRoom | L523-541 |
| `StudentTopicCluster` | `student_topic_clusters` | UUID | → ClassRoom, Chapter | L544-556 |

---

## 16. Pydantic Schemas

### Schema File ↔ Endpoint Cross-Reference

| Schema File | Used By Routes |
|-------------|----------------|
| [schemas/auth.py](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/schemas/auth.py) | `api/auth.py`, `api/teachers.py`, `api/students.py` |
| [schemas/onboarding.py](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/schemas/onboarding.py) | `api/teachers.py`, `api/students.py` |
| [schemas/curriculum.py](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/schemas/curriculum.py) | `api/curriculum.py` |
| [schemas/chapter.py](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/schemas/chapter.py) | `api/chapters.py`, `api/students.py` |
| [schemas/assignment.py](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/schemas/assignment.py) | `api/assignments.py`, `api/student_assignments.py` |
| [schemas/student_actions.py](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/schemas/student_actions.py) | `api/students.py`, `api/teachers.py`, `api/student_assignments.py` |
| [schemas/chat_ai.py](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/schemas/chat_ai.py) | `api/chat_ai.py` |
| [schemas/media.py](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/schemas/media.py) | `api/media.py` |
| [core/schemas.py](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/core/schemas.py) | **UNUSED** — `HealthResponse` never referenced |

### Unused / Orphan Schemas

| Schema | Status |
|--------|--------|
| `HealthResponse` (core/schemas.py:L6-7) | ⚠️ Defined but never imported or used |
| `SubtopicResponse` (schemas/chapter.py:L64-69) | Used in `ChapterResponse.subtopics` but unclear if populated by any service |

---

## 17. Inconsistencies & Flags

### 🔴 Frontend ↔ Backend Route Mismatches

| Frontend Call | Backend Route | Issue |
|---------------|---------------|-------|
| `api.get('/teachers/classes/${cls.class_id}/chapters')` from **StudentExplorePage**, **StudentHomePage**, **StudentAnalytics** | `/teachers/classes/{class_id}/chapters` (requires `require_teacher`) | **Students calling teacher-only endpoint.** Should use `/students/classes/{class_id}/chapters` or the chapters endpoint should relax auth. |
| `api.get('/teachers/classes')` from **StudentAnalytics** (when `isTeacherView`) | `/teachers/classes` (requires `require_teacher`) | Likely intentional (teacher viewing student analytics), but fragile — student tokens will 403. |

### 🟡 Prefix Inconsistency

| Issue | Details |
|-------|---------|
| Analytics router uses `/api/analytics` | All other routers use direct prefixes (`/auth`, `/teachers`, `/students`, `/media`, etc.). The `/api/` prefix is unique to analytics and creates an inconsistent URL namespace. |

### 🟡 Inline Schemas (Not in `schemas/`)

| Schema | Defined In |
|--------|-----------|
| `ChapterBootstrapRequest` | [api/chapters.py:L24-25](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/api/chapters.py#L24-L25) |
| `ResolveRequest`, `ResolveResponse`, `GenerateRequest`, `SpecGenerateRequest`, `SimulationResponse` | [api/simulation.py:L32-61](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/api/simulation.py#L32-L61) |
| `ExplanationSubmitRequest`, `ComputeClustersRequest` | [api/analytics.py:L29-346](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/api/analytics.py#L29-L346) |

### 🟡 Endpoints Returning Ad-Hoc Dicts (No Response Model)

| Endpoint | File:Line |
|----------|-----------|
| `GET /` (health) | api/health.py:L7 |
| `POST /auth/logout` | delegated to service |
| `GET /teachers/classes/{class_id}/chapters/{chapter_id}/analytics` | api/teachers.py:L92-99 |
| `GET /teachers/students/{student_id}/analytics` | api/teachers.py:L102-108 |
| `GET /teachers/classes/{class_id}/students/analytics` | api/teachers.py:L145-253 |
| `DELETE /chat-with-ai/chats/{chat_id}` | api/chat_ai.py:L71-78 |
| `GET /teachers/library/assets` | api/library.py:L15-29 |
| `POST .../adopt` | api/library.py:L32-51 |
| All 5 analytics endpoints | api/analytics.py (entire file) |
| `GET /simulations/supported-subjects` | api/simulation.py:L207-209 |
| `GET /simulations/example-prompts` | api/simulation.py:L212-214 |
| `POST /simulations/{simulation_id}/assess` | api/simulation.py:L256-276 |

### 🟡 Raw `dict` Body Instead of Pydantic Model

| Endpoint | Body Type | File:Line |
|----------|-----------|-----------|
| `POST .../adopt` | `body: dict` | api/library.py:L37 |

### 🟡 Unauthenticated Endpoints

| Endpoint | Expected? |
|----------|-----------|
| `GET /media/assets/{asset_id}` | Likely intentional for public media redirects, but could leak private content |
| `GET /simulations/{simulation_id}` | Probably OK for sharing |
| `GET /simulations/{simulation_id}/html` | Same |
| `GET /simulations/supported-subjects` | Reference data, OK |
| `GET /simulations/example-prompts` | Reference data, OK |
| `POST /simulations/{simulation_id}/assess` | **Suspicious** — POST with no auth |

### 🟡 ORM Models Not Directly Exposed by Any Endpoint

| Model | Notes |
|-------|-------|
| `OAuthAccount` | Used internally by auth service |
| `OAuthState` | Used internally by auth service |
| `Session` | Used internally for refresh tokens |
| `School` | Created in onboarding but no CRUD endpoints |
| `TeacherSchoolMembership` | Join table, no direct API |
| `CurriculumSnapshot` | Written by patch service but no dedicated read endpoint |
| `ChapterAssetGenerationJob` | Exposed indirectly via `AssignmentJobResponse` |
| `AssignmentRecipient` | Exposed indirectly via `AssignmentResponse.recipients` |

---

## 18. Open Questions / Risks

1. **Student pages calling teacher-only chapter endpoints** — `StudentExplorePage`, `StudentHomePage`, and `StudentAnalytics` call `GET /teachers/classes/{class_id}/chapters` which requires `require_teacher`. This will 403 for student tokens. Likely needs to use `/students/classes/{class_id}/chapters` instead, or the endpoint auth should be relaxed to `require_teacher_or_student`.

2. **`GET /media/assets/{asset_id}` is fully unauthenticated** — returns a 302 redirect to a signed URL or external URL. If asset IDs are predictable/guessable, this is a content leakage vector. The sister endpoint (`/signed-url`) does enforce auth.

3. **Analytics prefix inconsistency (`/api/analytics` vs everything else)** — the analytics router is the only one with an `/api/` prefix. This breaks URL conventions and could cause confusion during frontend development or reverse proxy configuration.

4. **~110 lines of inline query logic in `GET /teachers/classes/{class_id}/students/analytics`** (teachers.py L145-253) — no service layer, no response schema, raw ORM queries with N+1 loops. High risk of performance issues and difficult to test.

5. **No `CurriculumSnapshot` read endpoint** — snapshots are written by the curriculum patch service for version history, but there is no API to list or retrieve snapshots. Teachers cannot view curriculum change history.
