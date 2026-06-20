# Mootion Frontend Research

Source: automated codebase audit of `frontend/` (React + Vite, with an Express.js BFF in `server.ts` proxying to the FastAPI backend). Covers all teacher pages, student pages, and supporting components/data/server files.

---

## 1. Routing & Auth

### Route Guarding — `ProtectedRoute.tsx` (56 lines)

- Reads `mootion_access_token` and `mootion_role` from `localStorage`.
- No token + role `student` → redirect to `/login`. No token + role `teacher` → redirect to `/teacher/login`. No token + no role → redirect to `/login`.
- `LoginRoute` redirects already-authenticated users away from login pages: teacher → `/teacher/home`, student → `/student/home`.
- **Gap:** no role-mismatch handling — a student with a valid token can pass through a teacher-only route if they navigate there directly.

### Navigation Map

```
/                     → LandingPage → /onboarding or /teacher/login
/onboarding           → /signup/student or /teacher/login
/student/*            → guarded by ProtectedRoute (role: student)
/teacher/*            → guarded by ProtectedRoute (role: teacher)
```

---

## 2. Auth & Onboarding Flows

### Student Login — `StudentLoginPage.tsx` (182 lines)
- `POST /auth/student/request-otp { phone }` → `POST /auth/student/verify-otp { phone, otp }`.
- On success, stores `mootion_access_token`, `mootion_refresh_token`, `mootion_role='student'`, `mootion_student_id`, `mootion_student_name` in `localStorage`; navigates to `/student/home`.
- Two-step UI: phone entry → OTP entry.

### Student Signup — `StudentSignupPage.tsx` (472 lines)
- `POST /auth/student/signup { name, phone, class_number, section, school_code }` then `POST /auth/student/verify-otp { phone, otp }`.
- Form collects name, phone, class (6–12), section (A–F), and a school code (helper text: "Ask your teacher for this code").
- Same `localStorage` auth pattern as login; navigates to `/student/home`.

### Teacher Login — `TeacherLoginPage.tsx` (210 lines)
- `POST /auth/teacher/login { email, password }`. Response includes `onboarding_complete` flag.
- Routes to `/teacher/onboarding` if incomplete, else `/teacher/home`.
- Stores the same auth keys as student, teacher-prefixed (`mootion_teacher_id`, `mootion_teacher_name`).

### Teacher Onboarding — `TeacherOnboardingPage.tsx` (650 lines)
- 4-step wizard: Profile → Add Subjects → Add Classes → Add Students → Review (forward-only, no back navigation between steps).
- Nested payload: `subjects[]` → each with `classes[]` → each with `students[]` (`name`, `parent_phone`).
- `POST /auth/teacher/onboard` with the full nested payload; navigates to `/teacher/home` on success.

---

## 3. Teacher-Facing Pages

### Dashboard — `TeacherDashboardPage.tsx` (540 lines)
- `GET /teacher/classes` on mount → class cards (`subject`, `class_number`, `section`, `student_count`).
- Bottom nav: Home, Broadcast, Doubts, Analytics, Profile/Logout.
- **Mock data:** "Recent Activity" section (3 static items, e.g. "New doubt from Rahul in Math") is hardcoded, not fetched.

### Class Detail — `TeacherClassViewPage.tsx` (680 lines)
- `GET /teacher/class/{id}` and `GET /teacher/class/{id}/chapters` on mount.
- Two tabs: Curriculum (chapter list, inline "Add Chapter" → `POST /teacher/class/{id}/chapters`) and Students (name + status list).
- **Gap:** student "status" shown as static "Active" — no real engagement/activity data from backend.

### Chapter Setup — `TeacherChapterSetupPage.tsx` (1,380 lines)
- Full CRUD on topics within a chapter:
  - `GET /teacher/class/{classId}/chapter/{chapterId}`
  - `GET .../topics`, `POST .../topics` (create), `DELETE .../topics/{topicId}`
  - `PUT .../chapter/{chapterId}` (title edit)
  - `POST .../chapter/{chapterId}/publish` (one-way — no unpublish)
- No drag-to-reorder for topics.

