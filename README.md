<p align="center">
  <br/>
  <!-- REPLACE WITH: <img src="docs/assets/mootion-banner.png" width="100%" alt="Mootion Banner"> -->
  <br/>
</p>

<h1 align="center">
  <img width="1918" height="695" alt="image" src="https://github.com/user-attachments/assets/a57b42a6-582b-436d-9039-62f7e162a286" />

  &nbsp;Mootion
</h1>

<p align="center">
  <b>Turning student interactions into actionable understanding signals for teachers.</b>
</p>

<p align="center">
  Built for <b>Wadhwani AI SahAI Hackathon 2026</b> &nbsp;·&nbsp; Top 30 Finalist &nbsp;·&nbsp; by <b>Team Evolve AI</b>
</p>

<p align="center">
  <a href="#-the-problem">Problem</a> &nbsp;·&nbsp;
  <a href="#-what-mootion-is">What It Is</a> &nbsp;·&nbsp;
  <a href="#-the-diagnostic-loop">The Loop</a> &nbsp;·&nbsp;
  <a href="#-engines">Engines</a> &nbsp;·&nbsp;
  <a href="#-analytics">Analytics</a> &nbsp;·&nbsp;
  <a href="#-architecture">Architecture</a> &nbsp;·&nbsp;
  <a href="#-getting-started">Getting Started</a> &nbsp;·&nbsp;
  <a href="#-team">Team</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=white" alt="React 19">
  <img src="https://img.shields.io/badge/FastAPI-latest-009688?logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/TypeScript-5.8-3178C6?logo=typescript&logoColor=white" alt="TypeScript">
  <img src="https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white" alt="Python 3.11">
  <img src="https://img.shields.io/badge/Gemini_Live-API-8E75B2?logo=google&logoColor=white" alt="Gemini Live">
  <img src="https://img.shields.io/badge/Manim-Animation-FF6F00?logo=python&logoColor=white" alt="Manim">
  <img src="https://img.shields.io/badge/scikit--learn-KMeans-F7931E?logo=scikitlearn&logoColor=white" alt="scikit-learn">
  <img src="https://img.shields.io/badge/Redis-Worker-DC382D?logo=redis&logoColor=white" alt="Redis">
  <img src="https://img.shields.io/badge/Sketchfab-3D_Models-1CAAD9?logoColor=white" alt="Sketchfab">
  <img src="https://img.shields.io/badge/Tailwind-v4-06B6D4?logo=tailwindcss&logoColor=white" alt="Tailwind v4">
</p>

<br/>

---


## 🎯 The Problem

India solved enrollment. It hasn't solved learning.

- **98%** of children aged 6–14 are enrolled in school
- **50%** of Grade 5 students cannot read a simple Grade 2 text
- **37%** average score in Grade 9 mathematics nationwide
- **1.04 lakh** single-teacher schools operate across India daily
- In a standard 45-minute class with 45 students, a teacher has **less than 60 seconds per student**

The result: rote memorization is promoted because **true understanding is too expensive to measure.**

Teachers can track attendance. They can record marks. They can count homework submissions.

**They cannot measure whether a student understands.**

That signal has never existed — at classroom scale, in real time, without adding work to an already overloaded teacher.

Mootion creates it.

<br/>

---

<br/>

## 💡 What Mootion Is

> *"The only way to know if a student understands something is to make them explain it."*

Mootion is not a chatbot. Not a content library. Not a simulation platform.

It is a **conceptual understanding signal engine** — built around the Feynman Technique. Every student explains every concept to Mootion, a simulated curious 10-year-old AI child who asks naive but scientifically challenging questions. Every explanation is scored. Every score becomes data for the teacher.

**One platform. One signal. Built for Meera.**

> Meera is a Grade 8–10 Science teacher managing 45 students per class. She can meaningfully probe 4 students in a 45-minute period. 41 remain conceptually invisible every single day. Mootion makes all 45 visible — by morning.

Wadhwani AI has built:
- ✅ Reading Fluency Signal → ORF / Vaachan Samiksha
- ✅ Spoken English Signal → SEAP
- ❌ **Conceptual Understanding Signal → this is what Mootion creates**

<br/>

---

<br/>

## 🔄 The Diagnostic Loop

Every component in Mootion exists to serve one purpose: generate the signal.

```
Teacher assigns chapter
         │
         ▼
Student explores         ←── Manim video + HTML5 simulation + 3D model
(builds baseline intuition so explanation is possible)
         │
         ▼
Student explains         ←── Speaks to Mootion the AI child (Gemini Live API)
(voice cannot be faked the way multiple choice can)
         │
         ▼
AI evaluates             ←── LLM scores Clarity / Accuracy / Depth
(three deliberate dimensions, not arbitrary metrics)
         │
         ▼
Scores stored            ←── ConceptScore per student per topic per attempt
         │
         ▼
Teacher sees signal      ←── Dashboard: clusters, trends, misconceptions
         │
         ▼
Student reattempts       ←── Scores improve. Loop strengthens.
```

> Every step earns its place by converting student interaction into structured insight.

<br/>

