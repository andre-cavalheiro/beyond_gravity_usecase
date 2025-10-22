# Beyond Gravity Webapp

## Introduction

A modern web application for earthquake monitoring and visualization. 

**Tech Stack:** Next.js 15 and React 19.

---

## Getting Started (Local Development)

### Prerequisites

- Node.js 20+
- Yarn package manager
- Firebase project (for authentication)
- Access to API (local or deployed)

### Environment Setup

1. Install dependencies:

```bash
yarn install
```

2. Configure environment variables by creating `.env.local` from the template (`.env.local.example`):

### Running the Application

Start the development server with:

```bash
yarn run dev
# or
make start
```

The application will be available at [http://localhost:3001](http://localhost:3001).

### Building for Production

```bash
yarn build       # Build the application
yarn start       # Start production server on port 3001
```

---

## Architecture

### Routing with the Next.js App Router

This project uses Next.js 15's App Router, which maps folders inside `app/` directly to URLs. Every nested folder represents a route segment, and a `page.tsx` file inside that folder becomes the entry point for that segment. Shared UI that wraps multiple pages lives in a sibling `layout.tsx`, and special files like `loading.tsx` or `error.tsx` opt you into additional behaviors.

Applied to this codebase:

- `app/page.tsx` renders the public landing page served at `/`.
- `app/(auth)/` is a route group. The parentheses keep the segment out of the URL but let us cluster all authenticated routes under the `app/(auth)/layout.tsx` shell (sidebar, auth gating, global toasts).
- `app/(auth)/home/page.tsx` produces `/home`, the main authenticated dashboard.
- `app/(auth)/home/[id]/page.tsx` is a dynamic segment that resolves to `/home/<earthquake-id>` for individual event detail views.
- `app/api/` is reserved for API route handlers. Dropping a `route.ts` file under a folder like `app/api/earthquakes` would expose it at `/api/earthquakes`.

### API Client Layer

The frontend talks to the backend through the helpers in `lib/api`. `lib/api/client.ts` wraps Axios with the base URL, injects Firebase ID tokens on every request, and centralizes error logging. Shared response contracts live in `lib/api/types.ts`, and `lib/api/mocks.ts` provides fixtures that can be toggled with the `NEXT_PUBLIC_USE_MOCKS` flag for local work without the live service. Screens call the exported helpers such as `getEarthquakes`, `getEarthquake`, and `ingestEarthquakes`, which keeps pagination, filtering, and authentication logic in one place.

### Component System

UI primitives live under `components/ui` and come from [shadcn/ui](https://ui.shadcn.com), a collection of Tailwind-ready, Radix-powered components that we own in the repo. The `components.json` manifest tracks our shadcn configuration, so adding something new is as simple as running `npx shadcn-ui@latest add <component>`. The generator drops the files into `components/ui/` using our aliases, and you can customize them like any other source file.

## Deploying to Kubernetes

### Deployment Workflow

A full deployment can be executed with:

```bash
make deploy
```

This command:
1. Builds and pushes a Docker image
2. Deploys the Helm chart to Kubernetes

### Manual Deployment Steps

1. **Ensure Kubernetes Context**

   ```bash
   make validate-context  # Check current context
   make set-context       # Switch to correct context/namespace
   ```

2. **Build and Push Docker Image**

   ```bash
   make docker-build-push
   ```

   This builds a multi-stage Docker image and pushes it to Docker Hub (`andrecavalheiro/beyond-gravity-usecase-webapp:latest`).

3. **Deploy Helm Chart**

   ```bash
   make push-helm
   ```

   Deploys or upgrades the webapp using the Helm chart in `deploy/helm/`.

4. **Test the Deployment**

   Forward a port to test connectivity:

   ```bash
   kubectl port-forward svc/beyond-gravity-usecase-webapp 3001:3001
   ```

   Then visit [http://localhost:3001](http://localhost:3001).

---
