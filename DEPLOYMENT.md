# Deployment Guide (FastAPI + React)

## Quick codebase review

This repo is already split in a way that is ideal for low-cost hosting:

- `server/` is a FastAPI app with a health endpoint (`/api/health`) and env-driven config.  
- `web/` is a Vite + React SPA that calls `/api/*`.  
- CORS is controlled by `COEVO_CORS_ORIGINS`, so hosting frontend/backend on different domains is supported.

### Risks to account for in production

- Default secrets are development-only (`COEVO_JWT_SECRET` and admin password defaults), so set real values in hosting env vars.
- SQLite (`COEVO_DB_URL` default) is fine for demos but not reliable on ephemeral free instances; for persistence, use a managed Postgres URL.
- Agent mode depends on Ollama (local inference), which is usually **not** available in free cloud tiers. Keep `COEVO_AGENT_ENABLED=0` unless you host model infra separately.

## Recommendation: best free hosting option

For a **FastAPI + React** app, the best free-ish path today is:

1. **Railway** for backend + optional frontend service (simplest monorepo deploy)
2. **Vercel** for frontend if you prefer static-first hosting

Why not Streamlit: Streamlit is excellent for Python dashboards, but this project already has a dedicated React frontend and a FastAPI API, so Streamlit would add unnecessary rewrite/maintenance overhead.

## Deploy backend on Render

### 1) Create a new Web Service

- Root directory: `server`
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### 2) Set environment variables

Required minimum:

- `COEVO_JWT_SECRET=<strong-random-secret>`
- `COEVO_CORS_ORIGINS=https://<your-vercel-domain>`
- `COEVO_AGENT_ENABLED=0`
- If enabling agents: `ANTHROPIC_API_KEY=<your-key>`

Optional:

- `COEVO_SEED_ADMIN=1`
- `COEVO_ADMIN_PASSWORD=<secure-password>`
- `COEVO_DB_URL=<postgres-connection-string>` (recommended for persistence)

### 3) Verify

- Open `https://<render-service>/api/health` and confirm `{"ok": true, ...}`.

## Deploy frontend on Vercel

### 1) Import repo

- Project root: `web`
- Framework preset: **Vite**
- Build command: `npm run build`
- Output directory: `dist`

### 2) Set environment variable

- `VITE_API_BASE=https://<your-render-service>`

### 3) SPA routing

A `web/vercel.json` is included so client-side React Router routes resolve to `index.html`.

## Included deployment config files

- `render.yaml` (blueprint for backend service)
- `web/vercel.json` (SPA rewrites)

These are optional but useful for reproducible setup.


## Deploy both services on Railway

Two Railway config files are included:

- `server/railway.json` for FastAPI
- `web/railway.json` for React (Vite preview server)

### Backend service (Railway)

- Service root: `server`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Env vars:
  - `COEVO_JWT_SECRET=<strong-secret>`
  - `COEVO_CORS_ORIGINS=https://<frontend-domain>`
  - `COEVO_AGENT_ENABLED=1` (optional)
  - `ANTHROPIC_API_KEY=<your-key>` (required if agents enabled)

### Frontend service (Railway)

- Service root: `web`
- Build command: `npm install && npm run build`
- Start command: `npm run preview -- --host 0.0.0.0 --port $PORT`
- Env vars:
  - `VITE_API_BASE=https://<backend-domain>`
