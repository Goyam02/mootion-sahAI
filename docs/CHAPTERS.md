# Chapters

This document describes the current chapter scaffolding flow.

## What a Chapter Is

A chapter is the unit of learning delivery in Mootion.

It sits between curriculum and assignment:

- curriculum defines the roadmap
- chapter defines the learning segment
- assignment launches the actual classroom activity

Each chapter belongs to one class and one curriculum.

## Why Chapters Exist

Chapters are the bridge between the teacher's roadmap and the actual activities students will consume.

They let the backend:

- keep curriculum structure separate from delivery content
- attach reusable placeholder assets to one learning segment
- generate activity-specific content only when the teacher assigns it

## Current Model

- Chapters are created from curriculum units.
- Chapters are ordered by `sequence_number`.
- Each chapter starts with placeholder assets.
- Actual media generation now happens when a teacher creates an assignment.

## Status

Current chapter statuses:

- `unset`
- `generated`
- `active`
- `data_ready`

For now, new chapters start as `unset`.

## Placeholder Assets

Each chapter is seeded with placeholder assets for:

- concept video
- simulation
- 3D model
- quiz
- Explain It
- Predict It
- Spot It
- Connect It

Each asset has:

- `asset_type`
- `provider`
- `integration_target`
- `title`
- `description`
- `payload_json`
- `generation_status`
- `external_url`
- `storage_bucket`
- `storage_key`

### Why placeholders exist

The chapter must exist before the real content exists.

Placeholders let the frontend render structure immediately and let the assignment flow fill in the actual content later.

## Endpoint: `POST /teachers/classes/{class_id}/chapters/bootstrap`

### What it does

This endpoint creates chapter rows from the top-level curriculum children.

### Why it exists

It is the bridge from roadmap to chapter structure.

Use it when the teacher already has a curriculum and wants the backend to turn that roadmap into chapter objects.

### How it works

1. The backend loads the class curriculum.
2. It reads the curriculum root children.
3. Each top-level child becomes a chapter.
4. Each chapter child becomes a topic.
5. Each topic gets placeholder concept video, simulation, and 3D model assets.
6. Teachers can generate those assets directly from the topic workspace.

### How to use it

Send an empty POST request after the curriculum exists.

Example:

```http
POST /teachers/classes/CLASS_ID/chapters/bootstrap
Authorization: Bearer ACCESS_TOKEN
```

Request body:

```json
{
}
```

### What you get back

```json
{
  "class_id": "...",
  "curriculum_id": "...",
  "created_chapters": 4
}
```

### Important detail

This endpoint now creates both chapter rows and nested topic rows.

It also attaches topic-level placeholder assets for video, simulation, and 3D model generation.

## Assignment-Triggered Generation

Real content generation now happens in the topic workspace for the main media assets.

That means:

- bootstrap creates structure
- the chapter workspace lists topics
- the topic workspace can generate the concept video, simulation, and 3D model directly
- generated videos are stored in private object storage and served back through the backend media URL, which redirects to a signed URL

Assignments still exist for classroom delivery and assessment workflows.

## Related Endpoints

- `GET /teachers/classes/{class_id}/chapters`
- `GET /teachers/classes/{class_id}/chapters/{chapter_id}`

## `GET /teachers/classes/{class_id}/chapters`

Returns the chapter list for the class.

Use it when:

- building the teacher chapter view
- showing chapter counts
- choosing which chapter to assign

## `GET /teachers/classes/{class_id}/chapters/{chapter_id}`

Returns the detailed chapter with all assets.

Use it when:

- rendering a chapter detail page
- inspecting which assets have been generated
- debugging an assignment result

## Common Mental Model

- curriculum answers: what should we teach?
- chapter answers: how do we group the teaching?
- assignment answers: what activity should students do now?
