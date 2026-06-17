1. Start services
- brew services start redis
- brew services start minio or minio server ~/minio-data --console-address ":9000"
- uvicorn app.main:app --reload --host 0.0.0.0 --port 8001 in animation-engine/
- uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 in backend/
- python -m app.services.media_worker in a second backend/ terminal
2. Set backend env vars
- REDIS_URL=redis://localhost:6379/0
- MINIO_ENDPOINT=localhost:9000
- MINIO_ACCESS_KEY=minioadmin
- MINIO_SECRET_KEY=minioadmin
- MINIO_SECURE=false
- MINIO_MEDIA_BUCKET=mootion-media
- BACKEND_PUBLIC_URL=http://localhost:8000
- MANIM_SERVICE_BASE_URL=http://localhost:8001
- MANIM_SERVICE_URL=http://localhost:8001/explain
3. Create a teacher, class, curriculum, and chapters
- Register/login as a teacher.
- Create a class.
- Bootstrap curriculum.
- Bootstrap chapters.
- Confirm GET /teachers/classes/{class_id}/chapters returns chapters with assets.
4. Trigger a video job
- Create an assignment with assignment_type=video.
- Confirm the assignment is created immediately with status=queued.
- Confirm a chapter_asset_generation_jobs row exists in the backend DB.
- Confirm the worker terminal picks up the job.
5. Verify the generated video
- Wait for the worker to finish.
- Call GET /teachers/classes/{class_id}/chapters/{chapter_id}.
- Confirm the concept video asset now has:
  - generation_status=ready
  - external_url pointing to http://localhost:8000/media/assets/{asset_id}
6. Open playback
- Visit the returned external_url in the browser.
- It should stream the MP4 from MinIO through the backend.
7. Check MinIO directly
- Open MinIO console at http://localhost:9000.
- Confirm the object exists in bucket mootion-media.
8. Test recovery
- Stop the worker while a job is queued.
- Restart the worker.
- Confirm queued jobs are picked up from Redis/DB and continue.