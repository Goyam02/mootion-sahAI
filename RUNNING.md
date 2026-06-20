# Mootion Service Execution Guide

This document describes how to configure, bootstrap, and run all components of the Mootion platform for local development.

---

## 🔑 Environment Configuration (`.env`)

Mootion expects environment configuration files in specific folders for different services:

1. **Backend (`/backend/.env`)**:
   - Stores the database URL, OpenAI/Azure credentials, R2/MinIO storage details, and OAuth parameters.
   - *Status*: The root `.env` has been successfully copied to `/backend/.env` for you.

2. **Frontend (`/frontend/.env`)**:
   - Stores the `GEMINI_API_KEY` for the live real-time voice chatbot WebSocket proxy.
   - *Status*: A `.env` already exists in `/frontend/` with your Gemini key.

---

## 🚀 Execution Steps

### 1. Start Support Services
Make sure you have **Redis** running locally (e.g. via Docker, WSL, or native service):
```bash
# Example if using docker:
docker run -d --name redis-local -p 6379:6379 redis:7-alpine
```

---

### 2. Run the Backend (`mootion-backend`)
1. Open a terminal in the `/backend/` directory.
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the database migrations (optional, or it will bootstrap automatically):
   ```bash
   python migration.py
   ```
4. Seed the NCERT curriculum chapters and create the default teacher user (`abc`/`abc`):
   ```bash
   python seed_ncert.py
   ```
5. Start the FastAPI application:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```
   *Note: Access swagger docs at http://localhost:8000/docs*

---

### 3. Run the Media worker
The media worker handles background rendering of Manim videos, 3D models, and quizzes from assignments.
1. Open a second terminal in the `/backend/` directory.
2. Run the worker process:
   ```bash
   python -m app.services.media_worker
   ```

---

### 4. Run the Animation Engine (Optional, for Manim videos)
1. Open a terminal in the `/animation-engine/` directory.
2. Install requirements and run the FastAPI server:
   ```bash
   pip install -r requirements.txt
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
   ```

---

### 5. Run the Frontend (`mootion-frontend`)
1. Open a terminal in the `/frontend/` directory.
2. Install Node dependencies:
   ```bash
   npm install
   ```
3. Run the development server (which spins up the React Vite app + the Gemini WebSocket voice proxy):
   ```bash
   npm run dev
   ```
4. Open [http://localhost:3000](http://localhost:3000) in your browser.
