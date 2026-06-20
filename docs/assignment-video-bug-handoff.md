# Mootion — Assignment / Video Generation Bug: Full Context & Investigation History

**Purpose of this document:** The codebase has been reset via `git stash` to its
state before today's debugging session — none of the fixes described below
currently exist in the code. This document exists so that whoever picks this
up next (a different AI model, a different person) does not repeat the same
investigation from scratch, does not re-discover the same dead ends, and
starts from the most promising remaining lead instead of the beginning.

Read this alongside the other research docs (`frontend-research.md`,
`backend-api-endpoints-and-models.md`, `backend-business-logic-and-services.md`)
already produced for this project — this document assumes familiarity with
the API/model structure described there but restates the most relevant parts
inline for convenience.

---

## Part 1 — What Is Mootion

Mootion is an EdTech platform built for a hackathon (Wadhwani AI SahAI
Hackathon, Track 2, Phase 2), targeting **government school students in
India (Classes 6–12)** and their STEM teachers.

**The core problem it addresses:** teachers at classroom scale cannot tell
genuine conceptual understanding apart from surface-level memorization —
the "missing signal" problem.

**The core mechanism:** AI-driven voice conversations (Gemini voice API)
where a student explains a concept back to an AI (the Feynman technique).
This produces misconception-specific understanding signals that populate a
teacher dashboard. This mirrors Wadhwani AI's existing ORF/Vaachan Samiksha
architecture: voice-first, teacher-enablement, measurable signals at
government-school scale.

**Deployment model:** Teacher assigns a task (a chapter/topic activity) to
a class. Students complete it at home on a smartphone via a mobile-first PWA.
Teachers use a web/PWA dashboard. Two roles, two separate logins
(teacher, student).

**Key design principle (from mentor Sharanya Sharma, Wadhwani AI):** *the
nudge to use the product must come from the product itself, not the teacher
forcing the student.* This governs all student-facing copy and UX — e.g.
notifications should read "A new chapter is ready for you," never "Your
teacher assigned you work."

**MVP activity priority:** "Explain It" (Feynman/Teach the AI) and "Predict
It" (Predict-Observe-Explain) are highest priority. "Spot It" and "Connect
It" follow. "Fix It," "Prove It," "Analogize It" are post-MVP.

**Scope decision:** Class 5 was briefly supported, then deliberately removed
— the product is scoped to **Grades 6–12 only** for this submission (NCERT
doesn't actually teach a separate "Science" subject in Class 5; it's EVS,
which only splits into Science/Social Science from Class 6). This is
unrelated to the bug in this document — mentioned only so it isn't
mistaken for part of the same issue if grade-5 references are seen anywhere.

**Content generation pipeline:** the backend auto-generates concept
explanation videos using a self-hosted Manim microservice, ffmpeg, LaTeX,
and TTS, with a separate RAG system (ChromaDB, NCERT-syllabus-grounded)
providing context to the generation prompt. Generated videos are uploaded
to Cloudflare R2 (S3-compatible) for delivery.

**Stack:** FastAPI backend (`backend/`), Next.js/React frontend
(`frontend/`), separate Manim video-generation microservice (runs on
`localhost:8001` in dev), Redis (job queue), Cloudflare R2 (media storage).

---

## Part 2 — Architecture Relevant to This Bug

### Data model (relevant subset)

```
ClassRoom (grade, subject)
  └── Chapter (title, belongs to one ClassRoom)
        └── ChapterAsset (asset_type, provider, generation_status,
                           external_url, storage_bucket, storage_key,
                           payload_json)
              └── ChapterAssetGenerationJob (status, asset_id,
                                              assignment_id, result_json)

Assignment (class_id, chapter_id, assignment_type, title, status,
            content_json)
  ├── AssignmentRecipient (student_id) — one per enrolled student
  └── ChapterAssetGenerationJob (one or more, via assignment_id FK)
```

Important structural fact: **`AssignmentCreateRequest` only carries
`chapter_id`, not a `topic_id`.** Assignments are created at
**chapter granularity**. If a chapter has multiple topics, and multiple
`ChapterAsset` rows of the same `asset_type` exist under that chapter
(e.g. one per topic), the assignment-creation logic has no way to
disambiguate which one belongs to "the video the teacher just generated."
**This may be directly relevant to the still-unresolved bug below.**

### Two ways a video gets generated

1. **Direct/synchronous generation** (teacher-initiated, from the
   chapter-setup page): `POST /teachers/classes/{class_id}/chapters/{chapter_id}/assets/{asset_id}/generate`.
   This blocks the HTTP request for up to 300s and returns only once the
   video is fully done. No job row involved in this path historically.

