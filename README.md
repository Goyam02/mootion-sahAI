<p align="center">
  <br/>
  <img alt="MOOTION" src="Frontend/public/read/home.png" width="600">
  <br/>
</p>

<p align="center">
  <b>AI-Powered Interactive STEM Learning Platform</b>
</p>

<p align="center">
  Built for <b>AI4India</b> by <b>Evolve AI</b>
</p>

<p align="center">
  <a href="#-overview"><b>Overview</b></a> •
  <a href="#-key-features"><b>Features</b></a> •
  <a href="#-architecture"><b>Architecture</b></a> •
  <a href="#-tech-stack"><b>Tech Stack</b></a> •
  <a href="#-getting-started"><b>Getting Started</b></a> •
  <a href="#-api-reference"><b>API</b></a> •
  <a href="#-team"><b>Team</b></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=white" alt="React 19">
  <img src="https://img.shields.io/badge/Vite-6-646CFF?logo=vite&logoColor=white" alt="Vite 6">
  <img src="https://img.shields.io/badge/FastAPI-latest-009688?logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/TypeScript-5.8-3178C6?logo=typescript&logoColor=white" alt="TypeScript">
  <img src="https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Gemini_AI-1.5-8E75B2?logo=google&logoColor=white" alt="Gemini AI">
  <img src="https://img.shields.io/badge/Tailwind-v4-06B6D4?logo=tailwindcss&logoColor=white" alt="Tailwind v4">
  <img src="https://img.shields.io/badge/PostgreSQL-Neon-4169E1?logo=postgresql&logoColor=white" alt="Neon PostgreSQL">
  <img src="https://img.shields.io/badge/Motion-12-000000?logo=framer&logoColor=white" alt="Motion">
  <img src="https://img.shields.io/badge/Three.js-latest-000000?logo=threedotjs&logoColor=white" alt="Three.js">
  <img src="https://img.shields.io/badge/Manim-latest-FF6F00?logo=python&logoColor=white" alt="Manim">
  <img src="https://img.shields.io/badge/Apache_2.0-license-blue" alt="License">
</p>

<br/>

---

<br/>

# 📖 Overview

**MOOTION** is an **AI-native interactive STEM learning platform** that unifies visual understanding, structured navigation, and active retention into one seamless flow. It targets the **250 million STEM learners** who have access to content but lack a connected system to understand, navigate, and retain it.

The platform is built across three core capabilities — **ASK** (generate concept-specific animated videos, simulations, and visualizations on demand), **PLAN** (convert any uploaded syllabus into a navigable visual roadmap with topic dependencies), and **PLAY** (reinforce retention through adaptive games and voice-based tutoring).

Unlike fragmented workflows where students switch between YouTube, PDFs, and broken simulations, MOOTION provides a **unified multi-modal workspace** with:

