# Fury API

## Introduction

Fury API is a general-purpose API built with robust software architecture principles. It tightly integrates with the underlying data model, ensuring that data schemas and migrations are centrally managed and applied through the API itself. This design follows **Domain-Driven Design (DDD)** principles, which focus on structuring the API around real-world business concepts. Additionally, it employs the **Unit of Work (UoW)** pattern, ensuring that all database operations occur within a single transactional context, minimizing inconsistencies and maintaining integrity.

The API is built for cloud-native environments and is fully prepared for **containerized deployments**. It includes configurations for **Docker image building**, **Helm chart packaging**, and **Kubernetes deployment**. Development operations, database management, and deployments are streamlined using `make` commands to minimize manual intervention and reduce errors.

---

## Getting Started (Local Development)

### Environment Setup

Before running the API locally, ensure all dependencies are installed:

```bash
make install
```

This will:
- Install the necessary dependencies via Poetry.
- Set up a dedicated Python virtual environment.
- Install pre-commit hooks to enforce code quality.

Next, prepare your environment by creating a `.env` file based on the `.env.example` template.

### Launching the Database

Start the PostgreSQL database instance using Docker:

```bash
docker-compose up postgres -d
```

If this is the first time running the database, it will be empty. You need to apply initial database schema and policies:

```bash
make db-migrate
```

This command runs Alembic migrations, ensuring that the database structure aligns with the latest schema definitions in the codebase.

### Launching the API

You can start the API in one of two ways:

#### Using Docker

```bash
docker-compose up fury-api -d
```

#### Running the API Natively

If you prefer to run the API directly from your machine, activate the virtual environment and execute it manually:

```bash
source .venv/bin/activate
cd src
python -m fury_api
```

### Testing the Setup

Ensure the API is up and running:

```bash
curl http://localhost:3000/api/v1/health
```

Verify the API can successfully connect to the database:

```bash
curl http://localhost:3000/api/v1/health/velini
```

If these checks fail, verify that your `.env` file is properly set up and the database is running.

---

## Deploying to a Kubernetes Cluster

### Deployment Workflow

A full deployment can be executed with:

```bash
make deploy
```

Alternatively, you can perform individual deployment steps manually:

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



---

## Development

### Project Structure

Fury API follows a structured design based on **Domain-Driven Design (DDD)** consisting of multiple **domains** (under `src/fury_api/domain`) each encapsulating a specific business function. Each domain consists of:

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

### Configuration Management

Configuration settings are managed in `src/fury_api/lib/settings.py`. The `.env` file provides runtime settings for local development, while Kubernetes secrets store sensitive information in production.

### Adding a new Domain

Besides building the domain, you'll need to add references to it in `src/fury_api/domain/routes.py (router)`, `src/fury_api/core/unit_of_work:52 (_repos mapper)`, and (possibly if other domain need to use the new domains service) `src/fury_api/core/factories/service_factory:15 (ServiceType Enum)`


### Data Model and Database

Fury API has a tightly integrated data model using **SQLAlchemy**, which serves as both the **Object Relational Mapper (ORM)** and schema definition tool. This ensures that business logic and database interactions remain structured and scalable.

#### Schema Management and Migrations

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

## Testing

Run all tests:
```bash
make test
```

Database migrations can be tested with a temporary database (this does not guarantee the outcome is exactly as intended, just that the migration script works):
```bash
make test
```

### Making Requests

To interact with the API, you'll need a valid authentication toke from a valid user. You can obtain one by running:
```bash
make get-token
```

This token will be valid for 1 hour, which is the maximum duration allowed by Firebase.

Before using this command, ensure that the following environment variables are configured:
```bash
FURY_API_DEVEX_ENABLED=true
FURY_API_DEVEX_TOKEN_GENERATION_FIREBASE_USER_ID=your_firebase_user_id
```
Replace `your_firebase_user_id` with the appropriate Firebase User ID.

Alternatively, you can skip token validation for purely development purposes with the following configuration:
```bash
FURY_API_DEVEX_ENABLED=true
FURY_API_DEVEX_AUTH_OVERRIDE_ENABLED=true
FURY_API_DEVEX_AUTH_OVERRIDE_USER_NAME=...
FURY_API_DEVEX_AUTH_OVERRIDE_USER_EMAIL=...
FURY_API_DEVEX_AUTH_OVERRIDE_ORGANIZATION_ID=...
FURY_API_DEVEX_AUTH_OVERRIDE_USER_ID=...
FURY_API_DEVEX_AUTH_OVERRIDE_FIREBASE_USER_ID=...
```

---

## Debugging And Problem Solving

- Restart API to apply changes:
  ```bash
  kubectl rollout restart deployment fury-api
  ```
- Connect to the database directly:
  ```bash
  kubectl exec -it fury-api-postgresql-0 -- psql -U postgres
  ```
