# Mootion Backend — Business Logic & Service Layer

> Generated from `backend/app/services/`, `backend/app/simulation_engine/`, `backend/app/api/analytics.py`.
> Covers service flows, external integrations, fragile points, dead code, and workarounds.

---

## Table of Contents
1. [Auth & OAuth](#1-auth--oauth)
2. [Onboarding](#2-onboarding)
3. [Curriculum Bootstrap](#3-curriculum-bootstrap)
4. [Chapter & Asset Management](#4-chapter--asset-management)
5. [Content Generation Pipeline](#5-content-generation-pipeline)
6. [Media Worker & Queue](#6-media-worker--queue)
7. [3D Model Finder](#7-3d-model-finder)
8. [Doubt Resolution Flow](#8-doubt-resolution-flow)
9. [Student Grading (Attempt Scoring)](#9-student-grading-attempt-scoring)
10. [Student Playground](#10-student-playground)
11. [Chat with AI (Agentic Tutor)](#11-chat-with-ai-agentic-tutor)
12. [RAG Service](#12-rag-service)
13. [Library (Content Reuse)](#13-library-content-reuse)
14. [Analytics & Scoring](#14-analytics--scoring)
15. [Student Clustering](#15-student-clustering)
16. [Simulation Engine](#16-simulation-engine)
17. [Object Storage (Cloudflare R2)](#17-object-storage-cloudflare-r2)
18. [Fragile Points & Workarounds Summary](#18-fragile-points--workarounds-summary)
19. [Open Questions / Risks](#19-open-questions--risks)

---

## 1. Auth & OAuth

**Files:** [auth_service.py](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/services/auth_service.py), [oauth/google.py](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/services/oauth/google.py), [core/security.py](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/core/security.py)

### Flow
1. **Register** → hash password → create `User` row → issue JWT access + refresh tokens → create `Session` row with refresh hash (7-day TTL).
2. **Login** → lookup by `login_id` → verify password → issue tokens.
3. **Refresh** → lookup `Session` by hash → check expiry → revoke old session → issue new tokens (rotation).
4. **Logout** → revoke session by refresh hash.
5. **Google OAuth** → `build_google_authorization_url` creates `OAuthState` (10-min TTL, stores `requested_role`) → redirect → `complete_google_oauth` exchanges code for token → fetches userinfo → links/creates `OAuthAccount` + `User`.

### External Systems
- **Google OAuth2** (accounts.google.com, oauth2.googleapis.com, openidconnect.googleapis.com)

### Fragile Points
- ⚠️ **Insecure default JWT secret**: `jwt_secret` defaults to `"change-me"` ([config.py:L16](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/core/config.py#L16)). No runtime check forces a real secret in production.
- ⚠️ **OAuth state cleanup**: `OAuthState` rows are never cleaned up after expiry — only the specific consumed row is deleted. Stale rows accumulate.
- ⚠️ **OAuth creates random password**: When creating a new user via Google OAuth, a random password is generated with `token_urlsafe(24)` ([google.py:L102](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/services/oauth/google.py#L102)). The user can never log in with password auth unless they reset it — but no reset flow exists.

---

## 2. Onboarding

**File:** [onboarding_service.py](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/services/onboarding_service.py)

### Flow
1. **Teacher Preferences** → ensures a default `School` exists → creates `TeacherSchoolMembership` if missing → saves `preferred_language`.
2. **Create Class** → validates `subject ∈ ALLOWED_SUBJECTS` → creates `ClassRoom` + `TeacherClassMembership`.
3. **Complete Onboarding** → sets `user.onboarding_completed = True`. Accepts `load_ncert` flag but **does not act on it** — just echoes it back.
4. **Student Join** → lookup `ClassRoom` by `class_code` → creates `StudentClassMembership`.
5. **Student Language** → saves `preferred_language` → marks `onboarding_completed = True`.

### Fragile Points
- ⚠️ **`ALLOWED_SUBJECTS` is hardcoded** to `{"Physics", "Mathematics", "Chemistry", "Biology", "Computer Science", "Science"}` ([L38](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/services/onboarding_service.py#L38)). No way to extend from the frontend or admin panel.
- ⚠️ **`load_ncert` flag is accepted but ignored** — `complete_teacher_onboarding` does not trigger any curriculum bootstrap ([L124-134](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/services/onboarding_service.py#L124-L134)).
- ⚠️ **No "default school" cleanup**: `get_or_create_default_school` is called in both preference setup and class creation, creating redundant membership checks.

---

## 3. Curriculum Bootstrap

**Files:** [curriculum_service.py](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/services/curriculum_service.py), [curriculum_presets.py](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/services/curriculum_presets.py)

### Triggers
- `POST /teachers/classes/{class_id}/curriculum/bootstrap` → single NCERT curriculum
- `POST /teachers/classes/{class_id}/curriculum/bootstrap-bulk` → **destructive** full rebuild

### Flow — `bootstrap_ncert_curriculum`
1. Lookup `ClassRoom` to determine `grade` + `subject`.
2. Call `build_ncert_curriculum(title, grade, subject)`:
   - Loads `syllabus.json` (146KB, cached with `@lru_cache`).
   - Matches grade by integer, subject via `_normalize_subject` with alias map + fuzzy fallback.
   - **Grade 11-12 Science special-casing**: For `Physics`, `Chemistry`, `Biology` in grades 11/12, filters chapters by prefix matching (e.g., `"Physics Chapter 1: ..."`) and strips the subject prefix with regex ([curriculum_presets.py:L128-141](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/services/curriculum_presets.py#L128-L141)).
   - Builds a curriculum tree: root → chapter nodes → topic nodes.
   - Flattens into graph representation (nodes + "contains" edges).
3. Creates `CurriculumPlan` + `CurriculumSnapshot`.

### Flow — `bootstrap_ncert_curriculum_bulk`
1. **Deletes ALL existing** `CurriculumPlan` and `Chapter` rows for the class ([L427-437](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/services/curriculum_service.py#L427-L437)).
2. Creates curriculum + snapshot.
3. Bulk-creates `Chapter`, `ChapterAsset` (8 placeholder types), `ChapterTopic`, `ChapterTopicAsset` (3 placeholder types per topic).
4. Uses 3 sequential `db.commit()` calls to satisfy FK ordering.

### Curriculum Patching
- Supports `add_node`, `update_node`, `delete_node`, `move_node` operations on the curriculum tree.
- **Optimistic concurrency**: checks `expected_version` against current `curriculum.version`, bumps version on each patch.
- Snapshots every patch operation for version history.
- **`move_node` restriction**: can only move within the same parent — no cross-parent moves ([L231](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/services/curriculum_service.py#L231)).

### Fragile Points
- 🔴 **`bootstrap-bulk` is destructive with no confirmation** — deletes all existing chapters/curricula for the class, including any generated assets. The frontend calls this as a fallback when no curriculum exists ([TeacherClassViewPage.tsx:L154](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/frontend/src/pages/TeacherClassViewPage.tsx#L154)).
- ⚠️ **Grade 11/12 subject prefix stripping** relies on exact string matching of chapter names starting with `"Physics"`, `"Chemistry"`, or `"Biology"` ([curriculum_presets.py:L128-141](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/services/curriculum_presets.py#L128-L141)). If `syllabus.json` formatting changes, all grade 11-12 chapters will appear with dirty prefixes.
- ⚠️ **`_normalize_subject` maps `Physics/Chemistry/Biology` → `"science"`** for all grades, even though syllabus.json has separate entries for 11/12. The `_resolve_subject_entry` function compensates with fuzzy matching.
- ⚠️ **AI curriculum generation is declared but blocked**: `create_class_curriculum` raises `501 Not Implemented` for any `source_type` other than `"manual"` ([L263-264](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/services/curriculum_service.py#L263-L264)).

### External Systems
- None (static JSON file only).

---

## 4. Chapter & Asset Management

**File:** [chapter_service.py](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/services/chapter_service.py)

### Placeholder Asset Slots
Each chapter gets **8 placeholder assets** ([L56-146](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/services/chapter_service.py#L56-L146)):

| Asset Type | Provider | Integration Target |
|-----------|----------|--------------------|
| `concept_video` | manim | manim_generator |
| `simulation` | phet | phet_embed |
| `three_d_model` | model_finder | model_finder |
| `quiz` | quiz_generator | quiz_builder |
| `explain_it` | mootion_ai | voice_activity |
| `predict_it` | mootion_ai | voice_activity |
| `spot_it` | mootion_ai | voice_activity |
| `connect_it` | mootion_ai | voice_activity |

Each topic gets **3 placeholder assets** (`concept_video`, `simulation`, `three_d_model`) ([L149-184](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/services/chapter_service.py#L149-L184)).

### Chapter Bootstrap from Curriculum
- `bootstrap_chapters_from_curriculum`: iterates curriculum tree's top-level children, creates `Chapter` + `ChapterTopic` rows for new nodes, creates placeholder assets for each topic.
- Skips existing chapters/topics by `source_node_id`.

### Direct Asset Generation
- Teacher triggers `generate_chapter_asset` or `generate_topic_asset` → synchronous generation in the request handler.
- Only types in `DIRECT_GENERATION_ASSET_TYPES = {"concept_video", "simulation", "three_d_model"}` can be generated.
- Generation time estimates: `concept_video`: 180s, `simulation`: 75s, `three_d_model`: 45s.

### Fragile Points
- ⚠️ **Synchronous generation blocks the HTTP request** for up to 300s (Manim timeout). No async task pattern for the direct-generation path.
- ⚠️ **Duplicate `_persist_simulation_result`**: defined identically in both `chapter_service.py` ([L310-328](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/services/chapter_service.py#L310-L328)) and `chat_ai_service.py` ([L427-445](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/services/chat_ai_service.py#L427-L445)).
- ⚠️ **Quiz generation prompt hardcodes "science teacher"** in `assignment_service._run_quiz_generation` ([L453-464](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/services/assignment_service.py#L453-L464)), making it unsuitable for Mathematics or Computer Science quizzes.

---

## 5. Content Generation Pipeline

**File:** [assignment_service.py](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/services/assignment_service.py)

### Trigger
- Teacher creates assignment → `create_teacher_assignment` → `_create_generation_jobs`.

### Step-by-Step
1. Verify teacher access + chapter exists.
2. Auto-assign all students in class as `AssignmentRecipient`.
3. Find chapter assets matching `ASSIGNMENT_TYPE_TO_ASSET_TYPE` mapping.
4. For assets with `provider ∈ {"manim", "model_finder", "quiz_generator", "simulation"}`, create `ChapterAssetGenerationJob` rows (status: `queued`).
5. Enqueue each job ID to Redis via `media_queue.enqueue_media_generation_job`.
6. Derive assignment status from aggregate job statuses.

### Generation Dispatch (`process_generation_job`)
- **Manim** (`_run_manim_generation`): HTTP POST to `settings.manim_service_url` with params `topic`, `level=school`, `persona=teacher`, `face_enabled=False`, `rag_context`. Timeout: 300s. Returns `video_id`.
- **Model Finder** (`_run_model_finder_generation`): calls `find_model(query)` → Sketchfab API search + LLM-ranked thumbnail evaluation.
- **Quiz** (`_run_quiz_generation`): sends prompt to Azure OpenAI, asks for 3 MCQs as JSON. Parses with markdown-fence-stripping.
- **Simulation** (`_run_simulation_generation`): instantiates `SimulationPipeline().run(prompt)`. Returns `simulation_id` + HTML.

### Post-Generation
- **Manim**: downloads video from Manim service → uploads to Cloudflare R2 → updates `ChapterAsset` with `storage_bucket`, `storage_key`, `external_url`.
- **Model Finder**: sets `asset.external_url` to Sketchfab embed/viewer URL.
- **Quiz**: stores questions array in `asset.payload_json.quiz`.
- **Simulation**: stores `simulation_id`, constructs `external_url` pointing to backend's `/simulations/{id}/html` route.

### External Systems
- **Manim Service** (self-hosted, `MANIM_SERVICE_URL`)
- **Azure OpenAI** (quiz generation, grading)
- **Sketchfab API** (3D model search)
- **Cloudflare R2** / MinIO (video storage)
- **Redis** (job queue)

---

## 6. Media Worker & Queue

**Files:** [media_worker.py](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/services/media_worker.py), [media_queue.py](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/services/media_queue.py), [media_service.py](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/services/media_service.py)

### Architecture
- **Queue**: Redis list (`mootion-media:queue`). Jobs enqueued via `LPUSH`, consumed via `BRPOP`.
- **Deduplication**: Redis `SET NX` with key `mootion-media:enqueued:{job_id}`, 24-hour TTL.
- **Stale recovery**: `enqueue_pending_media_jobs` re-queues jobs stuck in `processing` for > `media_job_stale_timeout_minutes` (default: 120 min).

### Worker Loop
1. `BRPOP` with configurable timeout (default 1s).
2. Call `process_media_generation_job(job_id)`.
3. On completion, refresh parent `Assignment` status.
4. On failure, the DB job row records the error; the worker stays alive.
5. `acknowledge_media_generation_job` deletes the dedup key.

### Startup Checks
- Pings Redis.
- Tests R2 bucket existence (creates if missing).
- Performs test upload of `test_worker_startup.txt`.

### Fragile Points
- ⚠️ **Single-process, single-threaded worker** — one stuck Manim call (300s timeout) blocks all other jobs.
- ⚠️ **No retry mechanism** — failed jobs are marked `failed` and never retried. `attempt_count` is incremented but no max-retry or backoff logic exists.
- ⚠️ **Enqueue failure is silently swallowed** during assignment creation ([assignment_service.py:L149-153](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/services/assignment_service.py#L149-L153)): `except Exception: pass`.

---

## 7. 3D Model Finder

**File:** [model_finder.py](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/services/model_finder.py)

### Flow
1. Search Sketchfab API (`q={query}`, `sort_by=-relevance`).
2. Take top 5 results.
3. For each: download 4th thumbnail → encode as base64 data URI → send to Azure OpenAI with 185-line educational scoring prompt.
4. Select highest-scoring model.

### External Systems
- **Sketchfab API** (`settings.sketchfab_api_url`)
- **Azure OpenAI** (vision model for thumbnail ranking)

### Also Exports
- `query_llm(prompt, image_paths?)` — general-purpose Azure OpenAI wrapper used by grading, quiz generation, doubt topic identification, etc. Uses `OpenAI` client (not `AzureOpenAI`), configured with `base_url = settings.azure_openai_endpoint` ([L246](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/services/model_finder.py#L246)).

### Fragile Points
- ⚠️ **Two different OpenAI client wrappers**: `model_finder.query_llm` uses the `openai.OpenAI` client with `base_url`, while `chat_ai_service._get_client` and `rag_service._get_azure_client` use `openai.AzureOpenAI` with `azure_endpoint`. These have different URL normalization and API versioning behavior.
- ⚠️ **Thumbnail downloads save to a temp directory** but the code in `download_thumbnail` defaults to `save_dir="thumbnails"` ([L265](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/services/model_finder.py#L265)) — though the caller overrides with `tempfile.TemporaryDirectory()`, a direct call would write to the CWD.

---

## 8. Doubt Resolution Flow

**File:** [student_actions_service.py](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/services/student_actions_service.py)

### Product Design Intent
Per the product model: students should attempt understanding first, then raise doubts. The `tried_before` field and `attempt_text` field capture this intent.

### Flow
1. **Student submits doubt** (`submit_student_doubt`):
   - Verifies class membership.
   - If no `topic` provided, calls `query_llm` to identify a 2-4 word topic name.
   - Calls `_generate_clarification_video` → **Manim service** with 10s timeout. Falls back to hardcoded w3schools bunny video URL.
   - Creates `StudentDoubt` with status `"pending"`, initial message in `messages` JSON array.
2. **Teacher responds** (`respond_to_doubt`): sets status to `"responded"`, appends teacher message to `messages`, stores `response_text` + optional `voice_note_file_url`.
3. **Student replies** (`student_reply_to_doubt`): appends reply, resets status to `"pending"`.
4. **Resolve** (by student or teacher): sets status to `"resolved"`.
5. **Reopen** (student only): sets status back to `"pending"`.

### Teacher Name Formatting Workaround
- `_to_response` ([L209-247](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/services/student_actions_service.py#L209-L247)) applies **hardcoded name prefix heuristics**:
  - If name contains `"priya"` or `"mehta"` → `"Mrs. "` prefix.
  - If name contains `"sharma"` or `"arjun"` → `"Mr. "` prefix.
  - Otherwise → `"Mr. "` prefix.
- This is gender-assumption logic based on Indian name patterns.

### Fragile Points
- 🔴 **`tried_before` is not enforced** — the flag is stored but never checked. A student can submit doubts without any prior attempt, contradicting the stated "gated doubt flow" design.
- 🔴 **Clarification video fallback** is a hardcoded w3schools test video URL (`https://www.w3schools.com/html/mov_bbb.mp4`) ([L203, L206](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/services/student_actions_service.py#L203-L206)). Comment says "Return a high quality fallback explainer video" but it's Big Buck Bunny.
- ⚠️ **Doubt video has 10s Manim timeout** vs 300s for normal generation ([L199](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/services/student_actions_service.py#L199)). Will almost always time out and fall back to the bunny video.
- ⚠️ **Teacher name gender heuristic** ([L222-228](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/services/student_actions_service.py#L222-L228)) is a hackathon workaround. Will misattribute gender based on substring matching of names.
- ⚠️ **Messages use "Just now" as timestamp** instead of actual datetime ([L292, L398, L429](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/services/student_actions_service.py#L292)).

---

## 9. Student Grading (Attempt Scoring)

**File:** [student_actions_service.py:L92-182](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/services/student_actions_service.py#L92-L182)

### Trigger
- `POST /students/classes/{class_id}/assignments/{assignment_id}/submit`

### Flow
1. Verify student is a recipient of the assignment.
2. Lookup chapter title (defaults to `"Science Topic"` if not found).
3. Build LLM grading prompt — scores on 3 axes (0-3 scale): Understanding, Reasoning, Expression.
4. Call `query_llm` (Azure OpenAI) → parse JSON response.
5. On parse failure: **fallback to scores (2, 2, 2)** with error message as feedback ([L159](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/services/student_actions_service.py#L159)).
6. Save `StudentAttempt` row.

### Fragile Points
- ⚠️ **LLM parse failure gives a default passing score** (2/3 on each axis) rather than failing the attempt or returning 0. Students get credit for garbled input.
- ⚠️ **Grading prompt hardcodes "science teacher"** and "scientific facts" ([L116-117](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/services/student_actions_service.py#L116-L117)). Not appropriate for Mathematics.
- ⚠️ **No rate limiting** on submissions. Students can resubmit indefinitely.

---

## 10. Student Playground

**File:** [student_actions_service.py:L465-552](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/services/student_actions_service.py#L465-L552)

### Trigger
- `POST /students/playground/generate`

### Flow by `asset_type`
1. **`three_d_model`** / `model` → calls `find_model(topic)` via Sketchfab + LLM ranking.
2. **`simulation`** → calls `_get_phet_simulation_url(topic)` — keyword-matching to **4 hardcoded PhET URLs**.
3. **Anything else** (treated as video) → consumes **both** doubt quota and playground quota → calls `_generate_clarification_video`.

### Quotas
- Daily doubt videos: **5/day** ([L70](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/services/student_actions_service.py#L70)).
- Weekly playground items: **10/week** ([L81](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/services/student_actions_service.py#L81)).
- Quotas auto-reset based on `last_doubt_reset.date()` and 7-day interval.

### Fragile Points
- 🔴 **PhET simulation selection is fully hardcoded** ([L467-477](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/services/student_actions_service.py#L467-L477)): only 4 simulations exist (gravity, circuits, waves, forces). Anything else → defaults to Ohm's Law.
- ⚠️ **Video generation double-charges quota**: playground video uses both `check_and_use_playground_quota` AND `check_and_use_doubt_quota` ([L486, L522](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/services/student_actions_service.py#L486-L522)).

---

## 11. Chat with AI (Agentic Tutor)

**File:** [chat_ai_service.py](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/services/chat_ai_service.py) (867 lines)

### Architecture
Multi-step agentic pipeline per message:

1. **Context Resolution** → resolves `class_id`, `chapter_id`, `assignment_id` → builds context dict with grade, subject, chapter assets, assignment details.
2. **Tool Planning** (`_plan_tool_calls`) → uses Azure OpenAI (or heuristic fallback) to decide which tools to invoke. Supports slash commands: `/video`, `/universe`, `/quiz`, `/simulation`.
3. **Tool Execution** → runs selected tools sequentially, collects results.
4. **Answer Generation** → Azure OpenAI generates final answer incorporating tool results + RAG context.
5. **Persistence** → saves user message, tool messages, assistant message to `StudentAiChatMessage` table.

### Tool Planning Details
- Uses `_complexity_score` (word count, question words, conjunction density, chapter title mention) to decide when video is warranted.
- Keyword matching for explicit tool requests (e.g., `"show me"` → video, `"3d"` → model).
- Azure OpenAI planner call with structured JSON output → post-filtering to prevent false positives.
- **If Azure OpenAI is not configured**: falls back to heuristic keyword matching only.

### Tool Execution
- `video`: Manim service → download from Manim → upload to R2 → return presigned URL.
- `model`: Sketchfab search + LLM ranking.
- `quiz`: LLM-generated 3 MCQs (same as assignment flow).
- `simulation`: full `SimulationPipeline.run()` → persist to `SimulationRecord` → return `/simulations/{id}/html` URL.

### External Systems
- **Azure OpenAI** (planner + final answer + tool calls)
- **Manim Service** (video generation)
- **Cloudflare R2** (video upload)
- **Sketchfab** (3D models)
- **ChromaDB** (RAG context)

### Fragile Points
- ⚠️ **Entire request blocks during tool execution** — a video + simulation combo can take 300s+ synchronously.
- ⚠️ **In-memory simulation cache** in `SimulationOrchestrator` ([pipeline.py:L112](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/simulation_engine/pipeline.py#L112)) — lost on process restart, no LRU eviction.
- ⚠️ **`_generate_final_answer` without Azure config** returns a generic concatenation of tool summaries + truncated user message ([L617-633](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/services/chat_ai_service.py#L617-L633)). Not useful as a tutor response.

---

## 12. RAG Service

**File:** [rag_service.py](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/services/rag_service.py)

### Flow
1. Determine ChromaDB collection name from `grade` + `subject` (e.g., `class_9_science`, `class_11_physics`).
2. Apply NCERT subject normalization rules:
   - Grades 6-10: Physics/Chemistry/Biology all map to `"science"` (combined textbook).
   - Grades 11-12: separate collections.
3. Try primary collection → fallback to `science` → `biology` → `chemistry` → `physics`.
4. Generate embedding via Azure OpenAI `text-embedding-3-small`.
5. Query ChromaDB with embedding, retrieve top 5 results with metadata (chapter title, page number).

### Integration Points
Used by: `assignment_service._get_rag_context_for_asset`, `chat_ai_service._generate_final_answer`, `chat_ai_service._run_video_tool`, `student_actions_service._generate_clarification_video`.

### External Systems
- **ChromaDB** (persistent, local at `backend/chroma_db/`)
- **Azure OpenAI** (embedding generation)

### Fragile Points
- ⚠️ **Embedding model is hardcoded** to `"text-embedding-3-small"` ([L152](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/services/rag_service.py#L152)) — if the ChromaDB was populated with a different embedding model, results will be meaningless.
- ⚠️ **Silently returns empty string on any failure** — no logging or error propagation to caller for embedding/query failures.
- ⚠️ **`_get_rag_context_for_asset`** in `assignment_service.py` creates its own `SessionLocal()` rather than using the caller's DB session ([L359-374](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/services/assignment_service.py#L359-L374)) — can cause session leaks if an exception occurs between `SessionLocal()` and `finally`.

---

## 13. Library (Content Reuse)

**File:** [library_service.py](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/services/library_service.py)

### Flow
1. **List assets**: queries all ready `ChapterAsset` rows across ALL classrooms → joins with `Chapter` + `ClassRoom` → filters in-memory by grade (digit comparison), subject (substring), and search text.
2. **Adopt asset**: copies `external_url`, `storage_bucket`, `storage_key` from a source asset to a target asset slot → marks target as `"ready"`. No generation cost.

### Fragile Points
- ⚠️ **Filtering is done in Python** after fetching all rows ([L76-98](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/services/library_service.py#L76-L98)). Grade/subject/search filters are applied post-query. Will not scale with large datasets.
- ⚠️ **No ownership check**: any teacher can adopt any ready asset from any other teacher's class. This may be intentional for a content library but is not documented.

---

## 14. Analytics & Scoring

**Files:** [student_actions_service.py:L558-768](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/services/student_actions_service.py#L558-L768), [api/analytics.py](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/api/analytics.py)

### Two Separate Analytics Systems
There are **two independent analytics systems** in the codebase:

#### System A: `StudentAttempt`-based (student_actions_service)
- **Class overview** (`get_class_analytics_overview`): aggregates `StudentAttempt` scores (0-3 scale for understanding/reasoning/expression). Extracts misconceptions by keyword-searching AI feedback for `"misconception"` or `"incorrectly"`.
- **Chapter drill** (`get_chapter_analytics_drill`): score distribution + per-student breakdown. Returns **hardcoded mock misconceptions** ([L702-706](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/services/student_actions_service.py#L702-L706)).
- **Student drill** (`get_student_analytics_drill`): score timeline + language ratio. Returns **hardcoded mock values**: `streak: 5`, `prediction_accuracy: 75`, hardcoded misconceptions list ([L759-764](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/services/student_actions_service.py#L759-L764)).

#### System B: `ConceptScore`-based (api/analytics.py)
- **Submit explanation** (`submit_explanation`): sends student transcript to Azure OpenAI for clarity/accuracy/depth scoring (0-10 scale). Creates `ConceptScore` row.
- **Student scores** (`get_student_scores`): groups by chapter, computes trend (improving/declining/stable).
- **Class overview** (`get_class_overview`): per-chapter avg scores + weakest students.
- **Compute clusters** + **Get clusters**: delegates to `clustering_service`.

### Fragile Points
- 🔴 **Two parallel analytics systems** with different score scales (0-3 vs 0-10), different models (`StudentAttempt` vs `ConceptScore`), and different triggering endpoints. These are not integrated.
- 🔴 **Hardcoded mock data in student/chapter analytics drills** — `streak: 5`, `prediction_accuracy: 75`, and fixed misconception strings ([L759-764](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/services/student_actions_service.py#L759-L764), [L702-706](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/services/student_actions_service.py#L702-L706)).
- ⚠️ **Misconception extraction** is a naive keyword search on `ai_feedback` text ([L622-628](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/services/student_actions_service.py#L622-L628)).
- ⚠️ **`misconception_count` hardcoded to `2`** when no misconceptions found ([L645](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/services/student_actions_service.py#L645)): `len(misconceptions) or 2`.
- ⚠️ **N+1 queries** in analytics drills — `User` lookup inside loops for student names.

---

## 15. Student Clustering

**File:** [clustering_service.py](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/services/clustering_service.py)

### Flow
1. Fetch all `ConceptScore` rows for class + chapter.
2. Group by student, keep latest attempt per student.
3. If < 3 students have scores → return None.
4. Run **KMeans (k=3)** on 1D overall_score vector.
5. Map clusters to labels: lowest centroid → `"struggling"`, middle → `"average"`, highest → `"strong"`.
6. Delete old `StudentTopicCluster` rows → insert new ones.

### External Systems
- **scikit-learn** (KMeans)

### Fragile Points
- ⚠️ **Fixed k=3** regardless of actual data distribution. With exactly 3 students, every cluster has 1 student.
- ⚠️ **1D clustering** on a single scalar (`overall_score`). Simple threshold binning would be more interpretable and deterministic.

---

## 16. Simulation Engine

**Files:** [simulation_engine/pipeline.py](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/simulation_engine/pipeline.py), and layers: `prompt_understanding_layer.py`, `simulation_planning_layer.py`, `simulation_builder.py`, `scientific_validation.py`, `ui_quality_layer.py`, `assessment_layer.py`

### Pipeline Phases
1. **Understanding Prompt** → `PromptUnderstandingLayer.understand(prompt)` → `SimulationIntent`
2. **Planning Simulation** → `SimulationPlanningLayer.plan(intent)` → `SimulationSpecification`
3. **Building Simulation** → `SimulationBuilder.build(spec)` → HTML string + JS validation
4. **Validating Science** → `ScientificValidator.validate(spec)` → `ValidationResult` (fails if `score < 0.5`)
5. **Checking Quality** → `UIQualityChecker.check(html)` → quality score
6. **Generating Assessments** → `AssessmentGenerator.generate(spec)` → assessment prompts

### Orchestrator
- `SimulationOrchestrator` wraps the pipeline + adds an **in-memory `dict` cache** keyed by `simulation_id`.
- `generate_from_spec` skips phases 1-2, starts directly at building.

### Integration Points
Used by: `chapter_service.generate_chapter_asset`, `chapter_service.generate_topic_asset`, `assignment_service._run_simulation_generation`, `chat_ai_service._run_simulation_tool`, `api/simulation.py` routes.

---

## 17. Object Storage (Cloudflare R2)

**File:** [core/storage.py](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/core/storage.py)

### Architecture
- Wraps **boto3 S3 client** configured for Cloudflare R2 (or MinIO for local dev).
- `@lru_cache(maxsize=1)` singleton.
- `presigned_media_url`: if `OBJECT_STORAGE_PUBLIC_URL` is set, returns simple public URL path. Otherwise generates presigned S3 GET URL.

### Config
- Supports 3 sets of env vars: `OBJECT_STORAGE_*` > `R2_*` > `MINIO_*` (fallback chain in [config.py:L37-58](file:///Users/rachitgoyal/Desktop/hackathons/2026/13_wadhwani/mootion-wadhwani-aiiii/backend/app/core/config.py#L37-L58)).
- Default bucket: `mootion-media`.
- Default signed URL expiry: 15 minutes.

---

## 18. Fragile Points & Workarounds Summary

| Severity | Location | Description |
|----------|----------|-------------|
| 🔴 | `student_actions_service:L203,L206` | Clarification video falls back to Big Buck Bunny (w3schools test video) |
| 🔴 | `student_actions_service:L702-706,L759-764` | Analytics drills return hardcoded mock misconceptions, streak=5, prediction_accuracy=75 |
| 🔴 | `curriculum_service:L427-437` | `bootstrap-bulk` destructively deletes all chapters without confirmation |
| 🔴 | `student_actions_service:L250-310` | `tried_before` flag is stored but never enforced — gated doubt flow not implemented |
| 🔴 | `api/analytics.py` + `student_actions_service` | Two parallel analytics systems with different score scales (0-3 vs 0-10), not integrated |
| ⚠️ | `student_actions_service:L222-228` | Teacher name prefix heuristic based on hardcoded Indian name patterns |
| ⚠️ | `student_actions_service:L199` | Doubt clarification video has 10s timeout (vs 300s normal) — will almost always fall back |
| ⚠️ | `student_actions_service:L159` | LLM grading parse failure gives default 2/2/2 scores instead of failing |
| ⚠️ | `student_actions_service:L645` | `misconception_count` defaults to 2 instead of 0 via `or` operator |
| ⚠️ | `student_actions_service:L292,L398,L429` | Doubt messages use "Just now" string instead of actual timestamps |
| ⚠️ | `student_actions_service:L467-477` | PhET simulation selection: only 4 hardcoded URLs with keyword matching |
| ⚠️ | `onboarding_service:L124-134` | `load_ncert` flag accepted but never acted upon |
| ⚠️ | `curriculum_presets:L128-141` | Grade 11/12 chapter prefix stripping depends on exact syllabus.json formatting |
| ⚠️ | `curriculum_service:L263-264` | AI curriculum generation blocked with 501 for all non-manual source types |
| ⚠️ | `assignment_service:L149-153` | Redis enqueue failure silently swallowed |
| ⚠️ | `assignment_service:L453-464` | Quiz prompt hardcodes "science teacher" |
| ⚠️ | `config:L16` | JWT secret defaults to `"change-me"` with no production enforcement |
| ⚠️ | `model_finder` vs `chat_ai_service` | Two different OpenAI client wrappers with different URL normalization |
| ⚠️ | `chapter_service:L310-328` + `chat_ai_service:L427-445` | `_persist_simulation_result` duplicated identically |

---

## 19. Open Questions / Risks

1. **Two analytics systems compete for the same conceptual space** — `StudentAttempt` (0-3, understanding/reasoning/expression) and `ConceptScore` (0-10, clarity/accuracy/depth) score the same kind of student work but with different scales, models, and endpoints. Neither system references the other. Which one is canonical?

2. **`tried_before` gating is unenforced** — the product design calls for students to attempt an explanation before raising a doubt, but the backend accepts doubts regardless. This defeats the pedagogical intent of the "attempt-first" model and should either be enforced or the field removed.

3. **Synchronous AI generation can block requests for 5+ minutes** — Manim videos, simulations, and the chat-AI pipeline all run synchronously in the request handler. A single slow tool call blocks the entire response. The async media worker pattern exists for assignment-based generation but is not used for direct generation or chat.

4. **Hardcoded mock data shipped as "real" analytics** — `streak: 5`, `prediction_accuracy: 75`, and fixed misconception strings are returned from production endpoints as real data, with no indicator to the frontend that these are mocks. This will mislead teachers about actual student performance.

5. **Clarification video is functionally broken** — the 10-second Manim timeout virtually guarantees the fallback Big Buck Bunny video is served. This means every student doubt gets a meaningless test video instead of an AI-generated explanation, undermining a core feature.