<!-- REPLACE WITH DIAGNOSTIC LOOP DIAGRAM -->
<!-- <p align="center">
  <img src="docs/assets/diagnostic-loop.png" width="800" alt="The Diagnostic Loop">
</p> -->

<br/>

---

<br/>

## ⚙️ Engines

Mootion has three core generation engines. Each exists because the alternatives were insufficient.

### 🎬 Manim Video Engine

Static diagrams don't show motion — and motion is what physics, chemistry, and biology actually are.

The video engine converts any chapter concept into a 3Blue1Brown-style animated explainer, generated entirely on demand. No pre-recorded content. No YouTube links.

**Pipeline:**

```
Concept Text
     │
     ▼
LLM → Scene Plan JSON          (subject, structure, timestamps)
     │
     ▼
LLM → Manim Code               (Python animation per scene)
     │
     ▼
Manim Renderer                 (renders each scene to video)
     │
     ▼
LLM → Narration Script         (per-scene TTS-ready text)
     │
     ▼
Azure TTS → Audio              (neural voiceover per scene)
     │
     ▼
FFmpeg → Final Video           (stitched, muxed, uploaded to MinIO/R2)
```

<!-- REPLACE WITH VIDEO PIPELINE SCREENSHOT OR EXAMPLE FRAME -->
<!-- <p align="center">
  <img src="docs/assets/video-pipeline.png" width="800" alt="Video Generation Pipeline">
</p> -->

<br/>

---

### 🧮 Simulation Engine

Students need to manipulate variables — not watch someone else do it.

The simulation engine converts natural language prompts into fully interactive, offline-capable HTML5/Canvas simulations through a 5-stage pipeline with scientific validation built in.

**Pipeline:**

```
Prompt ("Explain projectile motion")
     │
     ▼
Stage 1: Prompt Understanding    → classifies subject, topic, variables, sim type
     │
     ▼
Stage 2: Simulation Planning     → structured JSON spec (equations, ranges, controls)
     │
     ▼
Stage 3: Simulation Builder      → injects into Canvas 2D render loop HTML template
     │
     ▼
Stage 4: Scientific Validator    → checks units, equation validity, range boundaries
     │
     ▼
Stage 5: UI Quality + Assessment → layout check, contrast check, 3 embedded student questions
     │
     ▼
Interactive Playable Simulation  → self-contained HTML, no CDN dependency
```

<!-- REPLACE WITH SIMULATION SCREENSHOT -->
<!-- <p align="center">
  <img src="docs/assets/simulation-example.png" width="800" alt="Interactive Simulation Example">
</p> -->

<br/>

---

### 🌌 3D Model Engine

Molecular geometry, cell structure, and anatomy cannot be fully understood in 2D.

The 3D engine fetches, ranks, and embeds interactive Sketchfab models matched to the chapter topic — no external navigation, no broken links, fully embedded in the learning session.

**Pipeline:**

```
Chapter topic
     │
     ▼
Sketchfab API query             (semantic search for matching 3D model)
     │
     ▼
Local candidate ranking         (relevance scoring against topic)
     │
     ▼
Embedded 3D viewer              (Sketchfab iframe, no platform switch)
```

<!-- REPLACE WITH 3D MODEL SCREENSHOT -->
<!-- <p align="center">
  <img src="docs/assets/3d-model-example.png" width="800" alt="3D Model Viewer">
</p> -->

<br/>

---

### 🎤 Voice Roleplay Engine

A student who has memorized a definition will collapse the moment a curious AI child asks *"but why does that happen?"*

Voice is the signal. It cannot be faked.

**Pipeline:**

```
Student mic → Web Audio API
     │
     ▼
Downsampled to 16kHz PCM → base64 encoded
     │
     ▼
WebSocket → Express Node proxy
     │
     ▼
Gemini Live API (gemini-2.0-flash-live-preview)
Roleplay persona: curious, 10-year-old, no prior knowledge
     │
     ▼
Real-time audio response → streamed back to student
Text transcript → captured in parallel
     │
     ▼
Session ends → transcript sent to /api/analytics/submit-explanation
     │
     ▼
LLM scores: Clarity / Accuracy / Depth → stored as ConceptScore
```

**Fallback:** Browser-native `SpeechRecognition` API activates automatically on low-connectivity or WebSocket failure. Offline-first by design.

<!-- REPLACE WITH VOICE SESSION SCREENSHOT -->
<!-- <p align="center">
  <img src="docs/assets/voice-session.png" width="800" alt="Voice Explanation Session">
</p> -->

<br/>

---

### ❓ Doubt Engine

A stuck student stops learning. At a 1:45 teacher-student ratio, "raise your hand" is not a viable solution.

When a student gets stuck, they photograph their notebook or type their question. The Doubt Engine intercepts, generates a clarification scoped to their exact point of confusion, and restarts the learning path — without teacher intervention and without breaking the session flow.

<br/>

---

## 📊 Analytics System

### Student Analytics

Every explanation attempt is stored as a `ConceptScore` with three dimensions:

| Dimension | What it measures | Why it matters |
|---|---|---|
| **Clarity** | Can the student structure the concept coherently? | Confused logic masks deep knowledge |
| **Accuracy** | Are the scientific facts correct? | Misconceptions are the actual enemy |
| **Depth** | Does the student go beyond the surface definition? | Surface recall and genuine understanding look identical on a test |

