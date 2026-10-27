# ToDo API

A **Django REST API** for task management. Users register (web or Telegram), authenticate with **JWT**, and manage tasks
with categories, deadlines, and completion status.

## Features

- **Tasks**: full CRUD through a single viewset; each user sees only their own tasks.
- **Categories**: urgency-based categories linked to tasks.
- **Auth**: Simple JWT (access/refresh, blacklist on rotation); separate registration flows for Telegram and web profiles.
- **API docs**: OpenAPI schema and **Swagger UI** (drf-spectacular).
- **Task events**: creating a task publishes a `todo.task.created.v1` event to RabbitMQ; the
  [todo-bot](https://github.com/Domiff/todo-bot) service consumes it and notifies the owner in Telegram.

## Tech stack

| Layer          | Technologies                                                       |
|----------------|--------------------------------------------------------------------|
| API            | Django 6, Django REST Framework, async views (adrf), Daphne (ASGI) |
| Auth           | djangorestframework-simplejwt                                      |
| Database       | PostgreSQL (Docker / production-style); SQLite when `DEBUG=True`   |
| Messaging      | RabbitMQ (aio-pika), events in CloudEvents 1.0 JSON format         |
| Proxy          | Nginx (reverse proxy, SSL, static files)                           |
| Tooling        | uv, Ruff, pre-commit                                               |
| Infrastructure | Docker Compose: Grafana, Loki, Promtail (logs/metrics plumbing)    |


## Application structure

### Repository tree

```text
.
├── backend/
│   ├── manage.py
│   ├── core/                         # Django project (settings, routing, ASGI)
│   │   ├── asgi.py
│   │   ├── messaging/                # RabbitMQ infrastructure shared by all apps
│   │   │   ├── connection.py         # one robust connection + channel per process
│   │   │   ├── events.py             # Event: CloudEvents envelope, serialized to JSON
│   │   │   ├── topology.py           # exchanges declared by this service
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
├── grafana/                          # Datasource provisioning + Loki/Promtail configs
│   ├── datasources.yml
│   ├── loki-config.yml
│   └── promtail-config.yml
├── nginx/
│   └── todo.conf                     # Nginx virtual host (proxy_pass → Unix socket)
├── Dockerfile
├── Justfile
├── wait-for-it.sh
├── docker-compose.yml
├── pyproject.toml                    # uv dependency groups: backend, dev
└── uv.lock
```

## Requirements

- **Python 3.13+**
- **[uv](https://docs.astral.sh/uv/)** (recommended) for installs and scripts
- **Docker** / Docker Compose for the full stack (Postgres, Nginx, backend, optional observability)

## Configuration

Create an env file at the **repository root** (it is gitignored; do not commit secrets):

### `.env`

| Variable                                            | Purpose                                                                      |
|-----------------------------------------------------|------------------------------------------------------------------------------|
| `DJANGO_SECRET_KEY`                                 | Django secret                                                                |
| `DJANGO_DEBUG`                                      | `True` for local dev; `False` for production                                 |
| `ALLOWED_HOSTS`                                     | Comma-separated list of allowed hosts (e.g. `localhost,127.0.0.1`)           |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | Postgres credentials                                                         |
| `POSTGRES_HOST`, `POSTGRES_PORT`                    | e.g. `pg` and `5432` in Compose; `127.0.0.1` when Postgres runs on the host |
| `RABBITMQ_USER`, `RABBITMQ_PASSWORD`                | RabbitMQ credentials (required)                                              |
| `RABBITMQ_HOST`, `RABBITMQ_PORT`                    | e.g. `todo-bot-rabbitmq` and `5672` in Compose (see [Messaging](#messaging)) |

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

## Docker Compose

From the repository root:

```bash
docker compose up --build
```

Typical ports:

| Service          | Port       | Notes                                                                       |
|------------------|------------|-----------------------------------------------------------------------------|
| Nginx            | 8080 / 443 | HTTP and HTTPS entry point; proxies to Daphne via Unix socket               |
| Backend (Daphne) | (internal) | Communicates with Nginx via `/tmp/daphne.sock`                              |
| Postgres         | 5432       | Persisted volume `pg_data`                                                  |
| RabbitMQ         | 5672 / 15672 | AMQP / management UI; currently unused, events go to `todo-bot-rabbitmq`  |
| Grafana          | 3000       | Default admin user/password in `docker-compose.yml` (change for production) |
| Loki             | 3100       | Log aggregation                                                             |
| Promtail         | 9080       | Log shipping                                                                |

Ensure `.env` sets `POSTGRES_HOST=pg`.

All services run on the external Docker network **`todo-network`** — create it once before the first start:

```bash
docker network create todo-network
```

## Messaging

The API publishes domain events to RabbitMQ so other services can react without calling the API.

- **Broker**: the RabbitMQ instance from the todo-bot stack (`todo-bot-rabbitmq`), reached over
  `todo-network`. Start todo-bot before creating tasks, otherwise publishing fails.
- **Exchange**: `todo.tasks` (`direct`, durable), declared by this service on connect.
  Queues and bindings belong to consumers.
- **Events**:

  | Routing key     | Event type             | Published when                                        |
  |-----------------|------------------------|-------------------------------------------------------|
  | `tasks.created` | `todo.task.created.v1` | a task is created by a user with a Telegram profile  |

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

The event type and payload are a contract with consumers: add optional fields freely, but publish
a new version (`...v2`) for breaking changes.

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
