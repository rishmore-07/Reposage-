# RepoSage — Production-Grade Architecture

> **Principal Software Architect Review**
> Designed for longevity, scalability, and team maintainability.
> Zero business logic. Pure architecture.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Architectural Principles](#2-architectural-principles)
3. [High-Level Architecture](#3-high-level-architecture)
4. [Backend Folder Structure](#4-backend-folder-structure)
5. [Frontend Folder Structure](#5-frontend-folder-structure)
6. [Docker Structure](#6-docker-structure)
7. [Documentation Structure](#7-documentation-structure)
8. [Folder-by-Folder Rationale](#8-folder-by-folder-rationale)
9. [Every Architectural Decision Explained](#9-every-architectural-decision-explained)
10. [Future Extension Points](#10-future-extension-points)
11. [Data Flow Diagrams](#11-data-flow-diagrams)

---

## 1. System Overview

RepoSage is an AI-powered GitHub repository intelligence platform. The architecture is designed to:

- Support **thousands of repositories** across **multiple organizations and users**
- Run **background AI pipelines** without blocking user-facing APIs
- Integrate with **GitHub App** webhooks asynchronously
- Plug in **LangGraph AI agents** without refactoring core code
- Scale individual services independently via Docker

---

## 2. Architectural Principles

| Principle | Decision |
|---|---|
| **Clean Architecture** | Strict layer separation: Domain → Application → Infrastructure → Presentation |
| **Single Responsibility** | Every module/class does exactly one thing |
| **Dependency Inversion** | All concrete implementations are injected, never directly instantiated |
| **Feature Modules** | Code grouped by domain feature, not technical layer |
| **12-Factor App** | All config from environment variables, stateless processes |
| **Ports & Adapters** | Core domain never imports infrastructure code |
| **Explicit over Implicit** | No magic; every dependency is visible |
| **Open/Closed** | Extension by adding new modules, not mutating existing ones |

---

## 3. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                             │
│                                                                 │
│   ┌──────────────────────────────────────────────────────┐     │
│   │           React SPA  (Vite + TypeScript)             │     │
│   │   TailwindCSS · shadcn/ui · TanStack Query           │     │
│   │   React Router · Zustand (future state mgmt)         │     │
│   └──────────────────────┬───────────────────────────────┘     │
└─────────────────────────-│───────────────────────────────────--─┘
                           │ HTTPS / REST + WebSocket
┌──────────────────────────▼───────────────────────────────────---┐
│                        API GATEWAY LAYER                        │
│                                                                 │
│   ┌──────────────────────────────────────────────────────┐     │
│   │           FastAPI Application Server                 │     │
│   │  Auth Middleware · Rate Limiting · CORS · Logging    │     │
│   │  API Key Validation · JWT Validation                 │     │
│   └──────┬────────────────────┬────────────────┬─────────┘     │
└──────────│────────────────────│────────────────│───────────────-┘
           │                    │                │
    ┌──────▼──────┐    ┌────────▼──────┐  ┌─────▼──────────┐
    │  Feature    │    │   GitHub App  │  │  Background    │
    │  Services   │    │   Webhook     │  │  Worker API    │
    │  (Domain)   │    │   Handler     │  │  (Celery)      │
    └──────┬──────┘    └────────┬──────┘  └─────┬──────────┘
           │                    │                │
┌──────────▼────────────────────▼────────────────▼───────────────┐
│                     INFRASTRUCTURE LAYER                        │
│                                                                 │
│  ┌──────────────┐  ┌─────────────┐  ┌──────────┐  ┌────────┐  │
│  │  PostgreSQL  │  │    Redis    │  │  Qdrant  │  │  S3 /  │  │
│  │  (Primary    │  │  (Cache +   │  │  (Vector │  │  MinIO │  │
│  │   Store)     │  │   Queue)    │  │   DB)    │  │  Store)│  │
│  └──────────────┘  └─────────────┘  └──────────┘  └────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                  Celery Workers                          │  │
│  │  repo_clone · embed_code · detect_drift · gen_pr_docs    │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                  AI Pipeline Layer (Future)              │  │
│  │     LangGraph Agents · LangChain · Tree-sitter           │  │
│  │     Gemini LLM · Qdrant Retriever                        │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. Backend Folder Structure

```
backend/
│
├── alembic/                          # Database migration engine
│   ├── versions/                     # Migration scripts (auto-generated)
│   ├── env.py                        # Alembic runtime environment
│   └── alembic.ini                   # Alembic configuration
│
├── app/
│   │
│   ├── api/                          # ── PRESENTATION LAYER ──
│   │   ├── __init__.py
│   │   ├── router.py                 # Root API router (aggregates all feature routers)
│   │   ├── dependencies.py           # Shared FastAPI dependency injectors (DB, Auth, etc.)
│   │   │
│   │   └── v1/                       # Version-namespaced API (future-proof)
│   │       ├── __init__.py
│   │       ├── auth/
│   │       │   ├── __init__.py
│   │       │   └── router.py         # POST /auth/login, /auth/register, /auth/refresh
│   │       ├── users/
│   │       │   ├── __init__.py
│   │       │   └── router.py         # GET/PATCH /users/me, /users/{id}
│   │       ├── organizations/
│   │       │   ├── __init__.py
│   │       │   └── router.py         # CRUD /organizations
│   │       ├── repositories/
│   │       │   ├── __init__.py
│   │       │   └── router.py         # CRUD /repositories, trigger analysis
│   │       ├── api_keys/
│   │       │   ├── __init__.py
│   │       │   └── router.py         # POST/DELETE /api-keys
│   │       ├── webhooks/
│   │       │   ├── __init__.py
│   │       │   └── router.py         # POST /webhooks/github (GitHub App events)
│   │       ├── notifications/
│   │       │   ├── __init__.py
│   │       │   └── router.py         # GET /notifications, PATCH mark-read
│   │       └── billing/
│   │           ├── __init__.py
│   │           └── router.py         # Future: Stripe webhooks, plan management
│   │
│   ├── core/                         # ── CORE CONFIGURATION ──
│   │   ├── __init__.py
│   │   ├── config.py                 # Pydantic BaseSettings (all env vars, no hardcodes)
│   │   ├── security.py               # JWT creation/verification, password hashing
│   │   ├── logging.py                # Structured logging configuration (JSON output)
│   │   ├── exceptions.py             # Custom exception hierarchy (AppError base)
│   │   ├── middleware.py             # CORS, request ID injection, timing middleware
│   │   └── constants.py              # App-wide enums and string constants
│   │
│   ├── db/                           # ── DATABASE INFRASTRUCTURE ──
│   │   ├── __init__.py
│   │   ├── base.py                   # SQLAlchemy DeclarativeBase + metadata
│   │   ├── session.py                # Async engine + session factory (AsyncSession)
│   │   └── init_db.py                # DB initialization script (used in startup)
│   │
│   ├── models/                       # ── DOMAIN MODELS (SQLAlchemy ORM) ──
│   │   ├── __init__.py
│   │   ├── user.py                   # User model
│   │   ├── organization.py           # Organization + membership model
│   │   ├── repository.py             # Repository + analysis status model
│   │   ├── api_key.py                # API key model (hashed secret)
│   │   ├── notification.py           # Notification model
│   │   ├── audit_log.py              # Immutable audit log model
│   │   └── billing.py                # Subscription + plan model (future)
│   │
│   ├── schemas/                      # ── REQUEST/RESPONSE SCHEMAS (Pydantic v2) ──
│   │   ├── __init__.py
│   │   ├── auth.py                   # LoginRequest, TokenResponse, RegisterRequest
│   │   ├── user.py                   # UserRead, UserUpdate, UserCreate
│   │   ├── organization.py           # OrgRead, OrgCreate, MembershipRead
│   │   ├── repository.py             # RepoRead, RepoCreate, AnalysisStatus
│   │   ├── api_key.py                # ApiKeyCreate, ApiKeyRead (never expose raw secret)
│   │   ├── notification.py           # NotificationRead, NotificationUpdate
│   │   ├── pagination.py             # Generic Page[T] schema for cursor pagination
│   │   └── common.py                 # MessageResponse, ErrorResponse, HealthResponse
│   │
│   ├── services/                     # ── APPLICATION SERVICES (Business Logic) ──
│   │   ├── __init__.py
│   │   ├── auth_service.py           # Login, register, token refresh, session revocation
│   │   ├── user_service.py           # User CRUD + profile management
│   │   ├── organization_service.py   # Org management, member invites, roles
│   │   ├── repository_service.py     # Repo registration, status tracking, metadata
│   │   ├── api_key_service.py        # Key generation (UUID4), hashing, rotation
│   │   ├── notification_service.py   # Fan-out notifications, read state, preferences
│   │   ├── webhook_service.py        # GitHub event routing and validation
│   │   └── billing_service.py        # Plan enforcement, quota checks (future)
│   │
│   ├── repositories/                 # ── DATA ACCESS LAYER (Repository Pattern) ──
│   │   ├── __init__.py
│   │   ├── base_repository.py        # Generic async CRUD (get, list, create, update, delete)
│   │   ├── user_repository.py        # User-specific queries (find by email, etc.)
│   │   ├── organization_repository.py
│   │   ├── repository_repository.py  # Repo queries (by owner, by status, paginated)
│   │   ├── api_key_repository.py     # Hash-based lookup
│   │   ├── notification_repository.py
│   │   └── audit_log_repository.py   # Append-only write methods
│   │
│   ├── workers/                      # ── BACKGROUND TASK WORKERS (Celery) ──
│   │   ├── __init__.py
│   │   ├── celery_app.py             # Celery factory, broker/backend from config
│   │   ├── tasks/
│   │   │   ├── __init__.py
│   │   │   ├── repo_tasks.py         # clone_repository, sync_repository tasks
│   │   │   ├── embed_tasks.py        # Future: parse_code, build_embeddings tasks
│   │   │   ├── notification_tasks.py # send_email, send_webhook_notification tasks
│   │   │   └── billing_tasks.py      # Future: usage metering tasks
│   │   └── schedules.py              # Celery Beat periodic task definitions
│   │
│   ├── ai/                           # ── AI PIPELINE LAYER (Future-Ready Stubs) ──
│   │   ├── __init__.py
│   │   ├── README.md                 # "Do not add logic here until AI milestone"
│   │   ├── agents/
│   │   │   ├── __init__.py
│   │   │   └── base_agent.py         # Abstract LangGraph agent interface
│   │   ├── pipelines/
│   │   │   ├── __init__.py
│   │   │   └── base_pipeline.py      # Abstract pipeline interface
│   │   ├── embeddings/
│   │   │   ├── __init__.py
│   │   │   └── base_embedder.py      # Abstract embedder (swap Gemini / OpenAI)
│   │   ├── parsers/
│   │   │   ├── __init__.py
│   │   │   └── base_parser.py        # Abstract tree-sitter parser interface
│   │   └── vector_store/
│   │       ├── __init__.py
│   │       └── base_vector_store.py  # Abstract Qdrant interface
│   │
│   ├── github/                       # ── GITHUB INTEGRATION LAYER (Future-Ready) ──
│   │   ├── __init__.py
│   │   ├── README.md                 # "Do not add logic here until GitHub App milestone"
│   │   ├── client.py                 # Abstract GitHub API client interface
│   │   ├── webhook_parser.py         # Validates HMAC signature, parses event types
│   │   └── app_auth.py               # JWT-based GitHub App authentication stubs
│   │
│   ├── utils/                        # ── SHARED UTILITIES ──
│   │   ├── __init__.py
│   │   ├── pagination.py             # Cursor and offset pagination helpers
│   │   ├── hashing.py                # bcrypt / SHA-256 wrappers
│   │   ├── datetime.py               # UTC-aware datetime helpers
│   │   ├── slugify.py                # URL-safe slug generation
│   │   └── retry.py                  # Exponential backoff decorator
│   │
│   └── main.py                       # FastAPI application factory (lifespan, routers)
│
├── tests/                            # ── TEST SUITE ──
│   ├── conftest.py                   # pytest fixtures, test DB setup
│   ├── factories/                    # Factory Boy model factories
│   │   ├── user_factory.py
│   │   └── repository_factory.py
│   ├── unit/
│   │   ├── services/
│   │   └── utils/
│   ├── integration/
│   │   ├── api/
│   │   └── repositories/
│   └── e2e/                          # Future: end-to-end workflow tests
│
├── scripts/                          # ── OPERATIONAL SCRIPTS ──
│   ├── seed_db.py                    # Dev data seeding
│   ├── create_superuser.py           # Bootstrap admin account
│   └── health_check.py              # External health probe script
│
├── .env.example                      # All required env vars with descriptions
├── pyproject.toml                    # Project metadata, deps, tool config (Ruff, mypy)
├── Dockerfile                        # Multi-stage production build
└── Dockerfile.dev                    # Development image with hot-reload
```

---

## 5. Frontend Folder Structure

```
frontend/
│
├── public/
│   ├── favicon.svg
│   └── robots.txt
│
├── src/
│   │
│   ├── app/                          # ── APPLICATION SHELL ──
│   │   ├── App.tsx                   # Root component, providers, router outlet
│   │   ├── Router.tsx                # All route definitions (React Router v6+)
│   │   └── providers.tsx             # QueryClient, ThemeProvider, AuthProvider
│   │
│   ├── features/                     # ── FEATURE MODULES (mirror backend features) ──
│   │   │
│   │   ├── auth/
│   │   │   ├── components/           # LoginForm, RegisterForm, OAuthButton
│   │   │   ├── hooks/                # useLogin, useRegister, useAuthState
│   │   │   ├── api/                  # authApi.ts (TanStack Query mutations)
│   │   │   ├── schemas/              # Zod validation schemas for forms
│   │   │   ├── types.ts              # AuthUser, TokenPair, Session
│   │   │   └── index.ts              # Public API (barrel export)
│   │   │
│   │   ├── dashboard/
│   │   │   ├── components/           # MetricsCard, ActivityFeed, QuickActions
│   │   │   ├── hooks/                # useDashboardMetrics
│   │   │   ├── api/                  # dashboardApi.ts
│   │   │   ├── types.ts
│   │   │   └── index.ts
│   │   │
│   │   ├── repositories/
│   │   │   ├── components/           # RepoCard, RepoList, ConnectRepoModal, AnalysisStatus
│   │   │   ├── hooks/                # useRepositories, useRepository, useConnectRepo
│   │   │   ├── api/                  # repositoriesApi.ts
│   │   │   ├── types.ts              # Repository, AnalysisState, RepoStatus
│   │   │   └── index.ts
│   │   │
│   │   ├── organizations/
│   │   │   ├── components/           # OrgCard, MemberList, InviteModal, RoleBadge
│   │   │   ├── hooks/                # useOrganization, useMembers, useInvite
│   │   │   ├── api/                  # organizationsApi.ts
│   │   │   ├── types.ts
│   │   │   └── index.ts
│   │   │
│   │   ├── api-keys/
│   │   │   ├── components/           # ApiKeyTable, CreateKeyModal, RevokeKeyButton
│   │   │   ├── hooks/                # useApiKeys, useCreateKey, useRevokeKey
│   │   │   ├── api/                  # apiKeysApi.ts
│   │   │   ├── types.ts
│   │   │   └── index.ts
│   │   │
│   │   ├── notifications/
│   │   │   ├── components/           # NotificationBell, NotificationPanel, NotificationItem
│   │   │   ├── hooks/                # useNotifications, useMarkRead
│   │   │   ├── api/                  # notificationsApi.ts
│   │   │   ├── types.ts
│   │   │   └── index.ts
│   │   │
│   │   └── billing/                  # Future: plan selection, usage, invoices
│   │       ├── components/
│   │       ├── hooks/
│   │       ├── api/
│   │       ├── types.ts
│   │       └── index.ts
│   │
│   ├── pages/                        # ── PAGE COMPOSITIONS (routes → feature assemblies) ──
│   │   ├── LoginPage.tsx
│   │   ├── RegisterPage.tsx
│   │   ├── DashboardPage.tsx
│   │   ├── RepositoriesPage.tsx
│   │   ├── RepositoryDetailPage.tsx
│   │   ├── OrganizationPage.tsx
│   │   ├── SettingsPage.tsx
│   │   ├── ApiKeysPage.tsx
│   │   ├── NotFoundPage.tsx
│   │   └── ErrorBoundaryPage.tsx
│   │
│   ├── components/                   # ── SHARED / DESIGN SYSTEM COMPONENTS ──
│   │   ├── ui/                       # shadcn/ui generated components (auto-managed)
│   │   │   ├── button.tsx
│   │   │   ├── input.tsx
│   │   │   ├── card.tsx
│   │   │   ├── dialog.tsx
│   │   │   ├── badge.tsx
│   │   │   └── ...
│   │   ├── layout/
│   │   │   ├── AppShell.tsx          # Main authenticated layout wrapper
│   │   │   ├── Sidebar.tsx           # Navigation sidebar
│   │   │   ├── TopBar.tsx            # Header with user menu, notifications
│   │   │   └── PageHeader.tsx        # Reusable page title + breadcrumb
│   │   ├── feedback/
│   │   │   ├── LoadingSpinner.tsx
│   │   │   ├── EmptyState.tsx
│   │   │   ├── ErrorFallback.tsx
│   │   │   └── StatusBadge.tsx
│   │   └── data/
│   │       ├── DataTable.tsx         # Generic sortable/filterable table
│   │       ├── Pagination.tsx
│   │       └── SearchInput.tsx
│   │
│   ├── hooks/                        # ── SHARED HOOKS ──
│   │   ├── useDebounce.ts
│   │   ├── useLocalStorage.ts
│   │   ├── useMediaQuery.ts
│   │   └── useWebSocket.ts           # Future: real-time updates
│   │
│   ├── lib/                          # ── INFRASTRUCTURE / INTEGRATIONS ──
│   │   ├── api-client.ts             # Axios instance (interceptors, base URL, auth headers)
│   │   ├── query-client.ts           # TanStack QueryClient configuration
│   │   ├── auth-store.ts             # Zustand auth state (tokens, user)
│   │   └── error-handler.ts          # Centralized API error parsing + toast display
│   │
│   ├── types/                        # ── GLOBAL TYPES ──
│   │   ├── api.ts                    # Generic ApiResponse<T>, ApiError, PaginatedResponse<T>
│   │   ├── env.d.ts                  # Vite env type declarations
│   │   └── global.d.ts               # Window augmentations
│   │
│   ├── utils/                        # ── FRONTEND UTILITIES ──
│   │   ├── formatters.ts             # Date, number, bytes formatters
│   │   ├── validators.ts             # Shared Zod schemas (email, url, etc.)
│   │   └── cn.ts                     # clsx + tailwind-merge utility
│   │
│   ├── constants/                    # ── FRONTEND CONSTANTS ──
│   │   ├── routes.ts                 # Typed route path constants
│   │   └── query-keys.ts             # TanStack Query key factories
│   │
│   └── styles/
│       └── globals.css               # Tailwind directives, CSS variables, base resets
│
├── index.html                        # Vite entry HTML
├── vite.config.ts                    # Vite config (aliases, proxy, plugins)
├── tsconfig.json                     # TypeScript strict configuration
├── tailwind.config.ts                # Tailwind + shadcn theme config
├── postcss.config.js
├── components.json                   # shadcn/ui CLI configuration
├── .env.example
└── package.json
```

---

## 6. Docker Structure

```
docker/
├── nginx/
│   ├── nginx.conf                    # Production reverse proxy config
│   └── default.conf                  # Virtual host: static files + API proxy
│
├── postgres/
│   └── init.sql                      # DB initialization (extensions: pgcrypto, uuid-ossp)
│
└── redis/
    └── redis.conf                    # Redis config (maxmemory, eviction policy)

# Root level
docker-compose.yml                    # Full stack for local development
docker-compose.prod.yml               # Production overrides (no volumes, no dev ports)
docker-compose.test.yml               # Isolated test environment (in-memory DB)
.env.example                          # Root env file template
```

### docker-compose.yml Service Map

```
services:
  postgres        → Port 5432   (PostgreSQL 16)
  redis           → Port 6379   (Redis 7)
  qdrant          → Port 6333   (Qdrant, future)
  backend         → Port 8000   (FastAPI + Uvicorn)
  worker          → (No port)   (Celery worker, same image as backend)
  beat            → (No port)   (Celery Beat scheduler, same image)
  flower          → Port 5555   (Celery monitoring UI, dev only)
  frontend        → Port 5173   (Vite dev server, dev only)
  nginx           → Port 80/443 (Reverse proxy, prod only)
```

---

## 7. Documentation Structure

```
docs/
│
├── architecture/
│   ├── overview.md                   # This document (high-level)
│   ├── backend.md                    # Backend layers, request lifecycle
│   ├── frontend.md                   # Frontend feature module contract
│   ├── database.md                   # Entity-relationship diagram, indexing strategy
│   ├── workers.md                    # Celery task definitions, retry policy
│   ├── ai-pipeline.md               # Future AI architecture (LangGraph flows)
│   └── github-app.md                 # GitHub App setup, webhook lifecycle
│
├── adr/                              # Architecture Decision Records
│   ├── 0001-use-clean-architecture.md
│   ├── 0002-async-sqlalchemy.md
│   ├── 0003-celery-over-arq.md
│   ├── 0004-qdrant-for-vectors.md
│   ├── 0005-api-versioning-strategy.md
│   └── 0006-feature-module-pattern.md
│
├── api/
│   ├── openapi.json                  # Auto-generated from FastAPI
│   └── postman_collection.json       # Dev-friendly Postman collection
│
├── guides/
│   ├── local-setup.md                # Step-by-step dev environment setup
│   ├── contributing.md               # Contribution guidelines + code standards
│   ├── env-variables.md              # All environment variables documented
│   ├── migrations.md                 # How to create and run Alembic migrations
│   ├── testing.md                    # Testing strategy and how to run tests
│   └── deployment.md                 # Production deployment checklist
│
└── README.md                         # Project root README (linked from GitHub)
```

---

## 8. Folder-by-Folder Rationale

### Backend

| Folder | Why It Exists |
|---|---|
| `app/api/` | **Presentation only.** Routers call services; they never touch the DB directly. |
| `app/api/v1/` | **API versioning from day one.** v2 can exist alongside v1 with zero breakage. |
| `app/core/` | **Cross-cutting concerns.** Config, security, logging live here so all layers can import them without circular dependencies. |
| `app/db/` | **Isolated DB wiring.** Session factory and engine setup are separated from models so you can swap databases later. |
| `app/models/` | **ORM-only.** SQLAlchemy table definitions. Never imported by the API layer directly. |
| `app/schemas/` | **Contract layer.** Pydantic schemas are the only thing the API layer exposes to the outside world. Models never leak out. |
| `app/services/` | **Business logic home.** All application rules live here. Services are injected into routes via FastAPI `Depends()`. |
| `app/repositories/` | **Data access encapsulation.** Services never write raw SQL. Repositories are the only code that touches SQLAlchemy sessions. |
| `app/workers/` | **Process isolation.** Background jobs run in separate Celery worker processes. They import services but are never imported by the API. |
| `app/ai/` | **Future-proofing.** Abstract interfaces defined now. When AI features land, implementations drop in here without touching any other layer. |
| `app/github/` | **GitHub as a plugin.** GitHub integration is a separate concern, not baked into business logic. Swap to GitLab later by replacing this module. |
| `app/utils/` | **Pure functions only.** No I/O, no external dependencies. Importable from any layer. |
| `alembic/` | **Migration as code.** All schema changes are versioned, reviewable, and reversible. |
| `tests/` | **Mirror of app structure.** Tests live adjacent to the code they cover but in a separate tree. Factories prevent test coupling to DB state. |

### Frontend

| Folder | Why It Exists |
|---|---|
| `src/features/` | **Feature cohesion.** Everything for a feature (components, hooks, API calls, types) lives together. Prevents cross-feature imports and spaghetti. |
| `src/pages/` | **Thin route compositions.** Pages assemble features; they contain no business logic themselves. |
| `src/components/ui/` | **shadcn/ui is auto-managed.** Never manually edit files here; use the CLI. Keeps design system upgradable. |
| `src/components/layout/` | **Structure vs. content separation.** Layout components are reused across every authenticated page. |
| `src/lib/` | **Infrastructure wiring.** API client, query client, auth store. These are singletons configured once and injected everywhere. |
| `src/types/` | **Global type contracts.** Shared types that span features. Feature-specific types stay inside their feature. |
| `src/constants/` | **No magic strings.** Route paths and query keys are typed constants. Typos become compile errors. |

---

## 9. Every Architectural Decision Explained

### 9.1 Clean Architecture with Feature Modules

**Decision:** Use Clean Architecture layers (Domain → Application → Infrastructure) combined with Feature Module organization.

**Why:** Pure layer organization (`models/`, `views/`, `controllers/`) causes horizontal coupling — every new feature touches every layer directory. Feature modules contain the blast radius of changes. A new feature = a new folder, not scatter across 6 directories.

**Trade-off:** More files per feature. Mitigated by barrel exports (`index.ts` / `__init__.py`).

---

### 9.2 Repository Pattern over Direct ORM Usage

**Decision:** Services call repositories; repositories call SQLAlchemy.

**Why:** If you call SQLAlchemy directly from services, you cannot swap databases, cannot mock data access in unit tests, and cannot enforce query boundaries. The repository pattern makes all data access explicit and testable.

**Trade-off:** More boilerplate. Justified at scale — the `base_repository.py` provides generic CRUD so individual repositories only override what's custom.

---

### 9.3 Async SQLAlchemy (AsyncSession)

**Decision:** Use SQLAlchemy 2.0 async sessions throughout.

**Why:** FastAPI is async. Using sync SQLAlchemy in an async framework blocks the event loop under load, eliminating the entire performance benefit of async I/O. Async sessions are slightly more complex to configure but mandatory for production FastAPI.

---

### 9.4 Pydantic v2 Schemas as the API Contract

**Decision:** Never expose ORM models to the API layer. Always use Pydantic schemas.

**Why:** ORM models carry session state, lazy-load triggers, and internal columns (e.g., `hashed_password`). Exposing them causes accidental data leaks and couples your API shape to your DB schema. Pydantic schemas are an explicit, validated, documented contract.

---

### 9.5 API Versioning from Day One

**Decision:** All routes live under `/api/v1/`.

**Why:** Without versioning, any breaking API change breaks all clients. With `v1` namespacing, you can run `v1` and `v2` simultaneously while migrating clients. The cost is one extra directory level. The benefit is never having an emergency "we broke everyone" incident.

---

### 9.6 Celery for Background Workers

**Decision:** Use Celery with Redis broker over ARQ or asyncio tasks.

**Why:** FastAPI background tasks (`BackgroundTasks`) are in-process — if the server restarts, tasks are lost. ARQ is simpler but less battle-tested. Celery has built-in retry logic, dead-letter queues, task monitoring (Flower), scheduled tasks (Beat), and mature operational tooling. For AI pipelines that may run for minutes, Celery is mandatory.

---

### 9.7 AI and GitHub as Isolated Modules

**Decision:** `app/ai/` and `app/github/` exist with only abstract interfaces. Zero implementations yet.

**Why:** Without the stubs, future developers will implement AI code directly in services, creating untestable, unmockable coupling. Abstract interfaces defined now enforce the contract before implementation. This is the Open/Closed Principle applied to entire subsystems.

---

### 9.8 No Hardcoded Values — Pydantic Settings

**Decision:** All configuration via `app/core/config.py` using `pydantic-settings`.

**Why:** Hardcoded values are a security risk (secrets in code) and an operational nightmare (redeploy to change a URL). Pydantic Settings reads from environment variables with type validation, defaults, and clear documentation. Every variable is declared in `.env.example`.

---

### 9.9 Feature Modules on the Frontend

**Decision:** Frontend mirrors backend feature organization.

**Why:** When a backend engineer adds a new feature, the frontend engineer knows exactly where to create the corresponding code. `features/repositories/` on the frontend maps to `api/v1/repositories/` on the backend. This reduces coordination overhead and onboarding time.

---

### 9.10 TanStack Query for All Server State

**Decision:** All API data goes through TanStack Query. No raw `useEffect` + `fetch`.

**Why:** TanStack Query handles caching, background refetching, loading states, error states, optimistic updates, and cache invalidation. Implementing this manually with `useEffect` leads to inconsistent loading states and cache bugs across the codebase.

---

### 9.11 Alembic for All Schema Changes

**Decision:** Never use `Base.metadata.create_all()` in production. Always use Alembic migrations.

**Why:** `create_all()` cannot handle modifications to existing tables. Alembic generates reversible, reviewable migration scripts that are committed to git. Every schema change is auditable, rollback-able, and deployable without downtime.

---

### 9.12 ADR Documentation

**Decision:** Every significant architectural decision gets an Architecture Decision Record (ADR) in `docs/adr/`.

**Why:** In 12 months, no one will remember why a decision was made. ADRs record the context, the options considered, the decision, and the consequences. This prevents re-litigating settled decisions and helps new contributors understand "why does it work this way?"

---

## 10. Future Extension Points

### Adding a New Backend Feature (e.g., "pull request reviews")

1. Create `app/models/pull_request.py` — ORM model
2. Create `app/schemas/pull_request.py` — Pydantic schemas
3. Create `app/repositories/pull_request_repository.py` — data access
4. Create `app/services/pull_request_service.py` — business logic
5. Create `app/api/v1/pull_requests/router.py` — HTTP endpoints
6. Register router in `app/api/router.py`
7. Create Alembic migration
8. **Zero changes to any existing file.**

---

### Adding a New Frontend Feature

1. Create `src/features/pull-requests/`
2. Add `types.ts`, `api/`, `hooks/`, `components/`
3. Create `src/pages/PullRequestsPage.tsx`
4. Add route to `src/app/Router.tsx`
5. **Zero changes to any existing feature.**

---

### Plugging in LangGraph Agents

1. Implement `app/ai/agents/pr_review_agent.py` extending `base_agent.py`
2. Implement `app/ai/pipelines/pr_review_pipeline.py`
3. Call from `app/workers/tasks/embed_tasks.py`
4. **No changes to API layer, services, or models.**

---

### Adding a New LLM Provider

1. Create `app/ai/embeddings/openai_embedder.py` implementing `base_embedder.py`
2. Config flag `AI_EMBEDDING_PROVIDER=openai` in `config.py`
3. Factory function in `app/ai/embeddings/__init__.py` returns correct implementation
4. **No downstream code changes.**

---

### Enabling GitHub App Webhooks

1. Implement `app/github/client.py` against the defined interface
2. Implement `app/github/app_auth.py`
3. Populate `app/api/v1/webhooks/router.py` (already wired)
4. Add Celery tasks in `app/workers/tasks/` for event processing
5. **Webhook endpoint already exists; no routing changes needed.**

---

### Adding Multi-Tenancy / Organizations Billing

1. `app/models/billing.py` already scaffolded
2. `app/services/billing_service.py` already stubbed
3. Add Stripe SDK, implement methods
4. Add `app/workers/tasks/billing_tasks.py` for metering
5. **No architectural refactoring needed.**

---

## 11. Data Flow Diagrams

### Request Lifecycle (Authenticated API Call)

```
HTTP Request
    │
    ▼
FastAPI Router (app/api/v1/repositories/router.py)
    │
    ├── Middleware: RequestID injection, Timing, CORS
    │
    ├── Dependency: get_current_user() → JWT verify → DB lookup → User object
    │
    ├── Dependency: get_db() → AsyncSession injected
    │
    ▼
Route Handler calls Service
    │
    ▼
Service (app/services/repository_service.py)
    │   ├── Business rule validation
    │   ├── Authorization check
    │
    ▼
Repository (app/repositories/repository_repository.py)
    │   ├── SQLAlchemy query
    │   └── Returns ORM model
    │
    ▼
Service maps ORM model → Pydantic schema
    │
    ▼
Route Handler returns Pydantic schema
    │
    ▼
FastAPI serializes → JSON Response
```

### Background Task Lifecycle

```
API Route: POST /repositories/{id}/analyze
    │
    ▼
Service validates repository exists + user authorized
    │
    ▼
Service updates repository.status = "QUEUED"
    │
    ▼
Service calls: celery_app.send_task("workers.tasks.repo_tasks.clone_repository", args=[repo_id])
    │
    ▼
Returns 202 Accepted immediately (non-blocking)
    │
    ▼ (async, separate process)
Celery Worker picks up task
    │
    ▼
Task opens its own DB session (not shared with API)
    │
    ▼
Task updates repository.status = "CLONING" → "EMBEDDING" → "COMPLETE"
    │
    ▼
Task sends notification via notification_service
    │
    ▼
Celery Beat can schedule periodic re-sync tasks
```

### GitHub Webhook Lifecycle (Future)

```
GitHub App → POST /api/v1/webhooks/github
    │
    ▼
webhook_parser.py: Verify HMAC-SHA256 signature
    │
    ▼
Parse event type (push, PR opened, PR review requested)
    │
    ▼
webhook_service.py: Route to appropriate Celery task
    │
    ▼
Celery Worker: Process event (e.g., trigger re-analysis on push)
    │
    ▼
AI Pipeline: LangGraph agent runs analysis
    │
    ▼
Result: GitHub PR comment posted via GitHub API
```

---

> **This document is the source of truth for RepoSage architecture.**
> All implementation decisions must trace back to a principle or ADR documented here.
> When in doubt: add a new module, never mutate an existing one.
