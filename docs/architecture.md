# SprintLens Architecture

SprintLens is a developer activity and project audit platform that combines project delivery, engineering evidence, performance feedback and developer growth in one workspace.

## System overview

```text
React + TypeScript (Vite)
        | same-origin /api/v1 requests
Django + Django REST Framework
        |                 |
    PostgreSQL         Redis
                          |
                    Celery worker + Beat

GitHub -- signed webhooks --> Django
Django -- approved project snapshot --> Google Gemini API
```

## Main components

| Component | Responsibility |
|---|---|
| `frontend/src/components/` | Login, grouped navigation, dashboards, feature screens and dialogs |
| `frontend/src/hooks/` | Session restoration, shared workspace state, API actions and page transitions |
| `frontend/src/api.ts` | Fetch client, CSRF headers, response handling and pagination |
| `backend/config/` | Django settings, URL routing, WSGI and Celery configuration |
| `backend/workspace/` | Models, API endpoints, authorization and business workflows |
| `backend/workspace/migrations/` | Versioned database schema changes |
| `backend/workspace/tests/` | API, permissions, workflows, integrations and production checks |
| `backend/scripts/`, `frontend/scripts/`, `deploy/` | Production build/start commands and deployment configuration |

## Features and data

- Organizations contain memberships with Admin, Manager or Developer roles. Projects have explicit team memberships and reviewer assignments.
- Projects contain tasks, sprints, milestones and dependencies. Tasks support assignment, progress updates, structured blockers, feedback and version checks against conflicting edits.
- Audit events record actors, changes and timestamps. Reviews and performance assessments support private drafts, published snapshots and developer responses.
- Growth goals track learning and milestones. Knowledge articles preserve shared solutions and revision history.
- Analytics explains workload, delivery and deadline risks. Reports provide authenticated PDF, CSV and JSON exports.

## Request and integration flow

1. React restores the session and obtains a CSRF token. Django authenticates users with session cookies; administrators create accounts.
2. The frontend sends API requests. Django checks organization, project and action permissions before using the ORM to read or update PostgreSQL.
3. Relevant mutations write audit records atomically. Responses update the frontend state.
4. GitHub webhooks verify signatures and deduplicate deliveries before storing commits, pull requests and reviews as task evidence.
5. Celery Beat schedules notification jobs; workers use Redis as the broker and persist notifications for the private inbox. Production also uses Redis for shared caching.
6. AI insights require a configured server-side Gemini key and explicit approval of the project snapshot. Generated insights remain reviewable drafts. Reports can operate without AI.

## Runtime and deployment

Local development uses React on port 5173 with a Vite API proxy to Django on port 8000, installed PostgreSQL on port 5432, and Redis for background jobs. The API-only backend does not serve application HTML, CSS or JavaScript.

The deployment target is Vercel for React and Render for Django/Gunicorn, PostgreSQL, Redis, Celery worker and Beat. Vercel forwards API requests to the backend. Production preparation exists; hosted deployment and final end-to-end verification remain pending.

Secrets stay in private local configuration or environment variables. Production validates configuration, uses secure cookies and provides health checks. GitHub activity is supporting evidence; commit counts alone do not determine performance.
