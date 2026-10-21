# Deployment

## Home server with Docker Compose

1. Install Docker Engine with the Compose plugin.
2. Clone the repository and copy `.env.example` to `.env`.
3. Generate strong values for `POSTGRES_PASSWORD` and `APP_API_KEY`; add Zotero/OpenAI settings.
4. Run `docker compose up -d --build`.
5. Seed optional metadata with `docker compose exec backend python -m app.cli seed-demo`.
6. Browse to `http://server:3000` over the private network.

Named volumes persist PostgreSQL, Redis, GROBID models, and paper files. Back up both
`postgres_data` and `paper_data` together. Test restores. Never commit `.env`.

## Tailscale

Install Tailscale on the server and client devices, keep Compose ports bound to loopback, and use
`tailscale serve --bg 3000` (or an equivalent Tailscale reverse proxy policy) to expose only the
frontend inside the tailnet. The Next.js server proxy holds `APP_API_KEY` and reaches the backend on
the internal Compose network. Do not publish PostgreSQL 5432, Redis 6379, GROBID 8070, or the worker.
Apply tailnet ACLs so only the intended user/devices can reach PaperMind.

The shared API key is defense in depth for a single-user private deployment, not internet-grade
identity. Public hosting requires TLS, real user sessions, CSRF protection, rate limiting, and a
secrets manager; it is outside V1 scope.

## Source deployment

Run `alembic upgrade head`, then start `uvicorn app.main:app` and
`celery -A app.worker.celery_app worker`. Start Next.js with `pnpm build && pnpm start`. Supply all
service URLs and `DATA_ROOT` through the environment and use a process supervisor.

