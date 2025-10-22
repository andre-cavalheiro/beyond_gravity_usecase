# Fury API

## Overview

Fury API is built with **Domain-Driven Design (DDD)** and **Unit of Work (UoW)** patterns, tightly integrating with its data model to centrally manage schemas, migrations, and transactional integrity. It's cloud-native and ready for **containerized deployments** with Docker, Helm, and Kubernetes configurations. Operations are streamlined via `make` commands to minimize manual intervention.

**Tech Stack:** FastAPI, PostgreSQL, SQLAlchemy, Firebase Auth, Docker, Kubernetes

---

## Getting Started (Local Development)

### Prerequisites
- Python 3.11+, Docker, Make

### Run Locally (5 minutes)
1. `make install` (install poetry and project dependencies)
2. Create `.env` (copy from `.env.example`) see how to configure firebase [here](../README.md#firebase-configuration).
3. `docker-compose up postgres -d` (launch database in the background) 
4. `make db-migrate` (run database migrations)
4. `make start`
5. Visit http://localhost:3000/docs

Alternatively, you can just use docker-compose - you'll still need to perform step 2 (create `.env`) for it to work.

```bash
docker-compose up fury-api -d
```

### Authentication

The API requires Firebase authentication for all endpoints. For local development, you have two options:

#### Option 1: Skip Authentication (Recommended for Local Dev)

Bypass token validation entirely by setting a mock user identity in `.env`:

```bash
FURY_API_DEVEX_ENABLED=true
FURY_API_DEVEX_AUTH_OVERRIDE_ENABLED=true
FURY_API_DEVEX_AUTH_OVERRIDE_USER_NAME=Test User
FURY_API_DEVEX_AUTH_OVERRIDE_USER_EMAIL=test@example.com
FURY_API_DEVEX_AUTH_OVERRIDE_ORGANIZATION_ID=org_123
FURY_API_DEVEX_AUTH_OVERRIDE_USER_ID=user_123
FURY_API_DEVEX_AUTH_OVERRIDE_FIREBASE_USER_ID=firebase_123
```

All requests will be authenticated as this mock user. Use this for rapid development.

#### Option 2: Generate Real Firebase Tokens
Test actual authentication flows using a Firebase user:

```bash
# In .env
FURY_API_DEVEX_ENABLED=true
FURY_API_DEVEX_TOKEN_GENERATION_FIREBASE_USER_ID=your_firebase_user_id

# Generate token (valid for 1 hour)
make get-token
```

Use this to better mimick real production scenarios.

## Architecture

### Domains

The API follows **Domain-Driven Design (DDD)** with a layered architecture. Each domain (`src/fury_api/domain/`) represents a business concept (users, organizations, earthquakes) and is self-contained with minimal cross-domain dependencies. 

```
HTTP Request → Controller → Service → Repository → Database
                    ↓           ↓          ↓
                 Routes    Business    Data Access
                           Logic
```

**`controller.py`** - HTTP endpoint handlers
- Maps HTTP requests to service method calls
- Handles request validation via Pydantic models
- Manages dependency injection (auth, services, UoW)
- Returns HTTP responses

**Example:**
```python
@router.get("/users/{id}", response_model=UserRead)
async def get_user(
    id: int,
    users_service: Annotated[UsersService, Depends(get_service(ServiceType.USERS))],
) -> User:
    return await users_service.get_user_by_id(id)
```

**`model.py`** - Data schemas
- Defines database table structure (via SQLModel/SQLAlchemy)
- Provides Pydantic validation for API input/output
- Auto-generates OpenAPI documentation
- Includes variants: `UserCreate` (input), `UserRead` (output), `User` (database model)

**`service.py`** - Business logic layer
- Orchestrates domain operations (create user, update organization, query earthquakes)
- Extends from `SqlService[T]` for database-backed services, which combined with our sqlalquemy pydantic models enabels standard CRUD operations out-of-the-box
- Enforces business rules and validation

**Example:**
```python
class UsersService(SqlService[User]):
    @with_uow
    async def get_user_by_id(self, id: int) -> User | None:
        return await self.repository.get_by_id(self.session, id)
```

**`repository.py`** - Data access layer
- Extends `GenericSqlExtendedRepository[T]`, which provides type-safe CRUD, pagination, filtering, and sorting out-of-the-box, allowing repositories to focus only on domain-specific queries.

**Example:**
```python
class UserRepository(GenericSqlExtendedRepository[User]):
    async def get_by_email(self, session: AsyncSession, email: str) -> User | None:
        q = select(User).where(User.email == email)
        return (await session.exec(q)).scalar_one_or_none()
```

Repositories are accessed via **Unit of Work** (`lib/unit_of_work.py`), which manages database transactions (commit/rollback) thus prroviding session lifecycle management. They also enforce multi-tenancy via PostgreSQL Row-Level Security.

**Example Flow:**
```python
# In controller - UoW injected automatically
users_service: Annotated[UsersService, Depends(get_service(...))]

# In service - @with_uow manages transaction
@with_uow
async def create_user(self, user_data: UserCreate) -> User:
    user = User(**user_data.dict())
    return await self.repository.add(self.session, user)
    # Transaction commits automatically on successful exit
```

### Authentication & Security

**Authentication Flow:**
```
Request → Extract Bearer token → Validate (Firebase/System/Override) →
Extract user claims → Database lookup → Verify organization →
Inject auth_user into services
```

**Multi-Tenancy**: The authentication system extracts `organization_id` from the authenticated user and passes it to the Unit of Work, which enforces Row-Level Security (RLS) at the PostgreSQL level. This ensures data isolation between organizations without application-level filtering.

**Usage in Controllers:**
```python
@router.get("/users")
async def get_users(
    current_user: Annotated[User, Depends(get_current_user)]  # Auth required
) -> list[User]:
    # current_user is fully validated and includes organization_id
    ...
```

### Pagination & Filtering

**Pagination** (`lib/pagination.py`) uses cursor-based pagination (via fastapi-pagination) for stateless, scalable list endpoints.

**Model Filters** (`lib/ model_filters/`) provides type-safe, declarative query filtering made available to all domains.
- **Definition-based**: Each model defines allowed filter fields and operations in its controller (fields and operations are white-listed)
- **18+ operations**: `eq`, `neq`, `gt`, `gte`, `lt`, `lte`, `in`, `nin`, `like`, `ilike`, `is_null`, `is_not_null` (their applicability varies according to the target field's data type)
- **SQL injection prevention**: All values are parameterized and automaticly casted with validation (strings, numbers, booleans, dates, arrays)

**HTTP Query Format:**
```
GET /api/earthquakes?filters=magnitude:gte:5.0&filters=location:like:California&sorts=magnitude:desc
```

**Usage in Controllers:**
```python
@router.get("/earthquakes")
async def list_earthquakes(
    filters_parser: Annotated[
        FiltersAndSortsParser,
        Depends(get_models_filters_parser_factory(EARTHQUAKES_FILTERS_DEFINITION))
    ],
) -> CursorPage[Earthquake]:
    return await service.get_items_paginated(
        model_filters=filters_parser.filters,
        model_sorts=filters_parser.sorts
    )
```

The system transforms HTTP query parameters into type-safe SQLAlchemy filters, validated against a declarative schema.

### Dependencies, Factories

**Components:** `dependencies/`, `factories/`

This architecture implements Dependency Injection and Factory patterns:

**Factories** create instances dynamically:
- `ServiceFactory`: Uses reflection to instantiate services by type (e.g., `ServiceType.USERS` → `UsersService`)
- `UnitOfWorkFactory`: Creates UoW (unit of work) instances with appropriate session factories (read-only vs read-write)
- `ClientsFactory`: Creates external client instances (USGS API, etc.)

**Dependencies** compose FastAPI injectable functions:
- `get_uow_tenant()`: Creates UoW (unit of work) scoped to current user's organization (write access)
- `get_uow_tenant_ro()`: Read-only variant
- `get_uow_any_tenant()`: No tenant isolation (for public data like earthquakes)
- `get_service()`: Creates services with UoW + auth context injected

Personal note on dependencies: leveraging dependency injection, whether it's for 3rd party clients, domain services, datbase clients helps maintain clean architecture and proper separation of concerns in FastAPI projects. That's why this project has so many of it.

**Request Flow Example:**
```
Controller endpoint → Depends(get_service(ServiceType.USERS, read_only=True))
  → get_uow_tenant_ro() → Creates UoW with organization_id
  → get_current_user() → Validates auth, extracts org_id
  → ServiceFactory.create_service() → Instantiates UsersService(uow, auth_user)
  → Service method → Repository CRUD → PostgreSQL (RLS enforced)
```

## Database & Migrations

Fury API has a tightly integrated data model using **SQLAlchemy**, which serves as both the **Object Relational Mapper (ORM)** and schema definition tool. This ensures that business logic and database interactions remain structured and scalable.

Database schema changes are managed using **Alembic**, which generates versioned migration scripts to evolve the database structure over time. Alembic tracks schema changes and allows for both **forward** and **rollback** operations, ensuring safe database modifications.

When modifying the data model (e.g., adding new tables or fields), generate a new migration script:
```bash
make m='describe your migration' db-create-migration
```
This will create a new migration file inside `src/fury_api/lib/db/migrations/versions/`, where you can customize the database changes if necessary.

Apply all pending migrations to bring the database schema up to date:
```bash
make db-migrate
```
This command ensures the schema reflects the latest changes defined in the migration scripts.

If a migration introduces an issue, you can revert the last migration:
```bash
make rollback
```
This will undo the most recent migration, restoring the previous state of the schema. Rollbacks are critical for avoiding disruptions when deploying database changes to production environments so when developing a new migration make sure the rollback logic is also sound.

#### Understanding Alembic Under the Hood

Alembic operates through its **configuration file** (`alembic.ini`) and an **environment script** (`env.py`). When you run a `make db-...` command, it effectively invokes Alembic under the hood, applying migrations using the configured **FURY_DB_URL** as the database connection.

## Development Guides

### Adding a new Domain

Besides building the domain, you'll need to add references to it in `src/fury_api/domain/routes.py (router)`, `src/fury_api/core/unit_of_work:52 (_repos mapper)`, and (possibly if other domain need to use the new domains service) `src/fury_api/core/factories/service_factory:15 (ServiceType Enum)`

### Configuration Management

Configuration settings are managed in `src/fury_api/lib/settings.py`. The `.env` file provides runtime settings for local development, while Kubernetes secrets store sensitive information in production.

## Deployment 

You can deploy to a Kubernetes cluster using:
```bash
make deploy
```

Make sure to adjust the following variables in your Makefile
```yaml
DOCKER_IMAGE
DOCKERFILE_PATH
KUBERNETES_CLUSTER
KUBERNETES_NAMESPACE
PROD_SECRETS_FILE
HELM_CHART_NAME
HELM_CHART_PATH
```

Under the hood this is the sequence of steps that happen:

1. **Ensure Kubernetes Context**

   To prevent deploying to the wrong cluster, validate your current context against the cluster name and namespace defined in the Makefile:

   ```bash
   make validate-context
   ```

   If needed, switch to the correct Kubernetes context:

   ```bash
   make set-context
   ```

2. **Build and Push Docker Image**

   ```bash
   make docker-build-push
   ```

   This builds a multi-architecture Docker image (`linux/amd64`, `linux/arm64`) and pushes it to the configured container registry. Ensure you are authenticated (`docker login`) before executing this step.

3. **Push Kubernetes Secrets**

   ```bash
   make push-secrets
   ```
   This command created a single kubernetes secret out of the content of `.env.prod`, which is later referenced under the by the helm deployment to inject these variables into the application pods as environment variables.

4. **Deploy Helm Chart**

   ```bash
   make push-helm
   ```

   This deploys or updates the API using Helm, ensuring that all Kubernetes resources are properly configured and managed.

5. **Run Database Migrations in Production**
   ```bash
   make db-migrate-prod
   ```

   What's happening under the hood is forwarding local traffic to the PostgreSQL instance:

   ```bash
   kubectl port-forward svc/fury-api-postgresql 5432:5432
   ```

   And updateing the database schema:

   ```bash
   make db-migrate
   ```

6. **Test the Deployment**

   Since the API is deployed as a **ClusterIP** service by default, it cannot be accessed externally without an ingress. However, you can manually forward a port to test connectivity:

   ```bash
   kubectl port-forward svc/fury-api 3000:3000
   ```

   Then check if the API is responding correctly:

   ```bash
   curl http://localhost:3000/api/v1/health
   ```

