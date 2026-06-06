set dotenv-filename := ".env"

install:
    uv sync --group dev

run:
    cd backend && uv run python manage.py runserver

run-asgi:
    cd backend && uv run daphne todo_manager.asgi:application

migrate:
    cd backend && uv run python manage.py migrate

makemigrations app="":
    cd backend && uv run python manage.py makemigrations {{ app }}

lint:
    uv run ruff check .

lint-fix:
    uv run ruff check --fix .

fmt:
    uv run ruff format .

up:
    docker compose up --build

down:
    docker compose down