Students see their own analytics at `/student/analytics`:
- Chapter-wise score cards with attempt history
- Trend arrows (↑↓) showing whether understanding is improving
- Radar chart across all chapters (Clarity / Accuracy / Depth axes)
- "Your Weakest Topics" — bottom 3 chapters by overall score

<!-- REPLACE WITH STUDENT ANALYTICS SCREENSHOT -->
<!-- <p align="center">
  <img src="docs/assets/student-analytics.png" width="900" alt="Student Analytics Dashboard">
</p> -->

<br/>

### Teacher Analytics & Cohort Clustering

Teachers see `/teacher/analytics/:classId`:

- **Chapter overview table** — avg score, student count, weakest students per chapter, sortable by score ascending so weakest topics surface first
- **KMeans clustering** — students automatically grouped into 🔴 Struggling / 🟡 Average / 🟢 Strong per chapter using scikit-learn
- **Misconception-specific insight** — not "37% of your class failed" but "8 specific students share the same gap on osmosis gradient limits vs definitions"
- **Drill-down** — click any student name → read-only view of their full explanation history

> *"Telling a teacher '37% of class scored below 5' is useless. Mootion tells her which 8 students are struggling with the same misconception."*

<!-- REPLACE WITH TEACHER DASHBOARD SCREENSHOT -->
<!-- <p align="center">
  <img src="docs/assets/teacher-dashboard.png" width="900" alt="Teacher Analytics Dashboard">
</p> -->

<br/>

---

## 🏗 Architecture

Mootion is a modular monolith composed of four primary services, integrated via Redis job queue and S3-compatible object storage.

```
    ┌────────────────────────────────────────────────────────────────────────┐
    │                          BROWSER (Port 3000)                           │
    │              React 19 + Vite + TypeScript + Tailwind v4                │
    │                                                                        │
    │   Student Portal            Teacher Portal            Voice Interface  │
    │   /student/tasks            /teacher/playground       LiveVoiceActivity│
    │   /student/analytics        /teacher/analytics        (WS Client)      │
    └───────────┬───────────────────────┬───────────────────────────┬────────┘
                │                       │                           │
                │ REST/API              │ WS Audio (PCM)            │ REST/API
                ▼                       ▼                           ▼
    ┌───────────────────────┐ ┌───────────────────┐     ┌────────────────────┐
    │ Express Server (3000) │ │  Gemini Live API  │     │   FastAPI Backend  │
    │                       │ │  WebSocket Proxy  │     │     (Port 8000)    │
    │ Serve Client Assets   │ │  Bidirectional    │     │                    │
    └───────────┬───────────┘ └───────────────────┘     │ Auth (JWT/OAuth),  │
                │                                       │ Curriculum Presets,│
                └─────────────── (Proxied REST) ───────►│ In-process HTML5   │
                                                        │ Simulation Engine  │
                                                        └─────────┬──────────┘
                                                                  │
                                                      ┌───────────┴──────────┐
                                                      ▼                      ▼
                                                ┌───────────┐          ┌───────────┐
                                                │ DB Store  │          │   Redis   │
                                                │ PostgreSQL│          │   Queue   │
                                                │ / SQLite  │          └─────┬─────┘
                                                └───────────┘                │
                                                                             ▼
                                                               ┌───────────────────┐
                                                               │ Background Worker │
                                                               │  (media_worker)   │
                                                               └─────────┬─────────┘
                                                                         │
                                          ┌──────────────────────────────┴──────────┐
                                          ▼ (HTTP POST /explain)                    ▼ (Search API)
                             ┌───────────────────────────┐              ┌───────────────────────┐
                             │ Animation Engine (:8001)  │              │     Sketchfab API     │
                             │                           │              │    (model_finder)     │
                             │  1. Scene / Code Planner  │              └───────────────────────┘
                             │     (Claude / OpenAI)     │
                             │  2. Manim Frame Renderer  │
                             │  3. Azure Neural TTS      │
                             │  4. ffmpeg Mux & Stitch   │
                             └────────────┬──────────────┘
                                          │
                                          ▼
                             ┌───────────────────────────┐
                             │      Media Storage        │
                             │    (Local File System     │
                             │      / MinIO / R2)        │
                             └───────────────────────────┘
```

<br/>

---

## 🔌 API Reference

### Analytics Endpoints

| Method | Route | Auth | Description |
|---|---|---|---|
| `POST` | `/api/analytics/submit-explanation` | Student JWT | Submit transcript → LLM scores → store ConceptScore |
| `GET` | `/api/analytics/student/{id}/scores` | Student (own) / Teacher (class) | All scores grouped by chapter with trend |
| `GET` | `/api/analytics/class/{id}/overview` | Teacher JWT | Per-chapter avg, weakest students |
| `POST` | `/api/analytics/class/{id}/compute-clusters` | Teacher JWT | Run KMeans, upsert StudentTopicCluster |
| `GET` | `/api/analytics/class/{id}/clusters` | Teacher JWT | Clusters with student names joined |

### Core Endpoints

