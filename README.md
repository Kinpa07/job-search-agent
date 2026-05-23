# Job Search Agent

An AI-powered job search pipeline that discovers, scores, and tracks job listings.

## Stack

- **Backend:** FastAPI + PostgreSQL + Celery + Redis
- **AI:** LangGraph + LangChain + Claude (Anthropic)
- **Frontend:** React 19 + TypeScript + TanStack Query + Zustand
- **Extension:** Chrome Manifest V3

## Setup

```bash
cp .env.example .env
# Fill in your API keys

cd backend
poetry install
docker compose -f docker/docker-compose.yml up -d
poetry run alembic upgrade head
poetry run uvicorn src.app.main:app --reload
```

Frontend and extension setup documented in later modules.
