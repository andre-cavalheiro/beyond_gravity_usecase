# Beyond Gravity – Earthquake Monitoring System

An earthquake monitoring and visualization system built with modern architecture principles. The application:

- **Ingests real-time earthquake data** from the USGS Earthquake Hazards Program API
- **Provides a reactive web interface** to explore, filter, and visualize earthquake events with 3D geospatial visualization
- **Exposes a comprehensive REST API** with advanced filtering, pagination, and image processing capabilities
- **Includes a CLI tool** with full parity to API operations for programmatic access and automation
- **Cloud-native ready** with Docker configuration, Kubernetes Helm charts, and production deployment support
- **Developer-friendly** with make commands for simplified local development and common operations

**Live Demo**: [beyond-gravity.cavalheiro.io](http://beyond-gravity.cavalheiro.io/)

Built with **FastAPI** (backend), **Next.js** (frontend), **PostgreSQL** (database), and **Domain-Driven Design** architecture principles for scalability and maintainability.

---

# Setup

# Run with Docker

## Prerequisites

- Docker: 24.0.6
- Docker Compose (v2): 2.23.0

## Quick start

From the repository root:

```bash
docker compose up
```

- Webapp: http://localhost:3001
- API: http://localhost:3000
- Postgres: localhost:5432 (user: `postgres`, password: `postgres`, db: `beyond-gravity-local`)

To stop:

```bash
docker compose down
```

To stop and remove the database volume:

```bash
docker compose down -v
```

## Forcing a clean rebuild

Docker aggressively caches images and keeps named volumes between runs, so after the first `docker compose up` subsequent starts are almost instant. If you need to re-test everything from scratch (for example, after changing dependencies or wanting to wipe the database), follow this sequence from the repository root:

```bash
# 1. Stop containers and drop the Postgres volume
docker compose down -v

# 2. Rebuild images without using cache
docker compose build --no-cache

# 3. Start fresh containers, recreating everything
docker compose up --force-recreate
```

This rebuilds the API and webapp images, applies migrations, and creates a brand-new Postgres data volume so you can validate the full bootstrap flow end to end.

# Backend

For detailed information about the API, including architecture, deployment, testing, and development guidelines, see [api/README.md](./api/README.md).

# Frontend

For detailed information about the web application, see [webapp/README.md](./webapp/README.md).


# CLI

## Setup

Before using the CLI, make sure the script is executable:

```bash
chmod +x cli.sh
```

## Usage

```bash
./cli.sh <command> [options]
```

The script changes into `api/`, sets `PYTHONPATH=src`, and delegates to `python -m fury_api.scripts.cli`. Any flags you pass are forwarded untouched.

### Common examples

- List the latest earthquakes:

  ```bash
  ./cli.sh list-earthquakes
  ```

- Paginate by internal ID:

  ```bash
  ./cli.sh list-earthquakes --after-id 777
  ```

- Pull full details for a specific record:

  ```bash
  ./cli.sh get-earthquake 797
  ```

- Ingest new data from USGS:

  ```bash
  ./cli.sh ingest-earthquakes 2024-01-01 2024-01-02 --min-magnitude 4.0
  ```

- Transform a CIIM Geo image (local file or URL):

  ```bash
  ./cli.sh transform-image https://example.com/image.jpg -o output.png
  ```

## Notes
- For each command you can learn more about it using the help flag (`-h`) e.g:
  - `./cli.sh -h`
  - `./cli.sh list-earthquakes -h`
  - etc
- Environment variables from `api/.env` are still respected because the script runs inside the API project root.


# Firebase Configuration

This application uses **Firebase Authentication** for user management. Before running the application locally or deploying it, you need to set up a Firebase project and configure the required environment variables.

## Step 1: Create a Firebase Project

If you don't already have a Firebase project:

1. Go to the [Firebase Console](https://console.firebase.google.com/)
2. Click **Add project** (or select an existing one)
3. Follow the setup wizard to create your project

## Step 2: Obtain Service Account Credentials (Required for API)

The backend API requires Firebase Admin SDK credentials to verify authentication tokens:

1. **Navigate to Project Settings:**
   - Click on the **⚙️ Gear Icon** in the left menu
   - Select **Project settings**

2. **Go to the "Service accounts" Tab:**
   - Click on the **Service accounts** tab
   - Scroll down and click **Generate new private key**
   - Click **Generate key** in the confirmation dialog

3. **Download the JSON file:**
   - A `.json` file will be downloaded containing your service account credentials
   - This file contains sensitive information - **never commit it to version control**

4. **Extract the following values for your API `.env` file:**
   ```bash
   FURY_FIREBASE_PROJECT_ID=<project_id>
   FURY_FIREBASE_PRIVATE_KEY_ID=<private_key_id>
   FURY_FIREBASE_PRIVATE_KEY=<private_key>
   FURY_FIREBASE_CLIENT_EMAIL=<client_email>
   FURY_FIREBASE_CLIENT_ID=<client_id>
   FURY_FIREBASE_CLIENT_X509_CERT_URL=<client_x509_cert_url>
   ```

## Step 3: Obtain Web API Key (Required for Webapp)

The frontend webapp needs the Firebase Web API key for client-side authentication:

1. **Navigate to Project Settings:**
   - Click on the **⚙️ Gear Icon** in the left menu
   - Select **Project settings**

2. **Go to the "General" Tab:**
   - Scroll down to the **"Your apps"** section
   - If you already have a web app, click on it to find the configuration
   - If not, click **Add app** → Choose **Web** (</>) and register your app

3. **Copy the Firebase SDK configuration:**
   - Look for the **"Firebase SDK snippet"** section
   - Select **"Config"** format
   - You'll see something like:
     ```javascript
     const firebaseConfig = {
       apiKey: "AIza...",
       authDomain: "your-project.firebaseapp.com",
       projectId: "your-project",
       // ... other fields
     };
     ```

4. **Extract the following values for your webapp `.env.local` file:**
   ```bash
   NEXT_PUBLIC_FIREBASE_API_KEY=<apiKey>
   NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=<authDomain>
   NEXT_PUBLIC_FIREBASE_PROJECT_ID=<projectId>
   ```

5. **Also add the API Web Key to your API `.env` file:**
   ```bash
   FURY_FIREBASE_WEB_API_KEY=<apiKey>  # Same value as NEXT_PUBLIC_FIREBASE_API_KEY
   ```

## Step 4: Enable Authentication Methods

Enable the authentication methods you want to use:

1. In the Firebase Console, go to **Authentication** in the left menu
2. Click on the **Sign-in method** tab
3. Enable Google as the only authentication providers (this system as is, is only prepared for Google) 

# Data Model

The project uses a relational database (PostgreSQL) to manage core entities. Here's an overview of the key tables:

## Tables

### `organization`
- **Purpose**: Represents organizations (tenant grouping for multi-tenant support)
- **Key Fields**: `id` (PK), `name`
- **Relationships**: One-to-many with `user` table (cascade delete)

### `user`
- **Purpose**: Represents system users, each belonging to an organization
- **Key Fields**: `id` (PK), `firebase_id`, `name`, `email`, `organization_id` (FK), `status`, `date_joined`, `last_login`
- **Relationships**: Many-to-one with `organization` table (foreign key: `organization_id`)

### `earthquake`
- **Purpose**: Stores earthquake event data ingested from USGS
- **Key Fields**: `id` (PK), `external_id` (unique), `title`, `magnitude`, `place`, `latitude`, `longitude`, `depth_km`, `occurred_at`, `tsunami`, `ciim_geo_image_url`, and many more event-specific fields
- **Relationships**: Standalone table (no foreign keys)

## Data Relationships

```
organization (1) ──── (many) user
```

Each organization can have multiple users. Users are cascading deleted when their organization is deleted. Earthquakes are independently managed and not linked to users or organizations, allowing system-wide data access.

## Schema Management

Database schema changes are managed through **Alembic migrations**. For detailed information about creating, applying, and rolling back migrations, see the [Schema Management and Migrations](./api/README.md#schema-management-and-migrations) section in the API README.


# Architecture

## System Architecture

This system follows a **layered, cloud-native architecture**:

```
┌─────────────────────────────────────────────┐
│         Frontend (Next.js)                   │
│  - Server-side rendering & client-side UI   │
│  - Firebase authentication integration      │
│  - 3D earthquake visualization (Three.js)   │
└─────────────────┬───────────────────────────┘
                  │ HTTP/REST
┌─────────────────▼───────────────────────────┐
│   API Gateway / Load Balancer (K8s)         │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│   FastAPI Backend (Domain-Driven Design)    │
│                                             │
│  ┌───────────────────────────────────────┐  │
│  │ Controllers (HTTP Routing)            │  │
│  └────────────────┬────────────────────┘  │
│                   │                       │
│  ┌────────────────▼────────────────────┐  │
│  │ Services (Business Logic)           │  │
│  │ - Earthquake ingestion & filtering  │  │
│  │ - User & Organization management    │  │
│  │ - Image transformation              │  │
│  └────────────────┬────────────────────┘  │
│                   │                       │
│  ┌────────────────▼────────────────────┐  │
│  │ Repositories (Data Access Layer)    │  │
│  │ - Unit of Work pattern              │  │
│  │ - Generic SQL repository            │  │
│  │ - Transaction management            │  │
│  └────────────────┬────────────────────┘  │
│                   │                       │
└─────────────────┬┴───────────────────────┬─┘
                  │                         │
      ┌───────────▼──────────┐   ┌─────────▼──────────┐
      │  PostgreSQL (Primary)│   │  USGS Earthquake   │
      │     Database         │   │      API           │
      └──────────────────────┘   └────────────────────┘
```

## Possible Optimizations and Known Limitations

1. **Real-time Updates**: Earthquakes are ingested on-demand or via scheduled tasks, not in real-time. Expect delays of minutes to hours depending on the ingestion schedule.
2. **Historical Data**: Only earthquakes ingested after the system deployment are available. USGS historical data would require a one-time bulk ingest.
6. **Mobile Support**: The 3D visualization is optimized for desktop browsers; mobile support is limited.
7. **API Rate Limiting**: Not implemented; high-volume requests could impact performance. 