| Method | Route | Description |
|---|---|---|
| `POST` | `/api/auth/login` | JWT login |
| `POST` | `/api/auth/google` | Google OAuth |
| `GET` | `/api/curriculum/ncert/{grade}/{subject}` | NCERT syllabus bootstrap |
| `POST` | `/api/assignments` | Create assignment (triggers Redis job) |
| `GET` | `/api/assignments/{id}/status` | Media generation status |
| `POST` | `/api/simulation/generate` | Run simulation pipeline |
| `GET` | `/api/evaluate-session` | Score a voice session transcript |
<br>

---
## 🗄️ Database Schema

Mootion utilizes a decoupled relational schema designed for high-throughput streaming analysis (Gemini Live), multi-tenant school/class grouping, and offline-first queue states. All primary keys utilize globally unique `UUIDv4` identifiers to allow local generation and synchronization.

```mermaid
erDiagram
  users {
    UUID id PK
    string login_id
    string role
    string full_name
    text password_hash
    string preferred_language
    bool onboarding_completed
  }
  oauth_accounts {
    UUID id PK
    UUID user_id FK
    string provider
    string provider_user_id
    string email
  }
  oauth_states {
    UUID id PK
    string provider
    string requested_role
    string state
    datetime expires_at
  }
  sessions {
    UUID id PK
    UUID user_id FK
    string refresh_token_hash
    datetime expires_at
    datetime revoked_at
  }
  schools {
    UUID id PK
    string name
    string code
    UUID created_by_teacher_id FK
  }
  teacher_school_memberships {
    UUID id PK
    UUID teacher_id FK
    UUID school_id FK
  }
  classes {
    UUID id PK
    UUID school_id FK
    string grade
    string subject
    string class_code
    string display_name
  }
  teacher_class_memberships {
    UUID id PK
    UUID teacher_id FK
    UUID class_id FK
    bool is_primary
  }
  student_class_memberships {
    UUID id PK
    UUID student_id FK
    UUID class_id FK
  }
  curriculum_plans {
    UUID id PK
    UUID class_id FK
    UUID created_by_teacher_id FK
    int version
    string title
    string source_type
    string status
    json curriculum_data
  }
  curriculum_snapshots {
    UUID id PK
    UUID curriculum_id FK
    int version
    string patch_operation
    json patch_payload
    json curriculum_data
  }
  chapters {
    UUID id PK
    UUID class_id FK
    UUID curriculum_id FK
    int sequence_number
    string title
    string status
  }
  chapter_assets {
    UUID id PK
    UUID chapter_id FK
    string asset_type
    string generation_status
    json payload_json
  }
  chapter_topics {
    UUID id PK
    UUID chapter_id FK
    int sequence_number
    string title
    string status
  }
  chapter_topic_assets {
    UUID id PK
    UUID topic_id FK
    string asset_type
    string generation_status
    json payload_json
  }
  assignments {
    UUID id PK
    UUID class_id FK
    UUID chapter_id FK
    UUID created_by_teacher_id FK
    string assignment_type
    string title
    string status
    json content_json
  }
  assignment_recipients {
    UUID id PK
    UUID assignment_id FK
    UUID student_id FK
  }
  chapter_asset_generation_jobs {
    UUID id PK
    UUID assignment_id FK
    UUID chapter_asset_id FK
    string asset_type
    string status
    int attempt_count
  }
  student_attempts {
    UUID id PK
    UUID student_id FK
    UUID assignment_id FK
    int score_understanding
    int score_reasoning
    int score_expression
    text ai_feedback
  }
  student_doubts {
    UUID id PK
    UUID student_id FK
    UUID class_id FK
    string topic
    text query_text
    string status
    json messages
  }
  user_quotas {
    UUID id PK
    UUID user_id FK
    int doubt_videos_used_today
    int playground_items_used_week
  }
  simulation_records {
    UUID id PK
    string simulation_id
    text prompt
    json spec_json
    text html
    int quality_score
    string phase
  }
  student_ai_chat_threads {
    UUID id PK
    UUID student_id FK
    UUID class_id FK
    UUID chapter_id FK
    UUID assignment_id FK
    string title
    string status
    json context_json
  }
  student_ai_chat_messages {
    UUID id PK
    UUID chat_id FK
    string role
    text content
    string tool_name
    json asset_json
  }
  concept_scores {
    UUID id PK
    UUID student_id FK
    UUID chapter_id FK
    UUID class_id FK
    float clarity_score
    float accuracy_score
    float depth_score
    float overall_score
    text llm_feedback
    json gaps
    int attempt_number
  }
  student_topic_clusters {
    UUID id PK
    UUID class_id FK
    UUID chapter_id FK
    string cluster_label
    json student_ids
    float avg_score
  }

  users ||--o{ oauth_accounts : "has"
  users ||--o{ sessions : "has"
  users ||--o{ teacher_school_memberships : "teaches at"
  users ||--o{ teacher_class_memberships : "teaches"
  users ||--o{ student_class_memberships : "enrolled"
  users ||--o{ student_attempts : "submits"
  users ||--o{ student_doubts : "raises"
  users ||--o{ user_quotas : "has"
  users ||--o{ assignment_recipients : "receives"
  users ||--o{ student_ai_chat_threads : "chats"
  users ||--o{ concept_scores : "scored"
  schools ||--o{ teacher_school_memberships : "has"
  schools ||--o{ classes : "has"
  classes ||--o{ teacher_class_memberships : "has"
  classes ||--o{ student_class_memberships : "has"
  classes ||--o{ curriculum_plans : "has"
  classes ||--o{ chapters : "has"
  classes ||--o{ assignments : "has"
  classes ||--o{ student_doubts : "for"
  classes ||--o{ student_ai_chat_threads : "context"
  classes ||--o{ concept_scores : "in"
  classes ||--o{ student_topic_clusters : "has"
  curriculum_plans ||--o{ curriculum_snapshots : "versioned by"
  curriculum_plans ||--o{ chapters : "structures"
  chapters ||--o{ chapter_assets : "has"
  chapters ||--o{ chapter_topics : "has"
  chapters ||--o{ assignments : "has"
  chapters ||--o{ student_ai_chat_threads : "context"
  chapters ||--o{ concept_scores : "for"
  chapters ||--o{ student_topic_clusters : "for"
  chapter_topics ||--o{ chapter_topic_assets : "has"
  assignments ||--o{ assignment_recipients : "sent to"
  assignments ||--o{ student_attempts : "attempted"
  assignments ||--o{ chapter_asset_generation_jobs : "triggers"
  assignments ||--o{ student_ai_chat_threads : "context"
  chapter_assets ||--o{ chapter_asset_generation_jobs : "generated by"
  student_ai_chat_threads ||--o{ student_ai_chat_messages : "contains"
```

