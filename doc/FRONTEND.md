# Frontend

The Next.js web application in `frontend/` provides the user interface for DistillNews.

## Contents

- [Tech Stack](#tech-stack)
- [Local Setup](#local-setup)
- [Environment Variables](#environment-variables)
- [Docker Build & Container Deployment](#docker-build--container-deployment)

## Tech Stack

- **Framework**: Next.js (App Router)
- **Language**: TypeScript / JavaScript
- **Styling**: Tailwind CSS, Lucide icons
- **State & Data Fetching**: React Hooks, fetch API

## Local Setup

```bash
cd frontend
npm ci
printf 'NEXT_PUBLIC_API_URL=http://localhost:8000\n' > .env.local
npm run dev
```

The app will start at `http://localhost:3000`.

## Environment Variables

Create a `frontend/.env.local` file for local development:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

`NEXT_PUBLIC_API_URL` is compiled into the browser bundle during build time, so rebuild or restart the dev server after changing it. Do not put API keys, database URLs, or other server secrets in frontend environment files.

## Docker Build & Container Deployment

From the `frontend/` directory, build and run using container build args:

```bash
NEXT_PUBLIC_API_URL=https://api.example.com docker compose up --build
```

For full-stack deployment alongside backend services, run `docker compose up --build` from the repository root.
