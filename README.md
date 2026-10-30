# ToDo API

A **Django REST API** for task management. Users register (web or Telegram), authenticate with **JWT**, and manage tasks
with categories, deadlines, and completion status.

## Features

- **Tasks**: full CRUD through a single viewset; each user sees only their own tasks.
- **Categories**: urgency-based categories linked to tasks.
- **Auth**: Simple JWT (access/refresh, blacklist on rotation); separate registration flows for Telegram and web profiles.
- **API docs**: OpenAPI schema and **Swagger UI** (drf-spectacular).
- **Task events**: creating, updating or deleting a task publishes an event to RabbitMQ; the
  [todo-bot](https://github.com/Domiff/todo-bot) service consumes it and notifies the owner in Telegram.

## Tech stack

| Layer          | Technologies                                                       |
|----------------|--------------------------------------------------------------------|
| API            | Django 6, Django REST Framework, async views (adrf), Daphne (ASGI) |
| Auth           | djangorestframework-simplejwt                                      |
| Database       | PostgreSQL; SQLite when `DEBUG=True`                               |
| Messaging      | RabbitMQ (aio-pika), events in CloudEvents 1.0 JSON format         |
| Tooling        | uv, Ruff, pre-commit                                               |
| Infrastructure | Postgres, RabbitMQ and logging live in [todo-infrastructure](#infrastructure) |


## Application structure

### Repository tree

```text
.
├── backend/
│   ├── manage.py
│   ├── core/                         # Django project (settings, routing, ASGI)
│   │   ├── asgi.py
│   │   ├── messaging/                # RabbitMQ client code shared by all apps
│   │   │   ├── connection.py         # one robust connection + channel per process
│   │   │   ├── events.py             # Event: CloudEvents envelope, serialized to JSON
│   │   │   ├── topology.py           # names of exchanges this service publishes to
│   │   │   └── utils.py              # JSON serialization helpers
│   │   ├── settings/                 # split settings (env, apps, base, database, rabbitmq, ...)
│   │   ├── urls.py                   # mounts /api/, /auth/, /admin/, /schema/
│   │   └── wsgi.py
│   ├── todo/                         # Tasks & categories
│   │   ├── migrations/
│   │   ├── events.py                 # task event types and payloads (contract with consumers)
│   │   ├── producers.py              # publish(), routing keys
│   │   ├── serializers.py
│   │   ├── models.py
│   │   ├── urls.py                   # router: tasks/
│   │   └── views.py                  # TaskViewSet (adrf ModelViewSet)
│   └── auth_user/                    # Registration & JWT-facing views
│       ├── migrations/
│       ├── admin.py
│       ├── models.py                 # TgProfile, WebProfile
│       ├── serializers.py
│       ├── urls.py
│       └── views.py
│
├── Dockerfile
├── Justfile
├── docker-compose.yml                # backend only; infrastructure is in todo-infrastructure
├── pyproject.toml                    # uv dependency groups: backend, dev
└── uv.lock
```

## Requirements

- **Python 3.13+**
- **[uv](https://docs.astral.sh/uv/)** (recommended) for installs and scripts
- **Docker** / Docker Compose and a running [todo-infrastructure](#infrastructure) stack

## Configuration

Create an env file at the **repository root** (it is gitignored; do not commit secrets):

### `.env`

| Variable                                            | Purpose                                                                      |
|-----------------------------------------------------|------------------------------------------------------------------------------|
| `DJANGO_SECRET_KEY`                                 | Django secret                                                                |
| `DJANGO_DEBUG`                                      | `True` → SQLite (local dev); `False` → Postgres (Docker, production)         |
| `ALLOWED_HOSTS`                                     | Comma-separated list of allowed hosts (e.g. `localhost,127.0.0.1,backend`)   |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | Same credentials as in todo-infrastructure's `.env`                          |
| `POSTGRES_HOST`, `POSTGRES_PORT`                    | `todo-pg` and `5432` in Docker; `127.0.0.1` when running on the host         |
| `RABBITMQ_USER`, `RABBITMQ_PASSWORD`                | Same credentials as in todo-infrastructure's `.env` (required)               |
| `RABBITMQ_HOST`, `RABBITMQ_PORT`                    | `todo-rabbitmq` and `5672` in Docker; `127.0.0.1` when running on the host   |

## Local development (without Docker)

1. Install dependencies:
   ```bash
   uv sync
   ```

2. Create `.env` at the repo root with at minimum:
   ```env
   DJANGO_SECRET_KEY=your-secret-key
   DJANGO_DEBUG=True
   ALLOWED_HOSTS=localhost,127.0.0.1
   ```
   With `DEBUG=True` the project uses SQLite — no Postgres required.
   The `RABBITMQ_*` variables have no defaults, so they must be set too. RabbitMQ itself only has
   to be reachable when an event is published (the connection is opened lazily).

3. Run migrations:
   ```bash
   just migrate
   ```

4. Start the API:
   ```bash
   just run
   ```
   Or with Daphne (ASGI):
   ```bash
   just run-asgi
   ```

## Infrastructure

Postgres, RabbitMQ, Redis and logging (Grafana, Loki, Promtail) are not part of this repository.
They run in the separate **todo-infrastructure** stack, and this service connects to it over the
external Docker network **`todo-network`**.

Start order: **todo-infrastructure → todo-api → todo-bot**. This compose file has no `depends_on`
on Postgres or RabbitMQ (Compose cannot depend on another project), so the infrastructure must be
up and healthy before the backend starts.

## Docker Compose

1. Start todo-infrastructure (it also expects the `todo-network` network, see its README).

2. In this repository set `DJANGO_DEBUG=False` in `.env` so the backend uses Postgres
   (`POSTGRES_HOST=todo-pg`). With `DEBUG=True` it uses SQLite **inside the container**, and the
   data is lost every time the container is recreated.

3. Build and start the backend:

   ```bash
   docker compose up -d --build
   ```

4. Apply migrations and create an admin user:

   ```bash
   docker compose exec backend python manage.py migrate
   docker compose exec backend python manage.py createsuperuser
   ```

| Service          | Container      | Port | Notes                                                   |
|------------------|----------------|------|---------------------------------------------------------|
| Backend (Daphne) | `todo-backend` | 8000 | Reachable as `backend:8000` from other services in `todo-network` |

There is no reverse proxy in front of Daphne, and Daphne does not serve static files: with
`DEBUG=False` the admin and Swagger UI load without styles.

## Messaging

The API publishes domain events to RabbitMQ so other services can react without calling the API.

- **Broker**: `todo-rabbitmq` from todo-infrastructure. The connection is opened lazily on the
  first publish, so the backend starts even if the broker is down, but publishing then fails.
- **Exchange**: `todo.tasks` (topic, durable). The exchange, queues and bindings are declared by
  todo-infrastructure (`definitions.json`); this service only publishes.
- **Events** (published only for users with a Telegram profile):

  | Routing key     | Event type             | Published when                  | `data`                                                                 |
  |-----------------|------------------------|---------------------------------|------------------------------------------------------------------------|
  | `tasks.created` | `todo.task.created.v1` | a task is created               | `task_id`, `tg_id`, `title`, `deadline`                                |
  | `tasks.updated` | `todo.task.updated.v1` | a task is updated (PUT / PATCH) | `task_id`, `tg_id`, `title`, `body`, `completed`, `deadline`, `category` |
  | `tasks.deleted` | `todo.task.deleted.v1` | a task is deleted               | `task_id`, `tg_id`, `title`                                            |

  `category` is the category's `urgency` slug; `completed` is a boolean. Event types live in
  `todo/events.py`, routing keys in `todo/producers.py` (`TaskRoutingKey`).

- **Format**: [CloudEvents 1.0](https://cloudevents.io/) JSON, persistent delivery:

  ```json
  {
    "specversion": "1.0",
    "id": "3f2b8c1e-7a4d-4f0e-9b6a-2d1c5e8f7a90",
    "source": "todo-api",
    "type": "todo.task.created.v1",
    "time": "2026-10-27T14:30:00+00:00",
    "subject": "tasks/42",
    "datacontenttype": "application/json",
    "data": {
      "task_id": 42,
      "tg_id": 1165414400,
      "title": "Buy milk",
      "deadline": "2026-10-28T18:00:00+00:00"
    }
  }
  ```

The event type and payload are a contract with consumers: todo-bot keeps its own copy of the
payload models with all fields required. Messages already waiting in the queue keep the format
they were published with. Breaking changes are meant to get a new event version (`...v2`).

## API overview

Base URL prefix: `/api/` for tasks, `/auth/` for registration and tokens.

| Area  | Example paths                                                                                                                                 |
| ----- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| Tasks | `GET api/tasks/`, `POST api/tasks/`, `GET api/tasks/<id>`, `PUT/PATCH api/tasks/<id>`, `DELETE api/tasks/<id>`                                |
| Auth  | `POST auth/tg/register/`, `POST auth/web/register/`, `POST auth/token/`, `POST auth/token/refresh/`, `POST auth/token/blacklist/`             |

The trailing slash on task routes is optional: `api/tasks/5` and `api/tasks/5/` both work.

Interactive documentation:

- **OpenAPI schema**: `/schema/`
- **Swagger UI**: `/schema/swagger-ui/`

Django admin (Unfold theme): `/admin/`

CORS is preconfigured for Vite dev origins (`localhost:5173`); extend `CORS_ALLOWED_ORIGINS` in settings if your frontend uses another URL.

## Development tooling

- **Ruff**: `uv run ruff check` (see `pyproject.toml`)
- **pre-commit**: install hooks with `pre-commit install` and run `pre-commit run --all-files`