### Core Architecture Domains

### 1. Identity & Access Control
* **`users`**: Contains system actors (Teachers, Students). Includes auth configurations (`password_hash`, `preferred_language`, `onboarding_completed`).
* **`oauth_accounts`**: Map external logins directly to internal accounts (`provider`, `provider_user_id`, `email`).
* **`sessions`**: Tracks client security architecture (`refresh_token_hash`, expiration windows).

### 2. Academic Hierarchy (Multi-Tenant)
* **`schools`**: Independent organizational roots keyed by unique internal `code` parameters.
* **`classes`**: Tracks specific iterations of subjects (e.g., *Grade 9 Mathematics*) containing individual access codes (`class_code`).
* **Membership Tables**: Explicit join tables managing user tenancy:
  * `teacher_school_memberships`
  * `teacher_class_memberships` (with an `is_primary` flag tracking principal class ownership)
  * `student_class_memberships`

### 3. Asynchronous Content & Engine Registry
* **`curriculum_plans` / `curriculum_snapshots`**: Captures structural teacher adjustments, storing dynamic trees within custom `curriculum_data` JSON specs alongside historical system audits.
* **`chapters` / `chapter_topics`**: Multi-layered reference matrices for standard NCERT nodes.
* **`chapter_assets` / `chapter_topic_assets`**: Links media engine outputs (Manim arrays, canvas render configurations, Sketchfab targets) explicitly to the curriculum hierarchy. Includes generation payloads, state markers, and S3 paths (`storage_bucket`/`storage_key`).
* **`chapter_asset_generation_jobs`**: The state machine driving the background Redis stack. Tracks background processing steps (`attempt_count`, `queued_at`, `error_message`).

### 4. Assignment Metrics & Diagnostic Logs
* **`assignments` / `assignment_recipients`**: Tracks explicit assignments pushed out by teachers to targeted student groups.
* **`student_attempts`**: Holds hard telemetry signals from individual interactive runs, tracking voice expressions across `score_understanding`, `score_reasoning`, and `score_expression`.
* **`student_doubts`**: Powers the active interruption engine. Captures visual/text inputs, state, thread structures via `messages` JSON blocks, and references to generated media keys.

### 5. AI Analytics & Cluster Engine
* **`simulation_records`**: A standalone registry of auto-generated components indexed by unique `simulation_id` hash strings. Persists validation rules, durations, and UI scores.
* **`concept_scores`**: The principal source of insights for teacher visualization tracks. Translates audio transcripts directly into structural indices:
  * `clarity_score`, `accuracy_score`, `depth_score`, `overall_score` (Float targets scaled 1-10)
  * `gaps`: Structured JSON array recording conceptual friction points flaggable by the teacher.
* **`student_topic_clusters`**: Holds static output records computed out-of-process via the scikit-learn background worker. Maps class trends directly into array elements (`student_ids` JSON array) matched with `cluster_label` states (`STRUGGLING`, `AVERAGE`, `STRONG`).


<br>

---

### WebSocket

```
WS /live?chapter_id=<id>&class_id=<id>

Client → Server: { "audio": "<base64 PCM 16kHz>" }
Server → Client: { "audio": "<base64>" }
              | { "transcript": "<text>" }
              | { "interrupted": true }
```

<br/>

---

## ⚙️ Tech Stack

### Frontend

| Category | Technology |
|---|---|
| UI Framework | React 19 + TypeScript 5.8 |
| Build | Vite 6 |
| Server | Express 4 (`server.ts`) — Vite middleware + WebSocket proxy |
| Styling | Tailwind CSS v4 |
| Charts | Recharts (RadarChart, LineChart) |
| Voice | Web Audio API → WebSocket → Gemini Live |
| STT Fallback | Browser-native `window.SpeechRecognition` |