2. **Assignment-triggered generation** (when a teacher clicks "Assign to
   Class"): `POST /teachers/classes/{class_id}/assignments` →
   `create_teacher_assignment` (in `assignment_service.py`) →
   `_create_generation_jobs`. This function is supposed to find the
   chapter's matching `ChapterAsset` rows (by `asset_type`, derived from
   `assignment_type` via a fixed mapping) and create
   `ChapterAssetGenerationJob` rows for any that aren't already generated
   — which are then enqueued to Redis and picked up by a worker that calls
   the Manim service.

### Job queue / stale recovery

`media_queue.py` has an `enqueue_pending_media_jobs()` function that runs
**on every app/worker startup** (`@app.on_event("startup")` in `main.py`).
It does two things:
- Re-queues jobs stuck in `"processing"` for more than
  `media_job_stale_timeout_minutes` (default 120 min) back to `"queued"`.
- Re-enqueues any job still sitting at `"queued"` status to Redis.

This function runs **independently of any assignment-creation logic** and
was a major source of confusion today (see Round 4 below) — it can
re-trigger real generation for old job rows with no connection to whatever
the teacher is currently doing.

---

## Part 3 — The Bug: Chronological Symptom History

This bug changed shape multiple times over one debugging session. Each
round below describes the symptom observed, what was found, what was
(temporarily) fixed, and — critically — whether that fix actually held.

### Round 1 (never fully confirmed resolved)
**Symptom:** After a teacher generated a video on the chapter-setup page,
revisiting that same page showed the video as "generating" again — even
though it had already been viewed and assigned. Logging out and back in
"fixed" the display.
**Working hypothesis at the time:** since direct generation
(`/assets/{asset_id}/generate`) is synchronous and blocks until done, the
backend wouldn't itself return "still generating" after completion — so
this was suspected to be a **frontend stale-cache issue**: the chapter
detail page wasn't re-fetching fresh data on revisit, and a full
logout/login forces a clean refetch.
**Status:** This was handed off as an investigation prompt but the
conversation moved on to other bugs before a confirmed root cause was
reported back. **This may still be present and is worth re-checking
independently of everything below.**

### Round 2 — "Assign to Class" re-generates an already-ready video
**Symptom:** Teacher generates a video (asset becomes `ready`). Teacher
clicks "Assign to Class." Manim service logs show the video being
generated again from scratch. Student dashboard shows the task as
"preparing" indefinitely, even though a finished video already existed.
**Root cause found (confirmed):** `_create_generation_jobs` in
`assignment_service.py` had **no guard** against assets that were already
`generation_status == "ready"`. It unconditionally created a new
`ChapterAssetGenerationJob` for any matching asset with
`provider ∈ {manim, model_finder, quiz_generator, simulation}`, regardless
of whether that asset already had a valid `external_url`.
**Fix applied (verified correct via direct code review):**
- Added a fast-path: if `asset.generation_status == "ready"`, skip job
  creation entirely, and instead build the assignment's `content_json`
  directly from the existing asset (helper: `_build_content_json_from_asset`,
  which pulls `resolve_asset_media_url(asset)` into `content_json["external_url"]`).
- `created` stays `0` in that case, so the assignment's status logic
  immediately sets `assignment.status = "ready"`.

### Round 3 — Backend confirmed fixed, but student still saw "preparing" + wrong field name
**Symptom:** After Round 2's fix, Manim logs confirmed no new generation
was happening — but the student dashboard still showed "preparing."
**Two separate causes found (confirmed via direct code review):**
1. **Stale fetch:** `StudentTasksPage.tsx` was reading a cached/stale
   `"queued"` snapshot from milliseconds after assignment creation (raw
   `fetch` inside `useEffect`, no data-fetching framework, so the browser's
   native fetch cache was serving a stale 200 response).
   **Fix applied:** added `'Cache-Control': 'no-cache'` globally to all
   requests in `frontend/src/lib/api.ts`. (Note: this is a **global**
   behavior change, not scoped to this one endpoint — acceptable tradeoff
   given the deadline, but worth knowing if anything else feels slower
   than expected later.)
