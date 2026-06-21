# Mootion Backend Domain Model

This is the source-of-truth model for the new Mootion backend.

## Core Principles

- One backend supports two roles: `teacher` and `student`.
- School, class, and subject structure is the primary tenant boundary.
- Language is a user preference, but content generation and UI can switch mid-session.
- Teacher content is curated, student activity is logged, and all attempts are kept.

## Core Entities

### Identity

#### `users`
- `id`
- `role` (`teacher` | `student`)
- `full_name`
- `phone` or `email`
- `password_hash`
- `preferred_language`
- `onboarding_completed`
- `created_at`, `updated_at`

#### `oauth_accounts`
- `id`
- `user_id`
- `provider` (`google`)
- `provider_user_id`
- `email`
- `created_at`

#### `sessions` / `refresh_tokens`
- `id`
- `user_id`
- `token_hash`
- `expires_at`
- `revoked_at`

### School Structure

#### `schools`
- `id`
- `name`
- `code`
- `created_by_teacher_id`
- `created_at`

#### `classes`
- `id`
- `school_id`
- `grade` (`6` to `12`)
- `section` or `display_name`
- `subject`
- `created_at`

#### `teacher_class_memberships`
- `teacher_id`
- `class_id`
- `is_primary`

#### `student_class_memberships`
- `student_id`
- `class_id`
- `roll_number` or `display_order`

### Curriculum and Chapters

#### `subjects`
- `id`
- `name` (`Physics`, `Mathematics`, `Chemistry`, `Biology`, `Computer Science`)

#### `curricula`
- `id`
- `school_id`
- `source` (`ncert` | `custom`)
- `language`
- `created_at`

#### `chapters`
- `id`
- `class_id`
- `curriculum_id`
- `sequence_number`
- `title`
- `status` (`unset` | `generated` | `active` | `data_ready`)
- `created_at`, `updated_at`

#### `chapter_assets`
- `id`
- `chapter_id`
- `asset_type` (`concept_video`, `simulation`, `activity_template`)
- `title`
- `description`
- `payload_json`
- `generation_status`
- `last_generated_at`

### Assignments and Activity

#### `assignments`
- `id`
- `chapter_id`
- `class_id`
- `assigned_by_teacher_id`
- `deadline_at`
- `note`
- `status` (`draft` | `live` | `archived`)

#### `assignment_activities`
- `id`
- `assignment_id`
- `activity_type` (`explain_it` | `predict_it` | `spot_it` | `connect_it`)
- `enabled`
- `order_index`

#### `activity_attempts`
- `id`
- `assignment_activity_id`
- `student_id`
- `attempt_number`
- `input_mode` (`voice` | `text`)
- `language`
- `transcript`
- `response_json`
- `scores_json`  
  Stores `understanding`, `reasoning`, `expression`, and `prediction_accuracy` where relevant.
- `created_at`

#### `activity_feedback`
- `id`
- `attempt_id`
- `feedback_text`
- `misconceptions_json`
- `follow_up_json`

### Doubts and Quotas

#### `doubts`
- `id`
- `student_id`
- `class_id`
- `chapter_id`
- `assignment_activity_id` nullable
- `topic`
- `question_text`
- `attempted_before`
- `status` (`open` | `answered` | `closed`)
- `created_at`

#### `doubt_responses`
- `id`
- `doubt_id`
- `response_type` (`clarification_video` | `text` | `voice_note`)
- `payload_json`
- `created_by_teacher_id` nullable
- `created_at`

#### `usage_quotas`
- `id`
- `user_id`
- `quota_type` (`doubt_video_daily` | `playground_weekly`)
- `window_start`
- `window_end`
- `used_count`
- `limit_count`

### Analytics

#### `chapter_analytics`
- `id`
- `class_id`
- `chapter_id`
- `understanding_distribution_json`
- `reasoning_distribution_json`
- `expression_distribution_json`
- `top_misconceptions_json`
- `completion_rate`
- `updated_at`

#### `student_progress_snapshots`
- `id`
- `student_id`
- `class_id`
- `chapter_id`
- `understanding_score`
- `reasoning_score`
- `expression_score`
- `language_ratio_json`
- `created_at`

#### `events`
- `id`
- `actor_user_id`
- `event_type`
- `entity_type`
- `entity_id`
- `payload_json`
- `created_at`

## Relationship Summary

- A `school` has many `classes`.
- A `teacher` can belong to many `classes`.
- A `student` can belong to one or more `classes`.
- A `class` has many `chapters` and `assignments`.
- A `chapter` has generated assets and can be assigned to a class.
- An `assignment` contains multiple activity toggles.
- A student can have many attempts per activity.
- Doubts are tied to students, chapters, and optionally a specific activity attempt.

## Lifecycle Rules

- Teacher onboarding creates or joins a school, then creates class memberships.
- NCERT bootstrap creates the full chapter sequence for each selected grade-subject pair.
- Chapter status moves from `unset` to `generated` to `active` to `data_ready`.
- Assigning a chapter makes one or more activities live for students.
- Students can retry activities indefinitely; each attempt is persisted.
- Doubt generation is quota-limited and logged for teachers.

## MVP Scope

Build first:
- users, oauth accounts, sessions
- schools, classes, memberships
- subjects, curricula, chapters
- assignments, activities, attempts
- doubts and quotas
- analytics snapshots and events

Defer until later:
- voice-note responses
- advanced notification delivery
- full custom curriculum authoring
- complex reporting exports