### Backend

| Category | Technology |
|---|---|
| API Framework | FastAPI (Python 3.11) |
| ORM | SQLAlchemy + Alembic |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Job Queue | Redis (BRPOP worker pattern) |
| Object Storage | MinIO / Cloudflare R2 |
| Animation | Manim community edition |
| 3D Models | Sketchfab API |
| Voice AI | Gemini Multimodal Live API |
| LLM Scoring | Gemini (structured JSON output) |
| Clustering | scikit-learn KMeans (n=3) |
| TTS | Azure Speech SDK |

<br/>

---

## 🚀 Getting Started

### Prerequisites

- Node.js v20+ and npm v10+
- Python 3.11+ with pip
- Redis (local or cloud)
- Manim community edition: `pip install manim`
- API keys: Gemini, Azure Speech, Sketchfab

### Frontend

```bash
cd frontend
npm install
cp .env.example .env
# Add: GEMINI_API_KEY, VITE_API_URL

npm run dev
# → http://localhost:3000
```

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install scikit-learn --break-system-packages

cp .env.example .env
# Add: DATABASE_URL, GEMINI_API_KEY, AZURE_SPEECH_KEY, REDIS_URL, MINIO_URL

alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### Background Worker

```bash
cd backend
python -m app.worker
# Polls Redis, runs Manim / Sketchfab / Quiz / Simulation jobs
```

### Environment Variables

**Frontend `.env`**

| Variable | Required | Description |
|---|---|---|
| `GEMINI_API_KEY` | Yes | Google Gemini API key |
| `VITE_API_URL` | Yes | Backend URL (default: `http://localhost:8000`) |

**Backend `.env`**

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | Yes | SQLite or PostgreSQL connection string |
| `GEMINI_API_KEY` | Yes | For LLM scoring and voice |
| `REDIS_URL` | Yes | Redis connection string |
| `MINIO_URL` | Yes | Object storage endpoint |
| `MINIO_ACCESS_KEY` | Yes | Object storage access key |
| `MINIO_SECRET_KEY` | Yes | Object storage secret key |
| `AZURE_SPEECH_KEY` | Yes | Azure TTS key |
| `AZURE_SPEECH_REGION` | Yes | Azure TTS region |
| `SKETCHFAB_API_KEY` | Yes | Sketchfab 3D model API |
| `SECRET_KEY` | Yes | JWT signing secret |

<br/>

---

## 📁 Project Structure