2. **Key mismatch / wrong fallback (a real bug that would have caused a
   404 even after the stale-fetch fix):** `StudentTaskActivityPage.tsx`'s
   `VideoSimulationContent` component was **ignoring**
   `content_json.external_url` entirely. It instead tried:
   ```js
   const mainJob = (task as any).dbTask?.jobs?.[0];
   const assetId = mainJob?.asset_id || task.id;
   const mediaUrl = `${getBackendBaseUrl()}/media/assets/${assetId}`;
   ```
   Because Round 2's fast-path legitimately produces an **empty `jobs`
   array** (no job was ever created for an already-ready asset),
   `mainJob` was `undefined`, and it fell back to `task.id` — which is the
   **assignment ID, not the asset ID** — producing a 404 against
   `/media/assets/{assignment_id}`.
   **Fix applied (confirmed present in the file when directly reviewed
   later):** prioritize `content_json.external_url` (then
   `content_json.embedUrl`) as the primary media source; only fall back
   to the `jobs[0].asset_id` construction when both are absent.

### Round 4 — Videos STILL regenerating; root cause was a third, separate code path
**Symptom:** Despite Round 2 and 3's fixes both being independently
verified correct by direct code review, a *new* topic's video was still
being generated a second time, per Manim service logs.
**Root cause found (confirmed):** `enqueue_pending_media_jobs()` in
`media_queue.py` (see Part 2 above) — the startup/stale-recovery
mechanism — re-queues jobs with **zero check on the underlying asset's
status**. It only looks at the job row's own age/status. A job stuck in
`"processing"` from an earlier crashed/interrupted attempt (very plausible
after a day of repeated manual testing, a 500 error, etc.) would get
silently reset to `"queued"` and re-enqueued **completely bypassing every
guard added to `_create_generation_jobs`**, because this path never calls
that function.
**Direct evidence found:** a specific job (`a42545e4`) was stuck in
`status=queued` since 08:39 UTC pointing at an asset that was already
`generation_status=ready`. Another job was found that had literally
re-run **20 hours after** its original `queued` timestamp — past the
120-minute stale threshold — consistent with a server restart triggering
`enqueue_pending_media_jobs()`.
**Fix applied (confirmed via direct code review of the final file):**
both loops inside `enqueue_pending_media_jobs` (stale-`processing` recovery,
and the plain `queued` re-enqueue loop) were changed to check
`asset.generation_status == "ready"` before re-queueing — if ready, mark
the job `"ready"`/superseded instead of re-running it.
A second defense layer was also added directly in the worker's entry
point, `process_generation_job` (in `assignment_service.py`): it now
short-circuits and marks the job `"ready"` immediately if
`asset.generation_status == "ready"`, **before** making any real call to
the Manim service — a last-line-of-defense check regardless of how the
job got enqueued.

### Round 5 — Orphaned assignment rows (a side effect of manual debugging, not new app logic)
**Symptom:** One specific assignment was *still* stuck showing "preparing"
even after all of Round 2–4's fixes were verified correct.
**Root cause found (confirmed via direct DB query):** the assignment's
`.status` column was literally `"queued"` in the DB, with
`content_json` still the original placeholder
(`{"placeholder": true, ...}`) — **despite** the underlying `ChapterAsset`
being `generation_status="ready"` and its associated job already marked
`status="ready"`.
This was traced to the manual debugging process itself: earlier
cleanup/diagnostic scripts (run directly against the DB during today's
investigation) had set `job.status = 'ready'` / `error_message =
'Superseded...'` directly on stuck job rows, **without** ever calling
`_refresh_assignment_status()` afterward. `enqueue_pending_media_jobs()`
(before its Round 4 fix) had the identical flaw. The result: the
assignment row was abandoned — its job said "done," but nothing ever told
the *assignment* to update.
**Fix applied:**
- A one-time retroactive script (`refresh_stale_assignments.py`) queried
  all assignments stuck in `"queued"`/`"processing"` and force-ran
  `_refresh_assignment_status()` on each.
- `enqueue_pending_media_jobs()` was further patched so that whenever it
  marks a job as superseded/ready, it now collects the affected
  `assignment_id`s into a set and calls `_refresh_assignment_status()` for
  each, **after** the main loop's `db.commit()` (to avoid nested-commit
  issues, since that function does its own commit).
- A diagnostic scan for any other orphaned assignments (status
  `queued`/`processing` with all jobs `ready`/`failed`) came back empty —
  confirmed no further leftover bad data at that point.

### Round 6 — UNRESOLVED: wrong video shown, silent re-generation, no "preparing" UI at all
**Symptom (most recent, NOT resolved before the code was reset):** A
fresh topic was generated and assigned. This time:
- The student dashboard did **not** show a "preparing" badge at all (the
  UI that Round 3 confirmed was working correctly for the `queued`/
  `processing` case did not appear).
- The Manim service logs showed a **new generation running** anyway, with
  no visible trigger from the frontend.
- **The video that ended up showing on the student's dashboard was a
  different video than the one the teacher had just generated.**

