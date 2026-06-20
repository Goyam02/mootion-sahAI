# Conceptual Understanding Analytics — Master Testing Guide

This guide outlines the backend Swagger UI procedures, frontend manual validation checklists, direct SQLite database queries, and known edge-case definitions for testing the conceptual analytics and KMeans clustering features in Mootion.

---

## SECTION 1: Backend — Swagger UI Testing

### Endpoint Reference Table

| Method | Route | Auth Header | Sample Request Body | Expected Response Shape |
| :--- | :--- | :--- | :--- | :--- |
| **POST** | `/api/analytics/submit-explanation` | `Bearer <student_jwt>` | `{"chapter_id": "cea832b6-2f2f-4f2c-94bc-fdddc21884b1", "class_id": "050979fb-d6d2-4389-8f32-bb6fc3e33dd8", "transcript": "Cell division is the process..."}` | `{"concept_score_id": "uuid", "clarity_score": 8.0, "accuracy_score": 9.0, "depth_score": 4.0, "overall_score": 7.0, "llm_feedback": "...", "attempt_number": 3, "created_at": "timestamp"}` |
| **GET** | `/api/analytics/student/{student_id}/scores` | `Bearer <jwt_token>` (own student or class teacher) | *None* | `[{"chapter_id": "uuid", "scores": [{"id": "uuid", "transcript": "...", "clarity_score": 8.0, "accuracy_score": 9.0, "depth_score": 4.0, "overall_score": 7.0, "llm_feedback": "...", "attempt_number": 1, "created_at": "timestamp"}], "trend": "stable"}]` |
| **GET** | `/api/analytics/class/{class_id}/overview` | `Bearer <teacher_jwt>` | *None* | `[{"chapter_id": "uuid", "avg_score": 6.64, "student_count": 3, "weakest_students": [{"student_id": "uuid", "full_name": "Alice Smith", "score": 4.0}]}]` |
| **POST** | `/api/analytics/class/{class_id}/compute-clusters` | `Bearer <teacher_jwt>` | `{"chapter_id": "cea832b6-2f2f-4f2c-94bc-fdddc21884b1"}` | `[{"id": "uuid", "class_id": "uuid", "chapter_id": "uuid", "cluster_label": "struggling", "student_ids": ["uuid"], "avg_score": 4.0, "computed_at": "timestamp"}]` |
| **GET** | `/api/analytics/class/{class_id}/clusters` | `Bearer <teacher_jwt>` | *None* | `[{"id": "uuid", "class_id": "uuid", "chapter_id": "uuid", "cluster_label": "struggling", "avg_score": 4.0, "students": [{"student_id": "uuid", "full_name": "Alice Smith"}], "computed_at": "timestamp"}]` |

---

### Step-by-Step Swagger UI Instructions

1. **Access the Documentation**:
   - Open your browser and navigate to `http://localhost:8000/docs`.

2. **Retrieve a Student JWT Token**:
   - Locate the `POST /auth/login` endpoint.
   - Click **Try it out** and enter the student credentials:
     ```json
     {
       "login_id": "student1",
       "password": "student1"
     }
     ```
   - Execute the request, then copy the returned `access_token` string (exclude quotes).
   - Scroll to the top of the Swagger page, click **Authorize**, paste the token in the value field, and click **Authorize**.

3. **Submit a Science Explanation**:
   - Locate `POST /api/analytics/submit-explanation`.
   - Fill in a valid `class_id` and `chapter_id` (retrieve these from the database or run the integration tests to populate them).
   - Enter a transcript such as:
     `"Cell division is the process by which a parent cell divides into two or more daughter cells. It is essential for growth."`
   - Execute and confirm you receive a `200 OK` response with clarity, accuracy, and depth scores.

4. **Retrieve a Teacher JWT Token**:
   - Click **Authorize** at the top, click **Logout** to remove the student session.
   - Under `POST /auth/login`, enter teacher credentials:
     ```json
     {
       "login_id": "abc",
       "password": "abc"
     }
     ```
   - Copy the teacher `access_token`, click **Authorize** at the top, and paste the teacher token.

5. **Test Clustering (KMeans)**:
   - Make sure at least 3 students have submitted scores for the class & chapter (you can run `python scratch/test_clustering.py` to auto-seed Alice Smith, Bob Jones, and Default Student scores).
   - Locate `POST /api/analytics/class/{class_id}/compute-clusters`. Enter the classroom UUID and request body:
     ```json
     {
       "chapter_id": "cea832b6-2f2f-4f2c-94bc-fdddc21884b1"
     }
     ```
   - Execute and verify you receive three cluster rows (`"struggling"`, `"average"`, `"strong"`).
   - Call `GET /api/analytics/class/{class_id}/clusters` to confirm that the student user UUIDs are successfully mapped and joined to their full names.