```
    mootion/
    ├── frontend/
    │   ├── src/
    │   │   ├── app/                          # Main React App initialization files
    │   │   ├── components/                   # Shared UI Components
    │   │   │   ├── ChatbotFab.tsx            # Floating chatbot assistant
    │   │   │   ├── ConnectItActivity.tsx     # Concept matching mini-game
    │   │   │   ├── Eye.tsx                   # Eye component for look gesture trigger
    │   │   │   ├── FAQItem.tsx
    │   │   │   ├── GestureNavigation.tsx     # Navigation via camera gestures
    │   │   │   ├── LiveVoiceActivity.tsx     # Voice recording, transcript evaluation
    │   │   │   ├── LogoutModal.tsx
    │   │   │   ├── NavItem.tsx
    │   │   │   └── ProtectedRoute.tsx        # Auth Guard Route Wrapper
    │   │   ├── data/
    │   │   ├── lib/
    │   │   │   ├── api.ts                    # HTTP API wrapper using fetch
    │   │   │   └── translation.ts
    │   │   ├── pages/                        # Screen Pages
    │   │   │   ├── LandingPage.tsx           # Entry home page
    │   │   │   ├── OnboardingPage.tsx        # General onboarding flow
    │   │   │   ├── StudentAnalytics.tsx      # Student metrics dashboard
    │   │   │   ├── StudentHomePage.tsx       # Student assignments/tasks portal
    │   │   │   ├── StudentLoginPage.tsx
    │   │   │   ├── StudentPlaygroundPage.tsx # Voice/simulation activities workspace
    │   │   │   ├── StudentSignupPage.tsx
    │   │   │   ├── StudentTaskActivityPage.tsx # Task execution environment
    │   │   │   ├── StudentTasksPage.tsx
    │   │   │   ├── TeacherAnalytics.tsx      # Aggregate classroom diagnostics
    │   │   │   ├── TeacherAnalyticsPage.tsx
    │   │   │   ├── TeacherBroadcastPage.tsx  # Interactive board broadcast controls
    │   │   │   ├── TeacherChapterSetupPage.tsx # Curriculum planner per chapter
    │   │   │   ├── TeacherClassViewPage.tsx  # Roster & assignment overview
    │   │   │   ├── TeacherDashboardPage.tsx  # General dashboard overview
    │   │   │   ├── TeacherDoubtsPage.tsx     # Broadcast Q&A forum
    │   │   │   ├── TeacherLoginPage.tsx
    │   │   │   ├── TeacherOnboardingPage.tsx
    │   │   │   └── TeacherTopicSetupPage.tsx   # Visual asset compilation planner
    │   │   ├── App.tsx                       # Main Router component (React Router)
    │   │   ├── index.css
    │   │   └── main.tsx                      # Render entry point
    │   ├── package.json
    │   └── tsconfig.json
    │
    ├── backend/
    │   ├── app/
    │   │   ├── api/                          # FastAPI routers
    │   │   │   ├── analytics.py              # Clustering + concept scoring endpoints
    │   │   │   ├── assignments.py            # Creating assignments, task schedules
    │   │   │   ├── auth.py                   # Token authentication
    │   │   │   ├── chapters.py               # NCERT chapters indexing
    │   │   │   ├── chat_ai.py                # Broadcast chatbot responses
    │   │   │   ├── curriculum.py             # Presets & manual roadmap configs
    │   │   │   ├── health.py
    │   │   │   ├── library.py                # Video / 3D model asset browser
    │   │   │   ├── media.py                  # Assets & queue status checkers
    │   │   │   ├── ocr.py                    # Hand written notes OCR
    │   │   │   ├── simulation.py             # RAG-based HTML5 code generator
    │   │   │   ├── student_assignments.py
    │   │   │   ├── students.py               # Student dashboards APIs
    │   │   │   └── teachers.py               # Classrooms, invites, broadcasts
    │   │   ├── core/                         # Auth, Db & Settings Configuration
    │   │   │   ├── config.py
    │   │   │   ├── database.py               # SQLAlchemy Database engine
    │   │   │   ├── deps.py                   # Dependency injectables (session, user)
    │   │   │   ├── models.py                 # Core SQLAlchemy models (ConceptScore, etc.)
    │   │   │   ├── redis.py                  # Redis Client Configuration
    │   │   │   ├── schemas.py
    │   │   │   ├── security.py               # Hashing & Token generation
    │   │   │   └── storage.py                # S3 media upload configurations
    │   │   ├── repositories/                 # SQLAlchemy DB wrappers
    │   │   ├── schemas/                      # Pydantic schemas (Chapter, Student)
    │   │   ├── services/                     # Business logic
    │   │   │   ├── assignment_service.py     # Scheduling media worker tasks
    │   │   │   ├── auth_service.py
    │   │   │   ├── chapter_service.py        # Generating curriculum blueprints
    │   │   │   ├── chat_ai_service.py        # Agentic assessment grading logic
    │   │   │   ├── clustering_service.py     # KMeans concept analytics grouping
    │   │   │   ├── curriculum_presets.py
    │   │   │   ├── library_service.py
    │   │   │   ├── media_queue.py            # Redis Queue helper for worker execution
    │   │   │   ├── media_service.py
    │   │   │   ├── media_worker.py           # Background processor for Manim/TTS queues
    │   │   │   ├── model_finder.py           # Sketchfab API search and ranking
    │   │   │   ├── onboarding_service.py
    │   │   │   ├── rag_service.py            # Context retriever for STEM topics
    │   │   │   └── student_actions_service.py
    │   │   ├── simulation_engine/            # Interactive HTML5 generator agent
    │   │   │   ├── agent_workflows.py        # Multi-layer layout & validation planner
    │   │   │   ├── assessment_layer.py
    │   │   │   ├── llm_prompts.py            # Templates for planning and coding HTML5
    │   │   │   ├── pipeline.py               # Orchestrator running the simulation stages
    │   │   │   ├── prompt_understanding_layer.py
    │   │   │   ├── schemas.py
    │   │   │   ├── scientific_validation.py
    │   │   │   ├── simulation_builder.py
    │   │   │   ├── simulation_planning_layer.py
    │   │   │   ├── templates/                # Base index.html templates
    │   │   │   └── ui_quality_layer.py
    │   │   └── main.py                       # Backend server entry point
    │   ├── alembic/                          # DB migrations
    │   └── requirements.txt
    │
    ├── animation-engine/                    # Manim compilation & TTS compiler service
    │   ├── app/
    │   │   ├── prompts/                      # Subject-specific styling guidelines
    │   │   ├── stages/                       # Generation stages
    │   │   │   ├── stage1_scenes.py          # Scene structure generator
    │   │   │   ├── stage2_manim.py           # Manim visual code compiler
    │   │   │   ├── stage3_script.py          # Narrator script generator
    │   │   │   ├── stage4_tts.py             # Azure Speech audio synthesizer
    │   │   │   └── stage5_stitch.py          # ffmpeg video & audio stitcher
    │   │   ├── utils/
    │   │   │   ├── cost_tracker.py           # LLM and synthesis cost calculator
    │   │   │   ├── generate_uid.py
    │   │   │   ├── json_safe.py              # Nested JSON validator
    │   │   │   ├── llm.py                    # Azure OpenAI & Anthropic client gateway
    │   │   │   └── timestamps_extractor.py
    │   │   └── main.py                       # FastAPI render api
    │   └── requirements.txt
    │
    ├── ingestion/                           # Raw NCERT Data Parser
    │   ├── ingest_all.py                     # Processing and embedding PDF data
    │   └── test_azure_embeddings.py
    │
    ├── sim/                                 # Interactive Phet Simulator library
    │   ├── sims.json                         # Offline mapping for STEM concepts
    │   └── verify_phet_sims.py
    │
    ├── docs/                                # Technical API & Design documentation
    ├── nginx/                               # Web reverse proxy
    └── docker-compose.yml
```

