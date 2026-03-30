# NexusCRM API

Multi-tenant CRM REST API built with FastAPI, SQLAlchemy 2.0, and PostgreSQL. Provides JWT authentication, role-based access control, and integrations with the Event-Driven and Semantic Search services.

## Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI |
| ORM | SQLAlchemy 2.0 (async) |
| Database | PostgreSQL 16 (schema: `crm`) |
| Auth | JWT (access 15min + refresh 7d) |
| Migrations | Alembic |
| Validation | Pydantic v2 |

## Key Features

- **Multi-tenancy** -- all tables scoped by `organization_id`, enforced at query level
- **RBAC** -- four roles: Owner, Admin, Sales Rep, Viewer
- **Deal pipeline** -- configurable stages with drag-and-drop support, full stage history tracking
- **Event service integration** -- triggers onboarding flow on user registration
- **Search service integration** -- proxies semantic search queries to the search API

## API Endpoints

| Group | Endpoints |
|---|---|
| Auth | register, login, refresh, logout |
| Contacts | CRUD + list with filters, pagination, search |
| Companies | CRUD + list contacts by company |
| Deals | CRUD + move stage + stage history |
| Activities | CRUD (call, email, meeting, note) |
| Pipeline | CRUD pipeline stages |
| Dashboard | Aggregated metrics and charts |
| Users | CRUD + invite + profile |
| Events proxy | `GET /api/v1/events/*` (proxied to event service) |
| Search proxy | `POST /api/v1/search/*` (proxied to semantic search) |

API docs available at `/docs` (Swagger UI) when running.

## Architecture

Layered architecture: **Router -> Service -> Repository -> Database**

Each layer has a single responsibility: routers handle HTTP, services contain business logic, repositories manage data access. All queries are scoped to the authenticated user's tenant.

## Running

```bash
pip install -e ".[dev]" --break-system-packages
alembic upgrade head
python -m uvicorn src.main:app --reload --port 8000 --host 0.0.0.0
```

## Seed Demo Data

```bash
python -m scripts.seed
```

Creates a full demo environment. Login: `demo@nexuscrm.dev` / `Demo1234!`

## Tests

298 tests with 91% coverage.

```bash
pytest tests/ -v
pytest tests/ --cov=src --cov-report=html
```

## Part of sebasing.dev

| Project | Stack |
|---|---|
| [portfolio-web](../portfolio-web) | Next.js, TypeScript, Tailwind |
| **nexus-crm-api** (this) | FastAPI, SQLAlchemy, PostgreSQL |
| [nexus-crm-dashboard](../nexus-crm-dashboard) | Angular, TypeScript, Tailwind |
| [event-driven-service](../event-driven-service) | Go, Gin, Redis Streams |
| [semantic-search-api](../semantic-search-api) | FastAPI, ChromaDB, sentence-transformers |

## License

MIT