This is a materially different symptom from every previous round — it's
not a status-sync delay, it's an **identity/matching problem**: something
is associating this assignment with the wrong chapter, topic, or asset
entirely.

**Leading hypothesis (not yet confirmed with hard evidence):** duplicate
`Chapter` rows. Per project history, curriculum bootstrap
(`GET /curriculum` → `POST /bootstrap` if empty → `GET /chapters`) is
called independently from **both** teacher and student page loads. If this
isn't strictly idempotent/transactional, two near-simultaneous bootstrap
calls for the same class (e.g. teacher loads class detail at the same
moment a student happens to load their dashboard) could create **two
`Chapter` rows with the same title**, each with its own separate set of
`ChapterAsset` rows. The teacher could be generating/viewing under one
`Chapter` row while the assignment (or the asset-matching logic) operates
on a *different* duplicate row — explaining both a different video and a
fresh, unguarded generation (since the duplicate's asset genuinely isn't
ready yet, none of Rounds 2–5's guards are wrong, they just don't apply to
*this* asset).

**Alternative hypothesis:** no duplicate chapters, but multiple
`ChapterAsset` rows of the *same* `asset_type` under one chapter (e.g. one
per topic, left over from earlier testing) — combined with the structural
fact noted in Part 2 that `_create_generation_jobs` matches assets by
`chapter_id` + `asset_type` only, with **no topic-level scoping** at all
(because `AssignmentCreateRequest` never carries a `topic_id`). If a
chapter has more than one video-type asset, the loop in
`_create_generation_jobs` (`for asset in assets: ...`) could pick up *any*
matching row — not necessarily the one the teacher just generated — and
either show its (different) `external_url` if it happens to already be
ready, or queue a fresh generation for it if not.

**This was never confirmed with hard evidence (exact chapter_ids, exact
asset_ids, a direct count of duplicate rows) before the code was reset.**
This is the single most important thing to investigate first when picking
this back up.

---

## Part 4 — Confirmed Facts (Ground Truth, Independent of Hypotheses)

These were established via direct reading of the actual files (not agent
self-reports) at various points today, and via direct DB queries. They
describe the **patched** state from Rounds 2–5 — since the code has been
reset, assume these specific guards are **absent** again unless
re-implemented, but the underlying *facts about how the system is wired*
remain true:

- `Assignment.content_json` is a freeform JSON blob populated either by
  `_build_content_json_from_asset` (fast-path) or
  `_rebuild_content_json_from_jobs` (post-job-completion path). Its field
  for video URLs is `external_url`; for 3D models it's `embedUrl`; for
  quizzes it's `quiz`.