6. **Error Responses Cheat Sheet**:
   - **401 Unauthorized**: JWT token is missing, expired, or malformed.
   - **403 Forbidden**: Student queries another student's scores, or teacher queries a classroom they do not own.
   - **404 Not Found**: Class ID or Chapter ID does not exist in the database.
   - **422 Unprocessable Entity**: Invalid body structure, missing required fields, or invalid UUID formatting.

---

## SECTION 2: Frontend — Manual Testing Checklist

1. **Student voice workspace**:
   - Log in to Mootion as student (`student1` / `student1`).
   - Navigate to `/student/tasks` and click on an assignment (e.g., an "Explain It" task).
   - Click the microphone button, explain a concept aloud (or type in the text area), and click **Stop Recording**.
   - Confirm a evaluation card renders underneath with Clarity, Accuracy, and Depth progress bars (color-coded: green $>7$, yellow $4-7$, red $<4$) along with the AI feedback.
   - Click **View Full Analytics**.

2. **Student Analytics page**:
   - Confirm you are redirected to `/student/analytics`.
   - Verify that chapter breakdown cards show the overall score, attempt count, and trend arrows (↑↓).
   - Expand a card and confirm all previous attempts appear with transcripts, individual scores, and feedback.
   - Confirm that the `recharts` Radar Chart renders successfully with chapters as axes.
   - Verify that the **Your Weakest Topics** section highlights the bottom 3 chapters in red.

3. **Teacher Diagnostics Workspace**:
   - Log in to Mootion as teacher (`abc` / `abc`).
   - Click on the analytics icon in the sidebar nav (navigates to `/teacher/analytics/:classId`).
   - Confirm that the **Class Overview** card loads a table showing Chapter, Average Score, Attempted Students, and Weakest Students.
   - Click the **Sort by Avg Score** button to verify it toggles sorting ascending/descending.
   - Under **Conceptual Student Clusters**, expand a chapter row and confirm that students are grouped into 🔴 Struggling, 🟡 Average, and 🟢 Strong tags.
   - Click the **Recompute Clusters** button next to a chapter row, observe the spinner animation, and confirm the clusters refresh.
   - Click on any student name tag inside a cluster. Verify it navigates to `/teacher/student/{studentId}/scores`, showing the student's history in a **Teacher View Mode** read-only dashboard.

---

## SECTION 3: Database Sanity Checks

Run these SQL queries directly on `backend/mootion.db` using a SQLite client (e.g., DB Browser for SQLite or command-line client) to confirm database consistency.

### 1. View Concept Scores for a Student
```sql
SELECT 
    attempt_number, 
    overall_score, 
    clarity_score, 
    accuracy_score, 
    depth_score, 
    transcript 
FROM concept_scores 
WHERE student_id = (SELECT id FROM users WHERE login_id = 'student1') 
ORDER BY attempt_number ASC;
```

### 2. Confirm Attempt Number Auto-Incrementing
```sql
SELECT 
    u.full_name, 
    c.title AS chapter_title, 
    cs.attempt_number, 
    cs.overall_score 
FROM concept_scores cs
JOIN users u ON cs.student_id = u.id
JOIN chapters c ON cs.chapter_id = c.id
ORDER BY cs.student_id, cs.chapter_id, cs.attempt_number;
```

### 3. Check Classroom Clusters & Student JSON Data
```sql
SELECT 
    c.title AS chapter_title, 
    stc.cluster_label, 
    stc.avg_score, 
    stc.student_ids 
FROM student_topic_clusters stc
JOIN chapters c ON stc.chapter_id = c.id;
```

---

## SECTION 4: Known Edge Cases

* **LLM Output Malformed**:
  - If the Azure OpenAI service fails to return a valid JSON object or returns incorrect schemas, the backend catches the parsing error and returns a `502 Bad Gateway` status (`"Failed to generate score from LLM"`). The student's voice state remains intact to try again.
* **Clustering with $< 3$ Student Scores**:
  - If the teacher requests cluster recomputation for a chapter where fewer than 3 students have logged scores, KMeans cannot partition the space. The backend skips the operation, returns a `400 Bad Request` status, and the frontend displays a toast alert: `"Error recomputing clusters. Minimum of 3 students with scores required."`
* **Student Score Auditing Guard**:
  - If a student alters the browser URL to `/api/analytics/student/{other_student_id}/scores`, the backend dependency check `require_teacher_or_student` confirms the session ID matches the query ID. If they differ, the backend blocks the query immediately with `403 Forbidden`.
* **Cross-Classroom Auditing Guard**:
  - If a teacher attempts to drill down into a student profile or classroom diagnostics for a class they do not teach, the backend queries `TeacherClassMembership` and `StudentClassMembership`. If there is no shared membership, the query is blocked with `403 Forbidden`.
