FROM python:3.13-slim-trixie AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /backend

COPY ../pyproject.toml ./

ENV UV_PROJECT_ENVIRONMENT=/usr/local

ENV UV_SYSTEM_PYTHON=1

RUN uv sync --group backend


FROM python:3.13-slim-trixie

WORKDIR /backend

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH=/usr/local/bin:$PATH

COPY --from=builder /usr/local /usr/local

COPY ../wait-for-it.sh /wait-for-it.sh
RUN chmod +x /wait-for-it.sh

COPY backend /backend

CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "todo_manager.asgi:application"]
