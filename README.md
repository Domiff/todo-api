# ToDo API

A **Django REST API** for task management. Users register (web or Telegram), authenticate with **JWT**, and manage tasks
with categories, deadlines, and completion status.

## Features

- **Tasks**: create, list, update, delete; optional filtering and detail by id.
- **Categories**: urgency-based categories linked to tasks.
- **Auth**: Simple JWT (access/refresh, blacklist on rotation); separate registration flows for Telegram and web profiles.
- **API docs**: OpenAPI schema and **Swagger UI** (drf-spectacular).

## Tech stack

| Layer          | Technologies                                                       |
|----------------|--------------------------------------------------------------------|
| API            | Django 6, Django REST Framework, async views (adrf), Daphne (ASGI) |
| Auth           | djangorestframework-simplejwt                                      |
| Database       | PostgreSQL (Docker / production-style); SQLite when `DEBUG=True`   |
| Proxy          | Nginx (reverse proxy, SSL, static files)                           |
| Tooling        | uv, Ruff, pre-commit                                               |
| Infrastructure | Docker Compose: Grafana, Loki, Promtail (logs/metrics plumbing)    |


## Application structure

### Repository tree

```text
.
├── backend/
│   ├── manage.py
│   ├── todo_manager/                 # Django project (settings, routing, ASGI)
│   │   ├── asgi.py
│   │   ├── config.py                 # env-driven settings (pydantic)
│   │   ├── settings.py
│   │   ├── urls.py                   # mounts /api/, /auth/, /admin/, /schema/
│   │   └── wsgi.py
│   ├── todo/                         # Tasks & categories
│   │   ├── migrations/
│   │   ├── serializers/
│   │   ├── models.py
│   │   ├── urls.py
│   │   ├── utils.py
│   │   └── views.py                  # async list/detail CRUD (adrf)
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

### `.env.django`

| Variable                                            | Purpose                                                                      |
|-----------------------------------------------------|------------------------------------------------------------------------------|
| `DJANGO_SECRET_KEY`                                 | Django secret                                                                |
| `DJANGO_DEBUG`                                      | `True` for local dev; `False` for production                                 |
| `ALLOWED_HOSTS`                                     | Comma-separated list of allowed hosts (e.g. `localhost,127.0.0.1`)           |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | Postgres credentials                                                         |
| `POSTGRES_HOST`, `POSTGRES_PORT`                    | e.g. `pg` and `5432` in Compose; `127.0.0.1` when Postgres runs on the host |

## Local development (without Docker)

1. Install dependencies:
   ```bash
   uv sync
   ```

2. Create `.env.django` at the repo root with at minimum:
   ```env
   DJANGO_SECRET_KEY=your-secret-key
   DJANGO_DEBUG=True
   ALLOWED_HOSTS=localhost,127.0.0.1
   ```
   With `DEBUG=True` the project uses SQLite — no Postgres required.

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
| Grafana          | 3000       | Default admin user/password in `docker-compose.yml` (change for production) |
| Loki             | 3100       | Log aggregation                                                             |
| Promtail         | 9080       | Log shipping                                                                |

Ensure `.env.django` sets `POSTGRES_HOST=pg`.

All services run on the external Docker network **`todo-network`** — create it once before the first start:

```bash
docker network create todo-network
```

## API overview

Base URL prefix: `/api/` for tasks, `/auth/` for registration and tokens.

| Area  | Example paths                                                                                                                                 |
| ----- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| Tasks | `GET api/list/`, `GET api/list/<id>`, `POST api/create/`, `PUT/PATCH api/update/<id>`, `DELETE api/delete/<id>`                               |
| Auth  | `POST auth/tg/register/`, `POST auth/web/register/`, `POST auth/token/`, `POST auth/token/refresh/`, `POST auth/token/blacklist/`             |

Interactive documentation:

- **OpenAPI schema**: `/schema/`
- **Swagger UI**: `/schema/swagger-ui/`

Django admin (Unfold theme): `/admin/`

CORS is preconfigured for Vite dev origins (`localhost:5173`); extend `CORS_ALLOWED_ORIGINS` in settings if your frontend uses another URL.

## Development tooling

- **Ruff**: `uv run ruff check` (see `pyproject.toml`)
- **pre-commit**: install hooks with `pre-commit install` and run `pre-commit run --all-files`