- `media_service.py`'s `resolve_asset_media_url(asset)` returns either a
  presigned R2 URL (`presigned_media_url`, which **may expire** — this was
  noticed but never investigated further; presigned URLs expiring with
  nothing to refresh them is a plausible independent cause of "stuck
  preparing"-like symptoms and should not be ruled out) or a constructed
  simulation HTML URL, or the raw `external_url` as a last resort.
- `GET /students/classes/{class_id}/assignments` (backing the student
  tasks list) returns the `Assignment.status` column directly, with no
  independent derivation logic of its own (confirmed by direct review of
  `assignment_repository.py`'s backing query at the time).
- `StudentTasksPage.tsx` and `StudentTaskActivityPage.tsx`, **as
  patched**, contained no remaining bugs in status-reading or
  media-URL-resolution logic — both correctly read `status` and
  `content_json.external_url` directly with no caching issues, once the
  `Cache-Control: no-cache` header was added globally.
- The note above means: **if "stuck preparing" or "wrong video" symptoms
  recur, the bug is almost certainly NOT in these two frontend files**
  (assuming whatever fix is reapplied matches what's described in Part 3) —
  look at the backend's matching/identity logic instead.

---

## Part 5 — Validated Fix Patterns (Reference Only — Re-Implement From Scratch)

The following describes the **shape** of the fixes that were verified
correct today. Exact line numbers will differ in the reset codebase — use
these as a design reference, not a literal patch.

**In `assignment_service.py`, inside the asset-matching loop of
`_create_generation_jobs`:**
```python
if asset.generation_status == "ready":
    assignment.content_json = _build_content_json_from_asset(assignment, chapter, asset)
    continue  # no job created; caller sets assignment.status = "ready"

if asset.generation_status in ("queued", "processing"):
    continue  # don't create a duplicate job; don't overwrite a job in flight
```

**In `process_generation_job` (the worker's entry point), before doing any
real generation work:**
```python
if asset.generation_status == "ready":
    job.status = "ready"
    job.error_message = "Superseded: asset already ready"
    job.finished_at = datetime.now(timezone.utc)
    db.commit()
    return
```

**In `media_queue.py`'s `enqueue_pending_media_jobs`, in both the
stale-`processing` loop and the plain `queued` loop:** check the
underlying asset's status before re-queueing; if ready, mark the job
superseded instead — **and** collect affected `assignment_id`s to call
`_refresh_assignment_status()` on each, after the main commit:
```python
assignments_to_refresh = set()
# ...inside each loop, when marking a job superseded:
assignments_to_refresh.add(str(job.assignment_id))
# ...after db.commit():
for assignment_id in assignments_to_refresh:
    _refresh_assignment_status(db, assignment_id)
```

**In `StudentTaskActivityPage.tsx`'s `VideoSimulationContent`:**
prioritize `content_json.external_url` / `content_json.embedUrl` over any
`jobs[0].asset_id`-based fallback construction.

**In `frontend/src/lib/api.ts`:** global `Cache-Control: no-cache` header
fixed a stale-fetch symptom, at the cost of disabling browser HTTP caching
for all requests through this client (acceptable tradeoff noted, not
re-evaluated since).

---

## Part 6 — Recommended Strategy For Whoever Picks This Up

**Do not repeat today's mistake of patching each new symptom in
isolation.** Every round above was a *correct* fix for what it found, and
the bug still kept coming back in a new shape — because each fix addressed
one mechanism without checking whether a structurally different mechanism
could produce the same-looking symptom. The actual lesson from today: this
codebase has **at least four independent code paths** that can create or
touch a `ChapterAssetGenerationJob` (assignment creation, the worker's
process loop, stale-job recovery, and possibly manual/admin scripts) — any
fix must be checked against all of them, not just the one currently being
debugged.

**Recommended order of operations:**

1. **Before writing any fix, get hard IDs for Round 6's "wrong video"
   bug.** Specifically: the `chapter_id` the teacher generated under
   (visible in the chapter-setup URL), the `chapter_id` stored on the
   resulting `Assignment` row, and a direct query for `Chapter` rows
   sharing the same `class_id` + `title`. This single check will confirm
   or rule out the duplicate-chapter hypothesis in under a minute and
   should happen first, before touching any code.
2. If duplicates are confirmed: fix the curriculum bootstrap flow's
   idempotency (likely needs a DB-level unique constraint on
   `(class_id, title)` for `Chapter`, or a transaction/lock around the
   "if no chapters exist, bootstrap" check, to close the race window
   between teacher-side and student-side bootstrap calls).
3. If no duplicates: investigate whether multiple `ChapterAsset` rows of
   the same `asset_type` exist under one chapter, and whether
   `_create_generation_jobs`/asset-matching needs topic-level scoping
   that doesn't currently exist in `AssignmentCreateRequest`.
4. Once the *matching* bug is fixed, re-apply (cleanly, all at once, not
   incrementally) the four guards described in Part 5 — they were each
   independently verified correct and should not need to be
   re-discovered, only re-implemented.
5. Re-check Round 1 (chapter-setup page showing stale "generating" on
   revisit) — this was never confirmed fixed and may still be present
   independently of everything else.
6. Investigate the presigned-URL-expiry note in Part 4 — if
   `resolve_asset_media_url` returns an expiring presigned URL and
   nothing refreshes it, this could cause a *new* "video won't load"
   symptom later that looks similar to "stuck preparing" but has a
   completely different cause.
7. **After any fix, test the full teacher-generates → assigns → student-
   watches loop manually, end to end, with a brand-new topic that has no
   debugging history** — not a repaired/patched older row. This is the
   actual judge-facing demo path and the one thing that was never cleanly
   verified today.

---

## Part 7 — Constraints For Whoever Implements This

- Backend changes should be kept minimal — prefer fixing root cause in the
  smallest number of files over broad refactors, given the hackathon
  deadline.
- No code from today's debugging session was committed to git — the
  repository is at (or very near) its pre-session state. Do not assume any
  of Part 5's patterns already exist; verify by reading the current files
  directly first.
- Frontend calls route through `frontend/src/lib/api.ts`; avoid
  introducing new direct `fetch`/`EventSource` calls that bypass it unless
  there's a specific reason (e.g. SSE, FormData uploads) — this codebase
  already has some components that bypass this wrapper, and it's a known
  source of inconsistent behavior, not something to add to.
- Time is extremely limited (hackathon deadline). Prioritize Part 6's
  ordered steps strictly — getting hard evidence first (step 1) is the
  highest-leverage thing that can be done before any further code changes.