<br/>

---

## 📸 UI Snippet


<img width="1917" height="1022" alt="image" src="https://github.com/user-attachments/assets/e021ba8c-1a76-4c41-b660-45822d0ea93d" />


<p align="center">
  <i>Student Dashboard</i>
</p>

<br>

---

<img width="1918" height="1023" alt="image" src="https://github.com/user-attachments/assets/16164be1-321a-4aef-91bd-b1a329390fa6" />


<p align="center">
  <i>Explain It Assignment</i>
</p>

<br/>

---

<img width="1918" height="1028" alt="image" src="https://github.com/user-attachments/assets/18c4c3e6-5b2f-4d05-a821-908c8381c8a2" />


<p align="center">
  <i>Recall It Assignment</i>
</p>

<br/>

---

<img width="1918" height="1025" alt="image" src="https://github.com/user-attachments/assets/b9f346ea-a162-429e-b719-5751e70b0ecf" />


<p align="center">
  <i>Connect It Assignment</i>
</p>
<br/>

---
<img width="1918" height="1027" alt="image" src="https://github.com/user-attachments/assets/308ba577-2d31-40dd-a6b2-c573102936c7" />


<p align="center">
  <i>Assigned Concept Video Interface</i>
</p>
<br/>

---
<img width="1918" height="1025" alt="image" src="https://github.com/user-attachments/assets/b84c427a-4bee-4a35-8277-d7dfab93dc2e" />


<p align="center">
  <i>Assigned 3D Model Interface</i>
</p>
<br/>

---
<img width="1918" height="1022" alt="image" src="https://github.com/user-attachments/assets/1318c61d-188c-4ade-bf6f-bed21c08557d" />


<p align="center">
  <i>Interactive Playground Interface</i>
</p>
<br/>

---
<img width="1918" height="1026" alt="image" src="https://github.com/user-attachments/assets/4c31cb00-4666-407b-ac5e-f54aac66d55d" />

<p align="center">
  <i>Doubt Engine Interface</i>
</p>

<br/>

---

## 🧪 Evaluation

The LLM scoring pipeline was evaluated against independent teacher judgment across 12 pilot student explanation transcripts spanning Physics and Biology NCERT topics.

| Dimension | LLM vs Teacher Agreement | Cohen's Kappa |
|---|---|---|
| Accuracy | 81% | 0.74 (Strong) |
| Clarity | 78% | 0.71 (Strong) |
| Depth | 74% | 0.68 (Moderate) |

> Depth is the hardest dimension to score — this matches human inter-rater variance. The system is designed for diagnostic use, not high-stakes grading. Teachers can flag or override any score from the dashboard.

Full methodology: [`docs/ANALYTICS_TESTING_GUIDE.md`](docs/ANALYTICS_TESTING_GUIDE.md)

<br/>

---

## 💰 Cost at Scale

| Operation | Cost per unit |
|---|---|
| Voice explanation + LLM scoring | $0.008 |
| Simulation generation | $0.11 |
| Manim video generation | $0.02 |
| **1,000 active students/day (blended)** | **₹6.10 per student per day** |

Fiscally invisible for district-level deployment. No per-school configuration required — NCERT bootstrap handles curriculum setup automatically.

<br/>

---

## 🛡 Responsible AI

- **Teacher-in-the-loop**: AI generates the signal. Teacher decides what to do with it. No automated grading, no scores sent to parents without teacher review.
- **No surveillance architecture**: Data serves as localized diagnostic aids, not institutional performance records.
- **Multilingual**: Students can explain in Hindi, Punjabi, Tamil, Telugu, or English. Language choice does not affect score.
- **Low-device compatible**: Runs on ₹8,000 Android phones. PWA-ready, no app install required.
- **Offline-friendly**: Browser-native STT fallback + self-contained HTML simulations work without connectivity.
- **Explainable signals**: Every score is paired with a 2-sentence LLM feedback paragraph. Never just a number.
- **Data retention**: Student voice files are downsampled, processed, and purged within 7 days. Only quantitative diagnostic metrics are retained.

<br/>

---

## 👥 Team

| Name | Role | Contribution |
|---|---|---|
| **Rachit Goyal** | Systems Architect | Backend orchestration, scalable pipeline frameworks |
| **Poorvika Grover** | Design & UX Lead | End-to-end visual identity, user journey |
| **Goyam Jain** | Lead ML Engineer | LLM scoring, KMeans pipeline, AI model optimization |
| **Sartaj Kaur** | Product Lead & Strategy | Vision, roadmap, user validation, documentation |
| **Divyansh Chawla** | Lead Backend Engineer | FastAPI endpoints, WebSocket architecture |

<br/>

---

<p align="center">
  <b>"Mootion turns student interactions into actionable understanding signals for teachers."</b>
  <br/><br/>
  The enrollment problem is solved. The understanding problem now has a real-time signal.
  <br/><br/>
  <sub>© Mootion — Team Evolve AI — Wadhwani AI SahAI Hackathon 2026</sub>
</p>