| Capability | What it does |
|---|---|
| **ASK** | Generates Manim-animated explainer videos, interactive physics simulations (Kepler's Laws 2D orbit simulator), and an immersive 3D solar system (Three.js) on demand |
| **PLAN** | Converts any topic or uploaded syllabus into a navigable visual roadmap with topic dependencies via AI |
| **PLAY** | Reinforces retention through 5 practice modes: timed challenges, flashcards, AI-generated audio lectures, "Teach the AI" voice conversations, and "Find the Wrong One" quizzes |

<br/>

---

<br/>

# ✨ Key Features

### 🧭 AI-Generated Learning Roadmaps

Enter any STEM topic (e.g., "Kepler's Laws") or upload a syllabus document — the AI generates a **structured concept graph** with logical dependencies, prerequisites, and progression paths.

- **Engine:** Google Gemini (`gemini-3-flash-preview`)
- **Visualization:** React Flow (`@xyflow/react`) with dagre auto-layout (top-to-bottom directed graph)
- **Node states:** `completed`, `in-progress`, `untouched` with visual indicators
- **Interaction:** Click any node to open its full-featured concept workspace with chat, simulations, and practice tools

### 💬 Conversational AI Tutor

The center panel of every concept workspace is a **topic-aware AI tutor** that engages in natural conversation with full history.

- **Model:** Gemini 3 Flash via `@google/genai` SDK
- **Context-aware:** Full message history sent with each request
- **Personality:** Concise, friendly, educational — 2-3 sentence responses
- **Entry points:** Preset quick-action buttons for launching simulations or practice modes

### 🎬 Automated Video Generation Pipeline

A **5-stage backend pipeline** (FastAPI, port 8001) that autonomously produces animated explainer videos from any topic:

```
Topic → Scene Planning (Azure OpenAI → JSON) 
      → Manim Code Gen + Rendering with LLM error correction (2 retries) 
      → Script/Narration Generation 
      → Azure TTS Audio (per-scene) 
      → Audio-Video Mux + Final Stitching + Optional SadTalker Face Animation
```

- **Self-healing:** Automatically fixes Manim compilation errors via LLM (up to 2 retries per scene)
- **Precision sync:** Per-scene audio-video alignment using ffprobe duration matching + ffmpeg `filter_complex`
- **Face animation:** Optional SadTalker integration for talking-head avatar overlay with GFPGAN enhancer
- **Output:** `final.mp4` at ~4-5 minute total generation time for 5 scenes

### 🌌 3D Interactive Simulations

Built-in browser-based simulations rendered directly inside the concept workspace:

| Simulation | Technology | Lines | Description |
|---|---|---|---|
| **Kepler's Laws Playground** | HTML5 Canvas | 745 | Interactive 2D orbit simulator — adjust eccentricity, semi-major axis, visualize equal-area sweeping in real time |
| **3D Solar System** | Three.js | 3106 | Full 3D solar system with texture-mapped planets, asteroid belt, dynamic lighting, custom shaders, orbit/zoom/pan camera controls |

### 🎮 Five Practice Modes

| Mode | UX | API Endpoint |
|---|---|---|
| **Challenge** | Timed 10-question MCQ quiz (30s per question), progress bar, percentage score | `POST /api/practice/challenge` |
| **Flashcards** | Flip-card with CSS 3D perspective transforms, shuffle, navigation | `POST /api/practice/flashcards` |
| **Listen** | AI-generated audio lecture with play/pause/restart, PCM 24kHz via Web Audio API | `POST /api/practice/listen` + TTS |
| **Prove It** | "Teach the AI" with voice (Web Speech API) or text — receives score + improvement suggestions | `POST /api/practice/prove-it` + WebSocket |
| **Wrong One** | Identify the incorrect statement among 4 options, with explanations | `POST /api/practice/wrong-one` |

### 🎤 Real-Time Voice Conversation (Gemini Live API)

WebSocket-based bidirectional audio streaming with Google's Gemini Live API. The AI plays a "curious student" — the user teaches it, and it asks counter-questions to deepen understanding.

- **Path:** `ws://localhost:3000/live?topic=<topic>`
- **Flow:** Browser mic → WebSocket → Gemini Live API → PCM audio response → Web Audio API playback
- **Voice model:** "Puck", PCM audio at 16kHz monoaural
- **Fallback:** Text-based interaction via `POST /api/practice/prove-it` when voice is unavailable

### 📄 Document Q&A with RAG (Backend API Service)

Upload PDF documents and ask questions with full context awareness:

- **Stack:** PyPDFLoader → LangChain `RecursiveCharacterTextSplitter` (chunk 700, overlap 150) → Nomic Embeddings (`nomic-embed-text-v1.5`) → ChromaDB vector store
- **LLM:** Groq (`llama-3.3-70b-versatile`) for answer generation
- **Retrieval:** Similarity search with score thresholding (< 0.6), top-12 documents
- **Context window:** Last 6 messages for conversation continuity
- **Summary detection:** Automatic detection of summary-type queries
- **Image Q&A:** OCR via Azure Vision API for image-based questions

### 🧩 Play Modes (RAG-Enhanced)

Backend API service provides three additional RAG-powered play modes for document-grounded learning:

- **Teach AI** — Explain concepts with document context; AI student asks follow-ups
- **Find Mistake** — Spot intentional errors in AI-generated explanations
- **Complete Missing Link** — Fill in missing logical steps in AI-generated explanations

<br/>

---

<br/>

# 🏗 Architecture

MOOTION follows a **two-backend microservices** architecture with a **unified Express + React frontend**:

```
┌────────────────────────────────────────────────────────────────────┐
│                        BROWSER (Port 3000)                          │
│                                                                      │
│  React 19 + Vite 6 + Tailwind v4 + Motion + ReactFlow + Three.js    │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐    │
│  │  Home/Onboard │  │  Roadmap     │  │  Concept Workspace     │    │
│  │  (pixel-art)  │  │  (ReactFlow) │  │ ┌──────┬────┬───────┐ │    │
│  └──────────────┘  └──────────────┘  │ │ Chat │Viz │Practice│ │    │
│                                        │ └──────┴────┴───────┘ │    │
│                                        └────────────────────────┘    │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                  Express 4 Server (server.ts)                │    │
│  │  ┌────────────────┐ ┌──────────────┐ ┌────────────────┐     │    │
│  │  │  Gemini AI API  │ │  Vite Dev    │ │  WebSocket     │     │    │
│  │  │  (Chat, TTS,    │ │  Middleware   │ │  (/live)       │     │    │
│  │  │  Roadmaps, Quiz)│ │              │ │  Gemini Live   │     │    │
│  │  └────────────────┘ └──────────────┘ └────────────────┘     │    │
│  └─────────────────────────────────────────────────────────────┘    │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
┌────────────────────────┐   ┌─────────────────────────┐
│  Backend: API Service  │   │  Backend: Pipeline      │
│  (FastAPI, :8000)      │   │  (FastAPI, :8001)       │
│                        │   │                         │
│  Q&A / RAG (Groq+Chroma)│   │  Stage 1: Scenes       │
│  TTS / Flashcards/Quiz  │   │  (Azure OpenAI)         │
│  Play Modes (3 games)   │   │  Stage 2: Manim         │
│  SadTalker Face Anim    │   │  Render + LLM fix       │
│  Roadmap CRUD           │   │  Stage 3: Script Gen    │
│  Chat History           │   │  Stage 4: Azure TTS     │
│                        │   │  Stage 5: Video Stitch   │
│  PostgreSQL (Neon)      │   │  + SadTalker opt        │
│  ChromaDB (vectors)     │   │                         │
│                        │   │  Filesystem: media/      │
│  AssemblyAI STT         │   │  outputs/ data/          │
└────────────────────────┘   └─────────────────────────┘
```

### Data Flow: Learning a Concept

```
1. User enters topic or uploads syllabus
       │
2. POST /api/generate-roadmap/text  →  Gemini generates JSON graph
   POST /api/generate-roadmap/file  →  Fallback roadmap for syllabus
       │
3. ReactFlow renders interactive concept graph (dagre layout, ~40 nodes)
       │
4. User clicks a node → /concept/:nodeId?topic=...
       │
5. ConceptWorkspace loads:
   ├─ Chat tutor (Gemini, topic-aware, full history)
   ├─ Left panel: Visual tools
   │   ├─ Storyboard: Manim video (POST to pipeline :8001/explain)
   │   ├─ Playground: Kepler 2D sim (iframe → kepler.html)
   │   └─ Universe: 3D solar system (iframe → Three.js)
   └─ Right panel: Practice tools (on demand)
       ├─ Challenge: POST /api/practice/challenge → 10 MCQs
       ├─ Flashcards: POST /api/practice/flashcards → 10 cards
       ├─ Listen: POST /api/practice/listen + /api/practice/tts
       ├─ Prove It: POST /api/practice/prove-it or WS /live
       └─ Wrong One: POST /api/practice/wrong-one → 10 questions
```

<br/>

---

<br/>

# ⚙️ Tech Stack

### Frontend

| Category | Technology | Purpose |
|---|---|---|
| **UI Framework** | React 19 + TypeScript 5.8 | Component model with strict typing |
| **Build Tool** | Vite 6 + `@vitejs/plugin-react` | HMR, bundling, React Fast Refresh |
| **Server Runtime** | Express 4 (custom `server.ts`) | API routes + Vite middleware + WebSocket server |
| **Routing** | React Router v7 | Client-side SPA routing |
| **Styling** | Tailwind CSS v4 + Autoprefixer | Utility-first CSS |
| **Animation** | Motion v12 (Framer Motion successor) | Spring layout animations, pixel-art reveal, scroll-driven morphing |
| **Graph Viz** | `@xyflow/react` v12 + `dagre` v0.8 | Interactive concept roadmap |
| **3D Rendering** | Three.js (custom 3106-line engine) | Solar system simulation with textures and shaders |
| **2D Physics** | HTML5 Canvas | Kepler's Laws orbit simulator |
| **Icons** | `lucide-react` | UI icon set (60+ icons) |
| **File Upload** | `react-dropzone` + `multer` (Express) | Syllabus drag-and-drop |
| **AI SDK** | `@google/genai` v1.29 | Gemini API: chat, TTS, roadmaps, quizzes, Live API |
| **WebSocket** | `ws` v8 | Gemini Live API voice streaming |
| **TS Runtime** | `tsx` v4 | TypeScript execution for dev server |

### Backend — API Service (port 8000)

| Category | Technology | Purpose |
|---|---|---|
| **Framework** | FastAPI (Python 3.11+) | Async REST API with auto-generated OpenAPI docs |
| **Database** | PostgreSQL (Neon) via SQLAlchemy | Relational storage for chats, messages, documents, videos, roadmaps |
| **Vector Store** | ChromaDB | Persistent document embeddings for retrieval-augmented generation |
| **LLM** | Groq (`llama-3.3-70b-versatile`) | Ultra-fast Q&A answer generation (512 tokens, 0.2 temp) |
| **Embeddings** | Nomic AI (`nomic-embed-text-v1.5`) | Document vectorization for similarity search |
| **TTS** | Azure Speech SDK | Neural text-to-speech |
| **STT** | AssemblyAI | Speech-to-text transcription |
| **OCR** | Azure Vision | Text extraction from images |
| **Face Animation** | SadTalker + GFPGAN | Talking-head avatar generation from audio + image |

### Backend — Pipeline Service (port 8001)

| Category | Technology | Purpose |
|---|---|---|
| **Framework** | FastAPI (Python 3.11+) | Video generation pipeline API |
| **LLM** | Azure OpenAI | Scene planning, Manim code generation, narration script generation |
| **Animation** | Manim (community edition) | Programmatic 3Blue1Brown-style math animations |
| **TTS** | Azure Speech SDK | Per-scene neural voiceover generation |
| **Video Processing** | FFmpeg + FFprobe | Audio-video muxing, scene stitching, duration analysis |
| **Face Animation** | SadTalker | Talking-head overlay on final video |

<br/>

---

<br/>

# 🚀 Getting Started

### Prerequisites

- **Node.js** v20+ and **npm** v10+
- **Python 3.11+** with `pip` and `venv`
- **FFmpeg** + **FFprobe** on PATH
- **Manim** community edition: `pip install manim`
- API keys for Gemini, Azure (OpenAI + Speech + Vision), Groq, Nomic, AssemblyAI, Neon PostgreSQL

### Frontend Setup

```bash
cd Frontend
npm install
cp .env.example .env
# Edit .env → set GEMINI_API_KEY

npm run dev
# → http://localhost:3000
```

### Backend — API Service

```bash
cd backend/backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r ../requirements.txt
pip install -r requirements.txt

# Set env vars (see configuration section below)
uvicorn app.main:app --reload --port 8000
# → http://localhost:8000
```

### Backend — Pipeline Service

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
mkdir -p outputs/scenes outputs/audio outputs/videos media

# Set env vars (see configuration section below)
uvicorn app.main:app --reload --port 8001
# → http://localhost:8001
```

### Production Build

```bash
cd Frontend
npm run build     # vite build + esbuild server bundle → dist/
npm start         # node dist/server.cjs on port 3000
```

<br/>

---

<br/>

# 🔐 Environment Variables

### Frontend (`.env`)

| Variable | Required | Description |
|---|---|---|
| `GEMINI_API_KEY` | Yes | Google Gemini API key for all AI features |

### Backend — API Service (`backend/backend/.env`)

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | Yes | Neon PostgreSQL connection string |
| `GROQ_API_KEY` | Yes | Groq API key for LLM inference |
| `NOMIC_API_KEY` | Yes | Nomic AI key for text embeddings |
| `ASSEMBLYAI_API_KEY` | Yes | AssemblyAI key for speech-to-text |
| `AZURE_SPEECH_KEY` | Yes | Azure Speech key for TTS |
| `AZURE_SPEECH_REGION` | Yes | Azure Speech region (e.g., `eastus`) |
| `AZURE_VISION_ENDPOINT` | Yes | Azure Vision endpoint URL |
| `AZURE_VISION_KEY` | Yes | Azure Vision API key |
| `SADTALKER_DIR` | Yes | Absolute path to SadTalker installation |
| `VECTOR_DB_DIR` | Yes | Path for ChromaDB persistence directory |
| `DOCUMENT_UPLOAD_DIR` | Yes | Path for uploaded document storage |

### Backend — Pipeline Service (`backend/.env`)

| Variable | Required | Description |
|---|---|---|
| `AZURE_OPENAI_API_VERSION` | Yes | e.g. `2025-04-14` |
| `AZURE_OPENAI_ENDPOINT` | Yes | Azure OpenAI resource endpoint |
| `AZURE_API_KEY` | Yes | Azure OpenAI API key |
| `AZURE_OPENAI_DEPLOYMENT` | Yes | Azure OpenAI deployment name |
| `AZURE_SPEECH_KEY` | Yes | Azure Speech key |
| `AZURE_SPEECH_REGION` | Yes | Azure Speech region |

<br/>

---

<br/>

# 📡 API Reference

### Frontend API (Express — Port 3000)

All endpoints use Google Gemini via `@google/genai` SDK.

#### `POST /api/generate-roadmap/text`
Generate a learning roadmap graph from a topic.
```json
// Req: { "topic": "Kepler's Laws" }
// Res: { "nodes": [{id, label, description, status}], "edges": [{id, source, target}] }
```

#### `POST /api/generate-roadmap/file`
Generate roadmap from uploaded syllabus file.
- **Type:** `multipart/form-data`, field: `syllabus` (PDF/PNG/JPG, max 10MB)

#### `POST /api/chat`
Topic-aware AI tutor conversation.
```json
// Req: { "topic": "...", "history": [{role, text}], "message": "..." }
// Res: { "text": "..." }
```

#### `POST /api/practice/challenge`
Generate 10 MCQs.
```json
// Res: [{ "question": "...", "options": ["A","B","C","D"], "correctAnswerIndex": 0 }]
```

#### `POST /api/practice/flashcards`
Generate 10 flashcards.
```json
// Res: [{ "front": "...", "back": "..." }]
```

#### `POST /api/practice/listen`
Generate lecture sentences for audio.
```json
// Res: { "sentences": ["..."] }
```

#### `POST /api/practice/tts`
Text-to-speech via Gemini TTS model.
```json
// Req: { "text": "..." }
// Res: { "audioBase64": "..." }  // PCM s16le 24kHz mono
```

#### `POST /api/practice/prove-it`
"Teach the AI" conversational mode. `isEndSession: true` triggers evaluation.
```json
// Req: { "topic": "...", "history": [...], "message": "...", "isEndSession": false }
```

#### `POST /api/practice/wrong-one`
Generate 10 "find the incorrect statement" questions.
```json
// Res: [{ "question": "...", "options": [...], "wrongAnswerIndex": 2, "explanation": "..." }]
```

#### `WebSocket /live?topic=<topic>`
Bidirectional voice conversation with Gemini Live API.
```
Client → Server: { "audio": "<base64 PCM 16kHz>" }
Server → Client: { "audio": "<base64 audio>" } | { "interrupted": true }
```

---

### Backend API (FastAPI — Port 8000)

#### `POST /qa/upload-doc`
Upload a PDF for RAG ingestion.
- **Params:** `chat_id` (optional UUID), file upload
- **Returns:** `document_id`, `chat_id`, `status`, `filename`

#### `POST /qa/ask`
Ask a question with optional document context and video generation.
- **Params:** `chat_id`, `question`, `document_id?`, `video_enabled?`, `face_enabled?`
- **Returns:** `answer`, `video_id?`, `video_status?`

#### `POST /qa/ask-from-image`
OCR + answering from uploaded image.

#### `POST /video/generate`
SadTalker video generation from audio + image.

#### Additional Routers
| Prefix | Router | Description |
|---|---|---|
| `/api/tts` | TTS Router | Text-to-speech endpoints |
| `/api/flashcards` | Flashcard Router | Flashcard generation |
| `/api/quiz` | Quiz Router | Quiz generation |
| `/api/roadmap` | Roadmap Router | CRUD for roadmaps |
| `/api/chat-history` | Chat History Router | Message and chat session management |
| `/api/manim-generator` | Manim Generator | Standalone Manim generation |
| `/api/play/teach-ai` | Teach AI | Document-grounded teaching game |
| `/api/play/find-mistake` | Find Mistake | Error detection game |
| `/api/play/complete-missing-link` | Missing Link | Gap-filling game |

---

### Pipeline Service (FastAPI — Port 8001)

#### `POST /explain`
Run full 5-stage video generation pipeline.
- **Params:** `topic`, `level` (default: `school`), `persona` (default: `teacher`), `face_enabled` (default: `false`)
- **Returns:** `{ "status": "complete", "video_id": "uuid", "video_path": "..." }`

#### `GET /video/{video_id}`
Serve generated video. Returns `404` if not found.

<br/>

---

<br/>

# 📸 Screenshots

> Screenshot assets are in the repository at `Frontend/public/assests/`.

### Homepage & Onboarding

| | |
|---|---|
| **Animated Hero** — Pixel-art "MOOTION" logo built from spring-animated SVG rectangles, followed by a scroll-triggered pixel-art sequence (potion → π symbol → atom). Background grid with decorative scribble SVGs. | ![Hero](Frontend/public/assests/image2.png) |
| **5-Step Onboarding** — Collects name, email, topic preferences (up to 5 from 10 STEM categories), learning style (Visual/Auditory/Reading/Kinesthetic), and learning pace. Progress bar, animated grid background with randomly pulsing cells. |![Onboarding](Frontend/public/read/onboard.png) |

### Workspace Selection & Roadmap

| | |
|---|---|
| **Workspace Selection** — Two entry points: "Study a Topic" (free-text input) or "Upload Syllabus" (drag-and-drop file). | ![Workspace](Frontend/public/read/workspace.png) |
| **Interactive Roadmap** — dagre-layouted directed graph with ~40 concept nodes, zoom/pan controls via React Flow, legend panel (completed/in-progress/up-next), back navigation. | ![Roadmap](Frontend/public/read/road.png) |

### Concept Workspace

| Panel | Feature | Description |
|---|---|---|
| **Left — Visual** | Storyboard | Full-screen Manim video player |
| | Playground | Interactive Kepler 2D orbit simulator (iframe) |
| | Universe | Full 3D solar system with Three.js (iframe) |
| **Center — Chat** | AI Tutor | Topic-aware conversational assistant with message history, animated loading indicators, inline tool suggestion buttons |
| **Right — Practice** | Challenge | Timed 10-question MCQ quiz with progress bar, percentage score, try-again |
| | Flashcards | 3D CSS flip-card interface with shuffle, card count, animate-micro-interactions |
| | Listen | AI-generated TTS audio lecture with play/pause/restart controls |
| | Prove It | Large voice/tap mic button, real-time speech-to-text, session scoring |
| | Wrong One | Identify the incorrect statement, receive explanations |

<br/>

---

<br/>

# 🗺 Project Structure

```
mootion-EvolveAI/
├── Frontend/                              # React + Vite frontend
│   ├── src/
│   │   ├── App.tsx                       # React Router v7 + Home page (pixel-art hero)
│   │   ├── Onboarding.tsx                # 5-step onboarding wizard
│   │   ├── WorkspaceSelection.tsx        # Study vs Syllabus entry
│   │   ├── WorkspaceStudy.tsx            # Topic text input
│   │   ├── WorkspaceSyllabus.tsx         # Syllabus file upload
│   │   ├── Roadmap.tsx                   # ReactFlow concept graph (dagre layout)
│   │   ├── ConceptWorkspace.tsx          # Main workspace (~1104 lines)
│   │   └── LoadingOverlay.tsx            # Animated loading overlay
│   ├── public/
│   │   ├── playground/
│   │   │   └── kepler.html              # 745-line 2D orbit simulator
│   │   ├── universe/
│   │   │   ├── index.html
│   │   │   ├── main.js                  # 3106-line Three.js engine
│   │   │   ├── textures/                # Planet surface textures
│   │   │   └── three.min.js
│   │   └── assests/
│   │       ├── image2.png               # Hero illustration
│   │       └── kepler_final.mp4         # Sample Manim video
│   ├── server.ts                        # Express 4 + Vite + WebSocket server
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   └── .env.example
│
├── backend/
│   ├── app/                              # Pipeline Service (port 8001)
│   │   ├── main.py                      # FastAPI: /explain, /video/{id}
│   │   ├── stages/
│   │   │   ├── stage1_scenes.py         # LLM scene planning
│   │   │   ├── stage2_manim.py          # Manim code gen + render + retry
│   │   │   ├── stage3_script.py         # Narration script gen
│   │   │   ├── stage4_tts.py            # Azure TTS
│   │   │   └── stage5_stitch.py         # Mux + stitch + SadTalker
│   │   ├── utils/
│   │   │   ├── llm.py                   # Azure OpenAI client
│   │   │   ├── generate_uid.py
│   │   │   ├── timestamps_extractor.py   # Manim → timestamp parser
│   │   │   └── json_safe.py             # Safe JSON extraction
│   │   └── prompts/                     # LLM prompt templates
│   │       └── scene_planner.txt, *_manim.txt, etc.
│   │
│   └── backend/                          # API Service (port 8000)
│       └── app/
│           ├── main.py                  # FastAPI with 10 routers
│           ├── core/
│           │   ├── config.py            # Env-based configuration
│           │   ├── database.py          # SQLAlchemy + Neon engine
│           │   ├── models.py            # 5 ORM models
│           │   └── schemas.py           # Pydantic response/request schemas
│           ├── api/
│           │   ├── qa.py                # Q&A + doc upload
│           │   ├── tts.py              # Text-to-speech
│           │   ├── flashcards.py        # Flashcard generation
│           │   ├── quiz.py             # Quiz generation
│           │   ├── roadmap.py           # Roadmap CRUD
│           │   ├── manim_generator.py   # Manim generation
│           │   ├── chat_history.py      # Chat history CRUD
│           │   ├── sad_talker_video.py  # SadTalker endpoint
│           │   └── play/
│           │       ├── teach_ai.py
│           │       ├── find_mistake.py
│           │       └── complete_missing_link.py
│           └── services/
│               ├── document_service.py  # PDF + ChromaDB ingestion
│               ├── qa_service.py        # RAG-based Q&A (Groq)
│               ├── tts_service.py       # Azure TTS
│               ├── sad_talker_service.py # SadTalker subprocess
│               ├── vision_service.py    # Azure Vision OCR
│               ├── chat_service.py      # Chat CRUD
│               └── message_service.py   # Message CRUD + context builder
│
├── .gitignore
├── README.md
└── dontReadMe.md
```

<br/>

---

<br/>

# 🧪 Performance

### Video Generation Pipeline (5 scenes)

| Stage | Avg Time | Model | LLM Retries |
|---|---|---|---|
| Stage 1: Scene Planning | ~8s | Azure OpenAI | 0 |
| Stage 2: Manim Rendering | ~45s/scene | Manim + Azure fix | 0–2 |
| Stage 3: Script Generation | ~6s | Azure OpenAI | 0 |
| Stage 4: TTS | ~3s/scene | Azure Speech (neural) | 0 |
| Stage 5: Stitch + Mux | ~5s | FFmpeg | 0 |
| **Total** | **~4–5 min** | — | — |

### RAG Q&A Pipeline

| Operation | Avg Time |
|---|---|
| PDF Ingestion (10 pages) | ~3s |
| Embedding Generation | ~1.5s |
| Similarity Search (top-12) | ~0.3s |
| Answer Generation (Groq) | ~1.2s |
| **Total Q&A Round-Trip** | **~3–4s** |

### Frontend

| Metric | Value |
|---|---|
| Dev load (Vite HMR) | ~1.5s |
| Prod load (static) | ~0.8s |
| Roadmap dagre layout (~40 nodes) | <50ms |
| Gemini Chat response | ~1–2s |
| Gemini TTS generation | ~2–3s |
| WebSocket audio latency (Live API) | ~500ms–1s |

<br/>

---

<br/>

# 👥 Team — Evolve AI

Built for **AI4India hackathon** by four students targeting 250 million STEM learners in India.

| Name | Role |
|---|---|
| **Rachit Goyal** | Systems Architect & Backend — core framework design and backend orchestration |
| **Poorvika Grover** | Design & UX Lead — end-to-end visual identity and user journey |
| **Goyam Jain** | Lead ML Engineer — AI development and model optimization |
| **Sartaj Kaur** | Product Lead & Strategy — product vision, roadmap, and user-centric execution |

### Target Users

- **Arjun** — B.Tech student who struggles with passive, text-based learning and needs instant visual explanations
- **Riya** — B.Sc student with access to content but no structured study path or topic dependency map
- **Kabir** — JEE aspirant who understands concepts during study but cannot retain them without active practice

### Anticipated Impact

| Metric | Estimate |
|---|---|
| Concept understanding speed | 2–3× faster |
| Retention through interactive practice | 40–60% improvement |
| Platform-switching overhead | Eliminated |

<br/>

---

<br/>

# 🛣 Roadmap

### Short-Term

- [ ] **User authentication** — JWT-based login/session management
- [ ] **Progress persistence** — Database-backed user progress across sessions
- [ ] **Docker Compose** — Single-command startup for all 3 services
- [ ] **Syllabus OCR pipeline** — Actual document parsing for syllabus roadmap generation

### Medium-Term

- [ ] **Multi-language support** — UI i18n + multi-lingual AI tutor
- [ ] **Learning analytics** — Track patterns, identify weak areas, recommend content
- [ ] **Spaced repetition** — Integrate with flashcard system for optimal recall
- [ ] **Collaborative workspaces** — Real-time shared learning sessions
- [ ] **Mobile responsive** — Full mobile concept workspace

### Long-Term

- [ ] **Custom avatars** — Personalized SadTalker talking heads
- [ ] **PWA offline mode** — Cached roadmaps with local AI inference
- [ ] **Community roadmaps** — User-generated and shared learning paths
- [ ] **Code playground** — In-browser IDE for CS/Programming topics
- [ ] **Adaptive difficulty** — AI adjusts content based on learner performance metrics

<br/>

---

<br/>

# ❓ Troubleshooting

### Frontend

| Issue | Likely Cause | Solution |
|---|---|---|
| Speech recognition not supported | Non-Chromium browser | Use Chrome or Edge |
| Gemini API 429 | Rate limit exceeded | Wait or use your own key with higher quota |
| Roadmap shows generic nodes | AI generation failed | Check network tab; server falls back to generic structure |
| WebSocket disconnects | Network or invalid key | Verify `GEMINI_API_KEY` has Live API access |
| TTS audio not playing | Autoplay policy blocked | User interaction must trigger first audio |

### Backend — API Service

| Issue | Likely Cause | Solution |
|---|---|---|
| Chat not found | Invalid/missing `chat_id` | Create chat via chat history API first |
| ChromaDB collection empty | Document ingestion failed | Verify PDF readability by PyPDFLoader |
| "I don't know" responses | No relevant docs found | Lower similarity threshold in `qa_service.py` (currently 0.6) |
| `face_enabled` requires `video_enabled` | Validation mismatch | Set both flags `true` |

### Backend — Pipeline Service

| Issue | Likely Cause | Solution |
|---|---|---|
| Manim rendering fails | Invalid Manim code | LLM auto-fix triggers (up to 2 retries); inspect outputs/animation.py |
| Video not found | Pipeline incomplete | Check `outputs/videos/<video_id>/final.mp4` |
| Missing audio/video | Scene ID mismatch | Verify scene IDs match across stages 2–5 |
| SadTalker not processing | Missing dependencies | Ensure SadTalker + GFPGAN installed at `SADTALKER_DIR` |

<br/>

---

<br/>

# 🤝 Contributing

1. **Fork** the repository
2. **Create a branch:** `git checkout -b feat/amazing-feature`
3. **Commit:** `git commit -m "feat: add amazing feature"`
4. **Push:** `git push origin feat/amazing-feature`
5. **Open a Pull Request**

### Commit Convention

Follows [Conventional Commits](https://www.conventionalcommits.org/):

| Prefix | Use Case |
|---|---|
| `feat:` | New feature |
| `fix:` | Bug fix |
| `refactor:` | Code restructuring |
| `perf:` | Performance |
| `docs:` | Documentation |
| `chore:` | Maintenance, deps, tooling |

### Guidelines

- Frontend: `npm run lint` (`tsc --noEmit`) before committing
- Backend: No circular imports; update Pydantic schemas with API changes
- Pipeline: Maintain backward compatibility with existing video IDs
- All new features should include corresponding UI or API documentation

<br/>

---

<br/>

# 📄 License

Distributed under the **Apache 2.0 License**. See `LICENSE` for more information.

---

# 🙏 Acknowledgments

- **[Google Gemini](https://deepmind.google/technologies/gemini/)** — AI models for chat, TTS, quizzes, roadmaps, and Live API
- **[Manim](https://www.manim.community/)** — 3Blue1Brown's math animation engine
- **[Three.js](https://threejs.org/)** — 3D rendering for the solar system
- **[React Flow](https://reactflow.dev/)** — Interactive graph visualization
- **[FastAPI](https://fastapi.tiangolo.com/)** — High-performance Python API framework
- **[Groq](https://groq.com/)** — Ultra-fast LLM inference for RAG
- **[ChromaDB](https://www.trychroma.com/)** — Open-source vector database
- **[SadTalker](https://github.com/OpenTalker/SadTalker)** — Talking-head animation system
- **[Motion](https://motion.dev/)** — Animation library for React
- **[Tailwind CSS](https://tailwindcss.com/)** — Utility-first CSS framework
- **[Neon](https://neon.tech/)** — Serverless PostgreSQL

---

<br/>

# 👥 Team — Evolve AI

Built for the **AI4India Hackathon 2026**, targeting 250 million STEM learners in India.

| | Name | Role |
|---|---|---|
| <img src="https://ui-avatars.com/api/?name=Rachit+Goyal&background=1a1a1a&color=fff&size=40" width="40" style="border-radius:8px"/> | **Rachit Goyal** | Systems Architect & Backend — core framework design and backend orchestration |
| <img src="https://ui-avatars.com/api/?name=Poorvika+Grover&background=2d2d2d&color=fff&size=40" width="40" style="border-radius:8px"/> | **Poorvika Grover** | Design & UX Lead — end-to-end visual identity and user journey |
| <img src="https://ui-avatars.com/api/?name=Goyam+Jain&background=3a3a3a&color=fff&size=40" width="40" style="border-radius:8px"/> | **Goyam Jain** | Lead ML Engineer — AI development and model optimisation |
| <img src="https://ui-avatars.com/api/?name=Sartaj+Kaur&background=4a4a4a&color=fff&size=40" width="40" style="border-radius:8px"/> | **Sartaj Kaur** | Product Lead & Strategy — product vision, roadmap, and user-centric execution |

<br/>

---

<p align="center">
  <sub>© 2026 MOOTION Studio — AI4India Hackathon 2026</sub>
</p>