### Topic Setup — `TeacherTopicSetupPage.tsx` (1,250 lines)
- `GET` topic detail, `PUT` to update, `POST .../content` to add a content block, `DELETE .../content/{contentId}`.
- `POST .../topic/{topicId}/generate { prompt }` — AI content generation, with a "Generate with AI ✨" UI and loading state.
- Supports content block types: text, video, quiz, interactive. No block reordering.

### Broadcast — `TeacherBroadcastPage.tsx` (460 lines)
- `GET /teacher/classes` (target picker) → `POST /teacher/broadcast { class_ids, message, type }` → `GET /teacher/broadcasts` (history).
- Message types: Announcement, Reminder, Motivation.
- **Design-principle conflict:** this entire feature is framed as direct teacher-to-student messaging ("Sent to Class {x}: {message}"), which is the opposite of the product-initiated-nudge principle. Students receive these as explicit teacher messages, not as something the product surfaced on its own.

### Analytics — `TeacherAnalyticsPage.tsx` (1,130 lines) + `TeacherAnalytics.tsx` (660 lines)
- Two overlapping analytics pages exist:
  - `TeacherAnalyticsPage`: `GET /teacher/classes`, `GET /teacher/analytics/class/{id}` → score/completion/active-students summary + per-student score table (status bands: Excellent >80%, Good >60%, Needs Help <60%).
  - `TeacherAnalytics`: `GET /teacher/analytics/class/{classId}` and `.../detailed` → chapter-level completion/avg-score plus a student-details table (chapters completed, overall score, last active).
- Both link into a shared student-scores view at `/teacher/student/{id}/scores`.
- **Note:** two separate components covering similar ground (`TeacherAnalyticsPage` vs `TeacherAnalytics`) — worth checking if both are still live routes or if one is dead code.

