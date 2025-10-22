# Fury API

## Overview

Fury API is built with **Domain-Driven Design (DDD)** and **Unit of Work (UoW)** patterns, tightly integrating with its data model to centrally manage schemas, migrations, and transactional integrity. It's cloud-native and ready for **containerized deployments** with Docker, Helm, and Kubernetes configurations. Operations are streamlined via `make` commands to minimize manual intervention.

**Tech Stack:** FastAPI, PostgreSQL, SQLAlchemy, Firebase Auth, Docker, Kubernetes

---

## Quick Start

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

### Tech Stack & Design Patterns
???

### Project Structure

Fury API follows a structured design based on **Domain-Driven Design (DDD)** consisting of multiple **domains** (under `src/fury_api/domain`) this is where the core business logic of the API exists. Each domain consists of:

- **`controller`**: Responsible for handling incoming HTTP requests and their respective routing.
  - Each function in the controller typically corresponds to an available HTTP endpoint exposed by the API (if marked by a FastAPI `APIRouter` decorator).

- **`service`**: Act as the core of the business logic for the domain.
  - Handles the main functionalities and operations related to the domain (e.g., service classes for blueprints, entities, scorecards, users, etc.).
  - Controllers use services to execute operations. In most cases, a controller only interacts with the service of its own domain, but complex endpoints may utilize multiple services.

- **`model`**: Represents the data structures of the domain (often mapped to database tables).
  - Models define the schema for the domain's data and can include validation and serialization logic.
  - They also specify the schema of objects expected and returned by the API. This enables the automatic generation of API documentation and the API client

- **`repository`**: Extends the models of the domain with specific database operations using SQLAlchemy.
  - Handles all database interactions, serving as an abstraction layer for the database.
  - Services utilize repositories to interact with the database. While most services only need access to their domain's repository, complex service operations may involve multiple repositories.
  - Repositories are accessed through a **Units of Work (UoW)** (`src/fury_api/core/unit_of_work.py`), which ensures that data operations occur within a single transaction and that each endpoint can only interact with the database in the intended way (read only, tenant control, etc.).


### Core Components

### Middleware & Request Pipeline

The API uses two essential middlewares configured in `src/fury_api/asgi.py`:

**CORS Middleware** (`lib/cors.py`):
- Enables cross-origin requests from web browsers
- Currently configured to allow all origins (`["*"]`) for development flexibility
- Essential if you have a web frontend consuming this API
- In production, restrict `CORS_ORIGINS` to specific trusted domains

**GZip Compression** (`lib/compression.py`):
- Automatically compresses responses larger than 500 bytes
- Uses maximum compression level (9) for optimal bandwidth savings
- Particularly effective for large JSON responses (typical 70-80% size reduction)
- Can be removed if you handle compression at the reverse proxy level (e.g., nginx, CloudFlare)

Both middlewares are applied globally to all endpoints. Custom per-endpoint middleware is intentionally avoided to keep the request pipeline simple and predictable.

---

The `src/fury_api/lib/` directory contains shared infrastructure and utilities used across domains:

- **`settings.py`**: Centralized configuration management using Pydantic. All environment variables and application settings are defined here with type safety and validation.

- **`db/`**: Database infrastructure including SQLAlchemy base models, session management, and Alembic migrations. The `base.py` module provides a `BaseDBModel` that all domain models inherit from, offering automatic JSON serialization with camelCase conversion and PATCH update functionality.

- **`exceptions.py`**: Custom exception hierarchy for consistent error handling across the API. All exceptions map to appropriate HTTP status codes and response formats.

- **`responses.py`**: Custom response classes using `msgspec` for fast JSON serialization (significantly faster than standard JSON libraries).

- **`jwt.py` / `firebase.py`**: Authentication infrastructure for token validation and Firebase integration.

- **`cors.py` / `compression.py`**: Middleware configurations for cross-origin requests and response compression.

- **`logging.py`**: Structured logging setup with request context tracking.

- **`utils/`**: Minimal utility functions that are actively used:
  - `dicts.py`: Dictionary manipulation (`dict_renamer` for token translation, `merge_dicts` for PATCH operations)
  - `string.py`: Case conversion helpers (`snake_case_to_camel`, `snake_case_to_pascal`) used for API response formatting and dynamic class loading

The library has been intentionally kept lean—only components that serve a clear, active purpose remain.


### Database & Migrations

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

