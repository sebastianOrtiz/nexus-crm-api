# CLAUDE.md — nexus-crm-api

Instrucciones para Claude Code al trabajar en este repositorio.

## Descripción

Backend REST API para NexusCRM: CRM multi-tenant construido con FastAPI,
SQLAlchemy 2.0 async, PostgreSQL 16 y JWT. Desplegado en `api.sebasing.dev`.

## Stack

| Componente | Tecnología |
|---|---|
| Framework | FastAPI 0.115 |
| ORM | SQLAlchemy 2.0 (async) |
| Driver DB | asyncpg |
| Migraciones | Alembic |
| Validación | Pydantic v2 |
| Auth | bcrypt + python-jose (JWT) |
| Tests | pytest + httpx (AsyncClient) |
| Linting | ruff + mypy |

## Arquitectura de capas

```
Router → Dependencies (DI) → Service → Repository → Database
               │
          Auth Middleware
          (JWT + tenant context)
```

- **Router** (`src/api/v1/routers/`): Define endpoints, valida input con Pydantic, convierte excepciones de dominio a HTTP.
- **Dependencies** (`src/api/v1/dependencies.py`): FastAPI DI para auth, sesión de DB, permisos de rol.
- **Service** (`src/services/`): Lógica de negocio y permisos. NUNCA importa FastAPI.
- **Repository** (`src/repositories/`): Queries SQLAlchemy. SIEMPRE filtra por `organization_id`.
- **Models** (`src/models/`): SQLAlchemy ORM models. Schema `crm`.
- **Schemas** (`src/schemas/`): Pydantic v2 para request/response.

## Principios obligatorios

1. **SOLID y KISS**: Sin god objects, sin lógica en routers, sin queries en servicios.
2. **Multi-tenancy**: Todo repository method que devuelve datos de negocio DEBE filtrar por `organization_id`.
3. **Sin strings mágicos**: Usar enums de `src/core/enums.py` y constantes de `src/core/constants.py`.
4. **Excepciones de dominio**: Los servicios lanzan `NotFoundError`, `ForbiddenError`, `ConflictError`. Los routers los convierten a HTTP.
5. **Type hints**: Todas las funciones públicas deben tener type hints completos.
6. **Docstrings**: Todas las clases y funciones públicas deben tener docstrings estilo Google/NumPy.

## Comandos frecuentes

```bash
# Instalar dependencias
pip install -e ".[dev]"

# Correr el servidor en desarrollo
python -m uvicorn src.main:app --reload --port 8000

# Aplicar migraciones
alembic upgrade head

# Crear nueva migración (después de cambiar modelos)
alembic revision --autogenerate -m "descripción del cambio"

# Correr tests
pytest tests/ -v

# Correr tests con cobertura
pytest tests/ --cov=src --cov-report=html

# Linting
ruff check src/ tests/
ruff format src/ tests/

# Type checking
mypy src/
```

## Variables de entorno

Ver `.env.example` para la lista completa. Copiar a `.env` y ajustar valores.

El `JWT_SECRET_KEY` **NUNCA** debe ser el valor de ejemplo en producción.

## Estructura de directorios

```
src/
├── core/
│   ├── config.py        # Settings (pydantic-settings)
│   ├── constants.py     # Constantes (JWT expiry, page size, etc.)
│   ├── database.py      # Engine async + get_session dependency
│   ├── enums.py         # Enums de dominio
│   ├── exceptions.py    # Excepciones de dominio
│   └── security.py      # Hash de passwords + JWT
├── models/              # SQLAlchemy ORM models (schema: crm)
├── schemas/             # Pydantic v2 request/response schemas
├── repositories/        # Data access (siempre filtran por org_id)
├── services/            # Lógica de negocio + permisos
├── api/
│   └── v1/
│       ├── dependencies.py  # get_current_user, role guards
│       ├── router.py        # Registro de todos los routers
│       └── routers/         # Un archivo por recurso
├── middleware/
│   └── logging.py       # Request/response logging
└── main.py              # App factory (create_app)

alembic/
├── env.py
├── script.py.mako
└── versions/

tests/
├── conftest.py          # Fixtures: DB, client, users, tokens
├── unit/                # Tests sin DB
└── integration/         # Tests con DB (usan test session)
```

## Roles y permisos

| Acción | Owner | Admin | Sales Rep | Viewer |
|---|---|---|---|---|
| Gestionar organización | ✅ | ❌ | ❌ | ❌ |
| Gestionar usuarios | ✅ | ✅ | ❌ | ❌ |
| Configurar pipeline | ✅ | ✅ | ❌ | ❌ |
| CRUD contactos/empresas | ✅ | ✅ | ✅ (asignados) | ❌ |
| CRUD deals | ✅ | ✅ | ✅ (asignados) | ❌ |
| CRUD actividades | ✅ | ✅ | ✅ (propias) | ❌ |
| Ver dashboard | ✅ | ✅ | ✅ | ✅ |

## Consideraciones de seguridad

- Passwords hasheados con bcrypt (rounds=12).
- JWT access token: 15 min. Refresh token: 7 días.
- El login usa el mismo mensaje de error para "usuario no existe" y "password incorrecto" (previene enumeración de usuarios).
- Todos los endpoints protegidos requieren `Authorization: Bearer <token>`.
- Los IDs son UUID v4 generados en Python.
- Multi-tenancy por `organization_id` en cada query — nunca se devuelven datos de otro tenant.
