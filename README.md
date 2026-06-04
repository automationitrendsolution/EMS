# iTrendTASKS

A production-ready **Employee Task & Project Management** platform — think Jira / Trello / ClickUp, scoped strictly to task and project management (no payroll, HR, CRM, etc.).

Built with **Django 5 + Django REST Framework + MongoDB (MongoEngine) + Django Channels + Celery + Bootstrap 5**, containerized with **Docker Compose** behind **Nginx**.

---

## Features (all 13 modules)

| # | Module | Highlights |
|---|--------|-----------|
| 1 | Employee Management | Employees, departments, designations, teams, profile images, status |
| 2 | Project Management | Create / edit / archive / delete, status & priority, manager + team |
| 3 | Task Management | CRUD, assign, reassign, clone, bulk assign, bulk status, tags |
| 4 | Subtasks | Unlimited subtasks, auto progress % (`done / total × 100`) |
| 5 | Kanban Board | Trello-like drag & drop, realtime sync, filter & search |
| 6 | Comments | Add / edit / delete, `@EMP0001` mentions with notifications |
| 7 | File Attachments | PDF/DOCX/XLSX/ZIP/PNG/JPG, validated, stored in a Docker volume |
| 8 | Time Tracking | Start / pause / resume / stop, per-task & per-employee reports |
| 9 | Activity Log | Timeline of every task event |
| 10 | Dashboard | Stat cards + Chart.js charts + employee workload |
| 11 | Notifications | Realtime via WebSockets + due-date reminders (Celery) |
| 12 | Reports | Task / Project / Employee / Productivity → CSV, Excel, PDF |
| 13 | AI Assistant | Task breakdown, task summary, project health (OpenAI + offline fallback) |

Plus: **RBAC** (Super Admin / Admin / Project Manager / Team Leader / Employee), **JWT** API auth, **Swagger** docs, **dark mode**, responsive UI.

---

## Architecture

```
Browser ──► Nginx ──► Daphne (ASGI) ──► Django
                                      ├─ REST API (DRF, JWT)        → MongoDB (MongoEngine)
                                      ├─ Server-rendered pages       (signed-cookie sessions)
                                      └─ WebSockets (Channels)      → Redis (channel layer)
Celery worker + beat ──► Redis (broker) ──► due-date reminders
```

* **Domain data** lives in MongoDB via MongoEngine. Django's ORM is *not* used for domain models; a tiny SQLite file backs only Django-internal tables (e.g. `django_celery_beat`).
* **Two auth paths share one user store:** JWT (`Authorization: Bearer …`) for the API, and signed-cookie sessions for the HTML frontend. The frontend mints a short-lived JWT per page render so its JavaScript can call the API and open authenticated WebSockets.

See [Document.md](Document.md) for the original specification.

---

## Quick start (Docker — recommended)

```bash
cp .env.example .env          # then edit secrets (see Security note below)
docker compose up --build
```

Open **http://localhost** — the first boot auto-seeds demo data (`RUN_SEED=1`).

**Demo logins** (password shown):

| Role | Email | Password |
|------|-------|----------|
| Super Admin | `admin@itrendtasks.local` | `admin12345` |
| Project Manager | `pm@itrendtasks.local` | `pm12345` |
| Team Leader | `tl@itrendtasks.local` | `tl12345` |
| Employee | `rajesh@itrendtasks.local` | `emp12345` |

API docs: **http://localhost/api/docs/** (Swagger) · **/api/redoc/**

---

## Local development (without Docker)

You need MongoDB and Redis running locally.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# point MONGO_HOST=localhost and REDIS_URL=redis://localhost:6379/0 in .env

python manage.py migrate                 # django-internal tables only
python manage.py seed_demo               # demo data
daphne -b 0.0.0.0 -p 8000 config.asgi:application   # ASGI (WebSockets work)
# ...or: python manage.py runserver       # HTTP only

# In separate shells (for reminders/async):
celery -A config worker -l info
celery -A config beat   -l info
```

---

## Testing

```bash
pytest                       # uses in-memory mongomock — no DB required
# or
python manage.py test
```

16 tests cover models, JWT/auth, task CRUD/move/kanban, timers, and AI fallbacks.

---

## REST API (selected)

All endpoints are under `/api/v1/` and support **search, filter, pagination (`?page=&page_size=`), and ordering (`?ordering=`)** where applicable.

| Area | Endpoint |
|------|----------|
| Auth | `POST /auth/login/`, `POST /auth/refresh/`, `GET /auth/me/` |
| Employees | `GET/POST /auth/employees/`, `GET/PATCH/DELETE /auth/employees/{id}/` |
| Projects | `GET/POST /projects/`, `GET/PATCH/DELETE /projects/{id}/`, `POST /projects/{id}/archive/` |
| Tasks | `GET/POST /tasks/`, `GET/PATCH/DELETE /tasks/{id}/`, `/assign/ /clone/ /move/` |
| Bulk | `POST /tasks/bulk-assign/`, `POST /tasks/bulk-status/` |
| Subtasks | `POST /tasks/{id}/subtasks/`, `POST .../{sid}/toggle/`, `DELETE .../{sid}/` |
| Comments | `GET/POST /tasks/{id}/comments/`, `PATCH/DELETE .../{cid}/` |
| Attachments | `POST /tasks/{id}/attachments/` (multipart), `DELETE .../{aid}/` |
| Time | `POST /tasks/{id}/timer/{start,pause,resume,stop}/`, `GET .../timelogs/` |
| Kanban | `GET /kanban/{project_id}/` |
| Notifications | `GET /notifications/`, `POST /notifications/read-all/` |
| Reports | `GET /reports/{type}/`, `GET /reports/{type}/export/{csv\|excel\|pdf}/` |
| AI | `POST /ai/breakdown/`, `POST /ai/tasks/{id}/summary/`, `POST /ai/projects/{id}/health/` |
| Dashboard | `GET /dashboard/stats/` |

WebSockets: `ws://…/ws/kanban/{project_id}/?token=<jwt>` and `ws://…/ws/notifications/?token=<jwt>`.

---

## Security

- JWT auth (access + refresh), bcrypt password hashing.
- CSRF protection on session forms; the session-based DRF fallback is **read-only** (mutations require a Bearer token) to avoid CSRF.
- Upload validation (extension allow-list + size cap), randomized stored filenames.
- Rate limiting (scoped throttles on auth & AI endpoints).
- Activity logging / audit trail per task.
- Hardened cookies, HSTS, and SSL redirect auto-enable when `DEBUG=False`.

> ⚠️ **Never commit real secrets.** `.env.example` is a template; put real values (`SECRET_KEY`, `JWT_SECRET`, `OPENAI_API_KEY`) only in `.env`, which is git-ignored. If a key was ever committed, rotate it.

---

## Project layout

```
config/        settings, urls, asgi/wsgi, celery, mongo bootstrap
core/          shared: middleware, permissions, pagination, realtime, ws auth
accounts/      Module 1 + auth (JWT) + RBAC
projects/      Module 2
tasks/         Modules 3,4,5,6,7,8,9 (+ consumers)
notifications/ Module 11 (+ consumer + Celery reminders)
dashboard/     Module 10
reports/       Module 12 (CSV/Excel/PDF)
ai_assistant/  Module 13 (OpenAI + fallback)
templates/     Bootstrap 5 server-rendered pages
static/        CSS + JS (kanban drag-drop, realtime, API client)
docker/        entrypoint, nginx.conf
```

See [DEPLOYMENT.md](DEPLOYMENT.md) for the production deployment guide.
