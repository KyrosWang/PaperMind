# HPC development

HPC is a development or batch-compute environment, not the persistent PaperMind server. Do not run
PostgreSQL, Redis, or long-lived workers on ordinary SLURM compute jobs unless site policy explicitly
supports services.

```bash
git clone <your-repository-url> PaperMind
cd PaperMind
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
pytest

cd frontend
pnpm install --frozen-lockfile
pnpm dev
```

Conda may replace `venv`. Node 22 and pnpm 11 are expected. Point `DATABASE_URL`, `REDIS_URL`, and
`GROBID_URL` at administrator-approved services; use SSH tunnels only if site policy permits them.
Basic unit tests use SQLite and mocks and need no services or credentials. Do not assume compute
nodes can reach PyPI, npm, Zotero, or OpenAI—prepare a wheelhouse and pnpm store on an approved
internet-connected login or transfer node.

Docker is only the preferred deployment packaging. Source development needs no Docker. If the site
supports Apptainer/Singularity, build images off-cluster (or with a sanctioned remote builder),
convert the backend/worker and GROBID images to SIF, bind a writable `DATA_ROOT`, and inject secrets
at runtime. PostgreSQL and Redis should remain external persistent services.

