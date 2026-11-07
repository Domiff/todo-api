# ToDo API

A **Django REST API** for task management. Users register (from the web app or the Telegram bot), authenticate with **JWT**, and manage tasks
with categories, deadlines, and completion status.

## Features

- **Tasks**: full CRUD through a single viewset; each user sees only their own tasks.
- **Priorities**: every task has a priority: low, middle (default) or high.
- **Categories**: a predefined list (work, study, personal, home, shopping, health, finance, other); a task may have none.
- **Auth**: Simple JWT (access/refresh, blacklist on rotation); one registration endpoint for the web app and the Telegram bot.
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
| Infrastructure | Postgres, RabbitMQ, the Caddy reverse proxy and logging live in [todo-infrastructure](#infrastructure) |


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
│       ├── models.py                 # Profile (tg_id, email)
│       ├── permissions.py            # IsBot: checks the X-Bot-Key header
│       ├── serializers.py            # RegisterSerializer, LinkTelegramSerializer
│       ├── urls.py
│       └── views.py
│
├── Dockerfile
├── Justfile
├── docker-compose.yml                # backend only; infrastructure and the proxy are in todo-infrastructure
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
| `ALLOWED_HOSTS`                                     | Comma-separated list of allowed hosts (e.g. `localhost,127.0.0.1`; add the domain in production) |
| `CORS_ALLOWED_ORIGINS`                              | Comma-separated frontend origins (e.g. `http://localhost:5173`)              |
| `CSRF_TRUSTED_ORIGINS`                              | Comma-separated origins with scheme for forms and the admin (e.g. `https://api.example.com`) |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | Same credentials as in todo-infrastructure's `.env`                          |
| `POSTGRES_HOST`, `POSTGRES_PORT`                    | `todo-pg` and `5432` in Docker; `127.0.0.1` when running on the host         |
| `BOT_API_KEY`                                       | Shared secret with todo-bot; without it `tg_id` is rejected                  |
| `RABBITMQ_USER`, `RABBITMQ_PASSWORD`                | Same credentials as in todo-infrastructure's `.env` (required)               |
| `RABBITMQ_HOST`, `RABBITMQ_PORT`                    | `todo-rabbitmq` and `5672` in Docker; `127.0.0.1` when running on the host   |

HTTPS settings. Their defaults are for production, so they must be turned off when the API is opened over plain HTTP:

| Variable                         | Default    | Local (HTTP) | Purpose                                              |
|----------------------------------|------------|--------------|------------------------------------------------------|
| `SECURE_SSL_REDIRECT`            | `True`     | `False`      | redirect every `http` request to `https`             |
| `CSRF_COOKIE_SECURE`             | `True`     | `False`      | send the CSRF cookie over HTTPS only                 |
| `SESSION_COOKIE_SECURE`          | `True`     | `False`      | send the session cookie over HTTPS only (admin login) |
| `SECURE_HSTS_SECONDS`            | `31536000` | `0`          | tell browsers to use only HTTPS for this host (1 year) |
| `SECURE_HSTS_INCLUDE_SUBDOMAINS` | `True`     | `False`      | apply HSTS to all subdomains                         |
| `SECURE_HSTS_PRELOAD`            | `True`     | `False`      | allow adding the domain to the browsers' HSTS preload list |

With `SECURE_SSL_REDIRECT=True` over HTTP Django answers with a permanent `301` to `https`, and the
browser caches it: after setting it to `False`, open the site in a private window or clear the
browser cache. Turn HSTS on only when HTTPS works on the domain: browsers then refuse plain HTTP for
it for `SECURE_HSTS_SECONDS`.

Behind the proxy HTTPS ends at Caddy, and Django learns the original scheme from the
`X-Forwarded-Proto` header (`SECURE_PROXY_SSL_HEADER` in `core/settings/security.py`).

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

Postgres, RabbitMQ, Redis, the Caddy reverse proxy and logging (Grafana, Loki, Alloy) are not part
of this repository. They run in the separate **todo-infrastructure** stack, and this service
connects to it over the external Docker network **`todo-network`**.

Start order: **todo-infrastructure → todo-api → todo-bot**. This compose file has no `depends_on`
on Postgres or RabbitMQ (Compose cannot depend on another project), so the infrastructure must be
up and healthy before the backend starts.

## Docker Compose

1. Start todo-infrastructure. It also expects the `todo-network` network and the `todo-static`
   volume (see its README).

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

5. Open the API through the proxy: `http://localhost:8080` locally (`SITE_ADDRESS=:8080` in
   todo-infrastructure) or the domain in production.

| Service          | Container      | Port                  | Notes                                                        |
|------------------|----------------|-----------------------|--------------------------------------------------------------|
| Backend (Daphne) | `todo-backend` | 8000 (not published)  | Reachable as `todo-backend:8000` from other services in `todo-network` |

### Static files and the reverse proxy

Daphne does not serve static files, so the backend is not published to the host and is opened only
through Caddy from todo-infrastructure. Caddy answers `/static/*` itself and forwards everything
else to `todo-backend:8000`.

```
browser ──> todo-caddy ──/static/*──> volume todo-static
                       └─everything else──> todo-backend:8000
```

- `STATIC_ROOT` is `backend/static` (`/backend/static` in the container).
- The external volume `todo-static` is mounted there, and the container runs `collectstatic` before
  Daphne on every start, so the volume always has the static files of the running version.
- Caddy mounts the same volume read-only and serves it.

The `static/` folder on the host is not used by Docker (only `backend/` is copied into the image)
and is gitignored.

Check that static files are served:

```bash
curl -I http://localhost:8080/static/admin/css/base.css
```

`404` means the volume is empty: check that the backend started and ran `collectstatic`
(`docker logs todo-backend`).

## Messaging

The API publishes domain events to RabbitMQ so other services can react without calling the API.

- **Broker**: `todo-rabbitmq` from todo-infrastructure. The connection is opened lazily on the
  first publish, so the backend starts even if the broker is down, but publishing then fails.
- **Exchange**: `todo.tasks` (topic, durable). The exchange, queues and bindings are declared by
  todo-infrastructure (`definitions.json`); this service only publishes.
- **Events** (published only for users with a Telegram profile, and not for requests with `X-Client: Telegram`):

  | Routing key     | Event type             | Published when                  | `data`                                                                 |
  |-----------------|------------------------|---------------------------------|------------------------------------------------------------------------|
  | `tasks.created` | `todo.task.created.v1` | a task is created               | `task_id`, `tg_id`, `title`, `deadline`                                |
  | `tasks.updated` | `todo.task.updated.v1` | a task is updated (PUT / PATCH) | `task_id`, `tg_id`, `title`, `body`, `completed`, `deadline`, `priority`, `category` |
  | `tasks.deleted` | `todo.task.deleted.v1` | a task is deleted               | `task_id`, `tg_id`, `title`                                            |

  `category` is the category's slug (an empty string if the task has none); `priority` is 1 (low), 2 (middle) or 3 (high); `completed` is a boolean. Event types live in
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
| Categories | `GET api/categories/`, `GET api/categories/<slug>` (read-only)                                                                        |
| Auth  | `POST auth/register/`, `POST auth/tg/link/`, `POST auth/token/`, `POST auth/token/refresh/`, `POST auth/token/blacklist/`             |

The trailing slash on task routes is optional: `api/tasks/5` and `api/tasks/5/` both work.

When creating or updating a task, `priority` is `1`, `2` or `3` (optional, defaults to `2`) and `category` is a category slug
such as `work` (optional, `null` for no category). Categories are created by a migration and managed in the admin.

Registration takes `username`, `password` and an optional `email`. A `tg_id` is accepted only from the bot, with a matching
`X-Bot-Key` header; the same applies to `POST auth/tg/link/`, which links Telegram to the logged-in user. Set the same `BOT_API_KEY`
in the `.env` of todo-api and todo-bot.

Interactive documentation:

- **OpenAPI schema**: `/schema/`
- **Swagger UI**: `/schema/swagger-ui/`

Django admin (Unfold theme): `/admin/`

CORS origins come from `CORS_ALLOWED_ORIGINS` in `.env` (e.g. `http://localhost:5173` for the Vite dev server).

## Development tooling

- **Ruff**: `uv run ruff check` (see `pyproject.toml`)
- **pre-commit**: install hooks with `pre-commit install` and run `pre-commit run --all-files`
