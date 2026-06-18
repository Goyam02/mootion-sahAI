Read the entire backend codebase before writing anything. This document gives you 
the frontend/backend contract context you need to implement NCERT subtopics correctly.

CONTEXT:
Mootion is an EdTech platform for Indian government school students (Classes 6–12).
The backend is FastAPI. The frontend is Next.js.

CURRENT DATA MODEL (already implemented):
- Class → has a Curriculum → has Chapters → each Chapter has Assets
- Curriculum is a tree: root node → unit nodes → (currently stops here)
- Chapter rows are bootstrapped from curriculum root's children (one chapter per unit node)
- Each chapter gets placeholder assets for all 8 activity types on creation
- Asset types: concept_video, simulation, three_d_model, quiz, explain_it, predict_it, 
  spot_it, connect_it

WHAT IS MISSING (what you are building):
The curriculum tree nodes support kinds: module, unit, topic, subtopic, lesson
But currently chapters are only bootstrapped one level deep (unit = chapter).
There is no subtopic/subsection layer surfaced to the frontend yet.

WHAT YOU NEED TO BUILD:
A subtopics system so that each chapter can have an ordered list of subtopics 
(e.g. Chapter: "Light" → subtopics: "Reflection", "Refraction", "Dispersion").

These subtopics come from scraping the NCERT syllabus for classes 6–12, 
subjects: Physics, Chemistry, Mathematics, Biology, Science.

IMPLEMENTATION REQUIREMENTS:

1. Populate the curriculum tree nodes for all NCERT chapters with their 
   real subtopics as child nodes with kind: "topic" or "subtopic"
   Use PATCH /teachers/classes/{class_id}/curriculum/{curriculum_id} with 
   operation: "add_node" to add them, OR seed them directly in the DB — 
   your choice based on what's cleaner in the backend architecture.

2. Expose subtopics on the chapter detail endpoint:
   GET /teachers/classes/{class_id}/chapters/{chapter_id}
   Currently returns assets only. Add a "subtopics" array to the response:
   [{ subtopic_id, title, order, kind, metadata }]
   Sourced from the curriculum tree nodes that are children of this chapter's source_node_id.

3. The same subtopics must be visible to students.
   If the student chapter view hits a different endpoint, expose subtopics there too.

4. Each subtopic can optionally have its own assets in the future 
   (not required now — just keep the data model extensible for this).

5. Write a seed script or migration that populates NCERT subtopics for all 
   supported subjects and grades so a fresh bootstrap gives real data immediately.

NCERT SCOPE TO SCRAPE/SEED:
- Classes 6–10: Science (map to both Physics + Chemistry + Biology conceptually), 
  Mathematics
- Classes 11–12: Physics, Chemistry, Mathematics, Biology
- Source: ncert.nic.in official textbook chapter listings

AFTER YOU IMPLEMENT:
Update docs/NCERT_SUBTOPICS_INTEGRATION.md with:
- The subtopics array shape added to the chapter response
- How the seed script is run
- How to add a new subject or grade in future
- Any caveats about curriculum node IDs and how they map to chapter source_node_id