# RepoSage

> AI-powered GitHub repository intelligence platform.

[![Python](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-blue.svg)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.x-blue.svg)](https://www.typescriptlang.org/)
[![Docker](https://img.shields.io/badge/Docker-ready-blue.svg)](https://www.docker.com/)

---

## Table of Contents

- [Overview](#overview)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Environment Variables](#environment-variables)
- [Development](#development)
- [Testing](#testing)
- [Contributing](#contributing)

---

## Overview

RepoSage connects to your GitHub repositories and runs AI-powered analysis pipelines to generate insights, detect drift, and produce automated documentation. The platform is built for teams managing multiple repositories across organizations.

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | FastAPI 0.115, Python 3.12, SQLAlchemy 2.0 (async), Alembic |
| **Background Workers** | Celery 5, Redis 7 |
| **Database** | PostgreSQL 16 |
| **Frontend** | React 18, TypeScript 5, Vite, TailwindCSS, shadcn/ui |
| **State Management** | TanStack Query, Zustand |
| **Container** | Docker, Docker Compose |
| **Reverse Proxy** | Nginx |

---

## Prerequisites

- Docker 24+ and Docker Compose v2
- Node.js 20+ (for local frontend dev)
- Python 3.12+ (for local backend dev)
- Git

---

## Quick Start

### 1. Clone and configure environment

```bash
git clone https://github.com/your-org/reposage.git
cd reposage
cp .env.example .env
```

Edit `.env` with your values (see [Environment Variables](#environment-variables)).

### 2. Start all services

```bash
docker compose up --build
```

| Service | URL |
|---|---|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| API Docs (ReDoc) | http://localhost:8000/redoc |
| Flower (Celery UI) | http://localhost:5555 |

### 3. Run database migrations

```bash
docker compose exec backend alembic upgrade head
```

### 4. Seed development data (optional)

```bash
docker compose exec backend python scripts/seed_db.py
```

---

## Project Structure

```
reposage/
├── backend/          # FastAPI application (Clean Architecture)
├── frontend/         # React SPA (Feature Modules)
├── docker/           # Nginx, PostgreSQL, Redis configs
├── docs/             # Architecture docs, ADRs, guides
├── .github/          # Issue templates, PR template, Actions
├── docker-compose.yml
├── docker-compose.prod.yml
└── .env.example
```

See [`docs/architecture/overview.md`](docs/architecture/overview.md) for the full architectural breakdown.

---

## Environment Variables

Copy `.env.example` to `.env` at the root. All variables are documented in [`docs/guides/env-variables.md`](docs/guides/env-variables.md).

**Critical variables to set:**

| Variable | Description |
|---|---|
| `SECRET_KEY` | JWT signing key — generate with `openssl rand -hex 32` |
| `DATABASE_URL` | PostgreSQL async DSN |
| `REDIS_URL` | Redis DSN |
| `GITHUB_APP_ID` | GitHub App ID (for webhook integration) |
| `GITHUB_PRIVATE_KEY` | GitHub App private key (PEM format) |

---

## Development

### Backend only

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install uv
uv pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

### Frontend only

```bash
cd frontend
npm install
npm run dev
```

### Pre-commit hooks

```bash
pip install pre-commit
pre-commit install
```

---

## Testing

### Backend

```bash
cd backend
pytest tests/ -v --cov=app --cov-report=term-missing
```

### Frontend

```bash
cd frontend
npm run test
npm run type-check
```

---

## Contributing

Please read [CONTRIBUTING.md](docs/guides/contributing.md) before opening a pull request.

Use the GitHub issue templates for bug reports and feature requests.

---

## License

MIT © RepoSage Contributors
