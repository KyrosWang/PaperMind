.PHONY: dev up down migrate test lint frontend-install seed

dev:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build

up:
	docker compose up -d --build

down:
	docker compose down

migrate:
	cd backend && alembic upgrade head

test:
	pytest

lint:
	ruff check backend tests && ruff format --check backend tests
	cd frontend && pnpm lint && pnpm typecheck

frontend-install:
	cd frontend && pnpm install

seed:
	python -m app.cli seed-demo

