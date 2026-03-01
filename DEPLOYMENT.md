# CoEvo Deployment Guide (v0.8.0)

This guide documents production-ready deployment for the current split architecture:

- `server/` → FastAPI backend
- `web/` → React + Vite frontend

CoEvo remains local-first in design. Cloud deploys are optional and mainly useful for public demos.

## 1) Release deployment checklist

Before publishing a GitHub release:

1. Set a strong `COEVO_JWT_SECRET` (do not use defaults).
2. Set a real admin password if using seeded admin.
3. Configure CORS to exact frontend origins.
4. Keep agents disabled unless model infrastructure and API keys are configured.
5. Verify backend health endpoint (`/api/health`) after deployment.

## 2) Required environment variables

### Backend (`server/`)

Minimum required for public deployment:

```env
COEVO_JWT_SECRET=replace-with-a-strong-random-secret
COEVO_CORS_ORIGINS=https://coevo-web.vercel.app
COEVO_AGENT_ENABLED=0
```

Common optional variables:

```env
COEVO_SEED_ADMIN=1
COEVO_ADMIN_PASSWORD=replace-with-strong-admin-password
COEVO_DB_URL=postgresql+psycopg://user:password@host:5432/coevo
COEVO_WEBHOOK_SECRET=replace-with-webhook-secret
COEVO_SMTP_HOST=smtp.mailprovider.com
COEVO_SMTP_PORT=587
COEVO_SMTP_USER=notifications@example.com
COEVO_SMTP_PASSWORD=replace-with-smtp-password
COEVO_SMTP_FROM=CoEvo <notifications@example.com>
```

If enabling agents:

```env
COEVO_AGENT_ENABLED=1
COEVO_DEFAULT_AGENT_MODEL=claude-3-5-haiku-latest
ANTHROPIC_API_KEY=your-anthropic-api-key
# or OPENAI_API_KEY / XAI_API_KEY / GEMINI_API_KEY depending on provider
# or COEVO_OLLAMA_URL when self-hosting Ollama
```

### Frontend (`web/`)

```env
VITE_API_BASE=https://your-backend.example.com
```

## 3) Deploy backend on Render

1. Create a **Web Service** from this repo.
2. Set **Root Directory** to `server`.
3. Use build command:
   ```bash
   pip install -r requirements.txt
   ```
4. Use start command:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```
5. Add backend env vars from the section above.
6. Verify:
   - `https://your-backend.example.com/api/health`

`render.yaml` is included as a baseline template for Render Blueprint deployments.

## 4) Deploy frontend on Vercel

1. Import this repo in Vercel.
2. Set **Root Directory** to `web`.
3. Framework preset: **Vite**.
4. Build command:
   ```bash
   npm run build
   ```
5. Output directory: `dist`.
6. Set `VITE_API_BASE=https://your-backend.example.com`.

`web/vercel.json` already includes SPA rewrites so client routes resolve to `index.html`.

## 5) Deploy both services on Railway

### Backend service

- Root directory: `server`
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Use backend env vars from this document.

### Frontend service

- Root directory: `web`
- Build command: `npm install && npm run build`
- Start command: `npm run start`
- Set `VITE_API_BASE=https://your-backend.example.com`

`server/railway.json` and `web/railway.json` are included for reproducible Railway deploy settings.

## 6) Public demo defaults (recommended)

For the simplest public demo setup:

- `COEVO_AGENT_ENABLED=0`
- Use managed Postgres for persistence (`COEVO_DB_URL=postgresql+psycopg://...`)
- Restrict CORS to the exact frontend URL
- Set a strong admin password if admin seeding is enabled

This keeps operational complexity low while preserving the off-chain signed-ledger core behavior.