### Doubts — `TeacherDoubtsPage.tsx` (990 lines)
- `GET /teacher/doubts` on mount, then 30-second `setInterval` polling for refresh (no SSE/WebSocket here, unlike Playground).
- AI-triage flow: `POST .../respond` (manual reply), `POST .../approve-ai` (accept AI's drafted answer), `POST .../reject-ai` (override with own response).
- Filter tabs: all / pending / ai_answered / resolved. Detail view is a modal/side-panel, not a separate route.
- **Design-principle note:** resolved doubts display "Answered by {teacher_name}" or "Answered by AI (approved by {teacher_name})" — fine for the teacher's own view, but the corresponding student-facing notification should stay product-framed rather than teacher-attributed.

---

## 4. Student-Facing Pages

### Home — `StudentHomePage.tsx` (1,010 lines)
- `GET /student/home` → student profile (xp, level, streak), subjects, recent activity, notifications. `GET /student/tasks/pending` for the pending-task badge. `POST /student/notifications/{id}/read`.
- Gamification: streak counter, level/XP display, dynamic time-of-day greeting.
- Bottom nav: Home, Explore, Playground, Tasks, Profile(logout).
- Copy is generally product-framed and on-principle (e.g. "Complete them to earn XP!"), though notification-item copy wasn't fully verified for teacher-framing leakage.

### Tasks — `StudentTasksPage.tsx` (440 lines)
- `GET /student/tasks`, with fallback to local mock store (`taskStore.getAll()`) on API failure.
- Filter tabs: All / Pending / Completed. Each task card shows XP reward and a due date.
- **Design-principle conflict:** "Due: {date}" framing implies a teacher-set deadline rather than a product-surfaced nudge.

### Task Activity — `StudentTaskActivityPage.tsx` (735 lines)
- `GET /student/task/{id}` (mock fallback via `taskStore.getById`), `POST .../progress`, `POST .../complete`.
- In-task doubt submission: `POST /student/doubts { task_id, question, subject }`.
- Completion triggers an XP celebration; "Open in Playground" deep-links to `/student/playground?taskId={id}`.
- **Design-principle conflicts:**
  - "Submit Doubt" button copy is mechanical/utilitarian rather than in the product's voice.
  - "Doubt submitted! You'll get a response soon" doesn't specify whether the response comes from the AI or the teacher — ambiguous attribution.

### Explore — `StudentExplorePage.tsx` (465 lines)
- `GET /student/subjects` → `GET /student/subject/{code}/chapter/{id}`, both with fallback to hardcoded `exploreData.ts` on error.
- Two-level drill-down: subjects → chapters → topics. Topic click routes into Playground with subject/chapter/topic context in the URL.

### Playground — `StudentPlaygroundPage.tsx` (~4,200 lines — largest file in the codebase)
- Combines topic picker, chat UI, voice recording, a canvas whiteboard, doubt submission, and session lifecycle management in one component. Strong refactor candidate given its size.
- Key calls: `POST /student/playground/session` (create), `GET .../session/{id}` (resume), `POST .../message`, `POST .../audio` (FormData), `POST .../session/{id}/end`, `GET .../session/{id}/history`, plus `POST /student/doubts` for in-session doubts.
- Real-time AI responses via `EventSource` SSE at `/student/playground/connect?session_id={id}` — not polling.
- Voice capture via the `MediaRecorder` API, sent as an audio blob.
- **Design-principle conflict:** doubt-prompt copy reads "Have a doubt? Ask your teacher!" — directly teacher-centric, should be product-framed (e.g. "Need help? Raise a doubt").
- Accepts deep-link query params (`taskId`, `subject`, `chapter`, `topic`) so Explore/Tasks can hand off context.

### Analytics — `StudentAnalytics.tsx` (620 lines)
- `GET /student/analytics` (overall score, per-subject breakdown, recent sessions, XP history, streak) and `GET /student/analytics/subject/{code}` for drill-down.
- **Dual-purpose component:** when accessed via `/teacher/student/{studentId}/scores`, the same component switches to teacher-view mode and calls `GET /teacher/student/{studentId}/analytics` instead — role detection comes from `mootion_role` in `localStorage` plus the presence of a route param.

---

## 5. Supporting Components

| Component | Lines | Role |
|---|---|---|
| `ChatbotFab.tsx` | 196 | Floating "Moo" chatbot — `POST /student/chat` (text) and `/student/chat/voice` (FormData). No error UI beyond `console.error`. |
| `Eye.tsx` | 64 | Purely decorative cursor-following eye animation. No API/state of note. |
| `FAQItem.tsx` | 31 | Accordion UI primitive, no API. |
| `GestureNavigation.tsx` | 102 | Swipe-right-to-go-back via touch events. Swipe-left (forward) is present in code but commented out. |
| `LiveVoiceActivity.tsx` | ~1,700 | A second, large voice-session implementation with its own session/connect/audio/message/end/board endpoints, functionally overlapping with the voice logic inside `StudentPlaygroundPage.tsx`. Uses raw `fetch`/`EventSource` directly, bypassing the `api.ts` wrapper (and therefore any auth-refresh logic it provides). Also relies on the deprecated `ScriptProcessorNode` for audio (vs. `AudioWorklet`). |
| `NavItem.tsx` | 28 | Presentational nav-item primitive. |
| `ProtectedRoute.tsx` | 56 | Covered in §1. |

**Open question:** `LiveVoiceActivity.tsx` and the voice/session logic embedded in `StudentPlaygroundPage.tsx` appear to duplicate the same session/connect/audio/board endpoint family — worth confirming which one is actually mounted/used in the live route tree, since maintaining both risks drift.

---

## 6. Data Layer

### Hardcoded / Mock Data (used as primary data or as error fallbacks, not pure placeholders)

| File | Contents | Consumed by |
|---|---|---|
| `data/exploreData.ts` (344 lines) | 4 subjects with chapters/topics and hardcoded progress percentages | `StudentExplorePage` (fallback), `StudentPlaygroundPage` (fallback) |
| `data/syllabus.ts` (335 lines) | 5-subject curriculum tree (math, science, english, social science, hindi) — chapters → topics → subtopics | Teacher chapter/topic setup pages |
| `data/tasks.ts` (82 lines) | 4 hardcoded tasks, each with a `dueDate` in January 2025 (i.e. in the past relative to any realistic demo date) | `taskStore.ts` |
| `data/taskStore.ts` (72 lines) | In-memory closure-based store (`getAll`, `getById`, `updateProgress`, `completeTask`, `addTask`, `setTasks`) with **no persistence** — resets on page refresh, no backend sync | `StudentTasksPage`, `StudentTaskActivityPage` (both as error fallbacks) |

**Risk:** `tasks.ts`'s hardcoded past due-dates will visibly look broken in any live demo or pilot if the fallback path is hit — worth either updating the dates or confirming the fallback never triggers in the actual deployed environment.

---

## 7. Static / Marketing Pages

- **`LandingPage.tsx`** (470 lines) — fully static marketing page, no API calls. Routes into `/onboarding` ("Start Learning") or `/teacher/login` ("I'm a Teacher"). Includes a "How Mootion Works" 3-step explainer and a 5-question FAQ accordion.
- **`OnboardingPage.tsx`** (78 lines) — role-selection screen ("I'm a Student" / "I'm a Teacher"), no API calls, just routes to signup or teacher login.
- **`not-found.tsx`** (49 lines) — standard 404 page, links back to `/`.

---

## 8. BFF Server — `server.ts` (500+ lines)

This is an **Express.js Backend-for-Frontend**, not a pure static file server:

- Proxies most `/auth/*`, `/student/*`, and `/teacher/*` calls through to the FastAPI backend, in some cases combining or transforming multiple backend calls into one response.
- Specifically handles: student OTP login/signup flow, teacher login/onboarding, chat/playground/tasks/analytics (student side), classes/chapters/topics/analytics/doubts/broadcast (teacher side).
- Hosts SSE endpoints for the real-time playground voice connection.
- Handles file uploads.
- Serves the production Vite build as static assets.

**Open question:** since this proxy layer exists, confirm whether `frontend/src/lib/api.ts` always routes through this BFF (`server.ts`) rather than hitting the FastAPI backend directly in some environments — this affects where auth-refresh and error-handling logic actually lives.

---

## 9. Cross-Cutting Patterns

- **State management:** 100% local `useState`/`useEffect`, fetch-on-mount. No React Context, no Redux, no shared global state anywhere in the audited files.
- **Auth persistence:** all tokens, role, and name/ID fields live in plain `localStorage` (no httpOnly cookie layer visible at this level).
- **Real-time strategy is inconsistent:** Playground uses SSE; Doubts uses 30-second polling. Worth deciding if Doubts should also move to SSE/WebSocket for parity, or if polling is an intentional simplicity tradeoff.
- **Auth-wrapper bypass:** `LiveVoiceActivity.tsx` and parts of `StudentPlaygroundPage.tsx` use raw `fetch`/`EventSource` instead of the shared `api` client in `lib/api.ts`, meaning they don't benefit from whatever auth-refresh/error-handling logic that wrapper provides.

---

## 10. Design-Principle Violations (Product-Initiated Nudge Principle)

Per Sharanya Ma'am's core principle — *the nudge to use the product must come from the product itself, not the teacher forcing the student* — the following copy/features currently cut against that:

1. **`TeacherBroadcastPage`** — the entire broadcast feature is explicit teacher-to-student direct messaging by design, not a product-surfaced nudge.
2. **`StudentPlaygroundPage`** (doubt prompt) — "Have a doubt? Ask your teacher!" should be reframed in product voice (e.g. "Need help? Raise a doubt").
3. **`StudentTasksPage`** — "Due: {date}" framing implies a teacher-imposed deadline rather than a self-paced, product-initiated task.
4. **`StudentTaskActivityPage`** — "Submit Doubt" button copy is mechanical; "You'll get a response soon" doesn't clarify AI vs. teacher as the source.
5. **`TeacherDoubtsPage`** — resolved-doubt attribution ("Answered by {teacher_name}") is appropriate for the teacher's own view, but the student-facing equivalent notification should stay product-framed rather than naming the teacher.

---

## Open Questions / Risks

- `TeacherAnalyticsPage.tsx` and `TeacherAnalytics.tsx` cover overlapping ground — confirm which is the live route and whether the other is dead code.
- `LiveVoiceActivity.tsx` appears to duplicate the voice-session logic already inside `StudentPlaygroundPage.tsx` — confirm which is actually mounted, since maintaining two parallel implementations of the same session/connect/audio flow is a drift risk.
- `data/tasks.ts` has hardcoded January 2025 due dates that will look stale/broken if its fallback path is ever hit in a live demo or pilot.
- Several components (`LiveVoiceActivity.tsx`, parts of `StudentPlaygroundPage.tsx`) bypass the shared `api.ts` client via raw `fetch`/`EventSource`, skipping whatever auth-refresh logic lives there.
- `TeacherDashboardPage`'s "Recent Activity" section is hardcoded mock data, not a real feed — needs a real endpoint before this can be considered pilot-ready.
