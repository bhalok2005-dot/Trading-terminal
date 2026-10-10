# Deployment

## Local development

Use Docker Compose for PostgreSQL and the app stack:

```bash
docker compose up --build
```

## Production

- Frontend: Vercel
- Backend and database: Render Blueprint in `render.yaml`

### Render API and PostgreSQL

1. Push the repository to GitHub and create a new Render Blueprint from it.
2. Deploy the Blueprint. It provisions the FastAPI service and PostgreSQL database, runs Alembic migrations before startup, and generates `JWT_SECRET`.
3. Copy the deployed API URL, for example `https://trading-dashboard-api.onrender.com`.

The Blueprint uses free plans for an initial trial. Check Render's current limits and select a persistent paid database plan before storing important account or trading data.

### Vercel frontend

1. Import the same GitHub repository as a Vercel project.
2. Set **Root Directory** to `frontend`; keep the detected Next.js framework and default build settings.
3. Set `NEXT_PUBLIC_API_URL` to the Render API URL without a trailing slash. Apply it to the Vercel environments you deploy, then deploy or redeploy. Next.js bundles this public variable at build time.
4. Copy the Vercel deployment URL.

### Connect browser and API

In the Render API service's environment settings, set `CORS_ORIGINS` to a JSON array containing the Vercel URL and any local development origins you need. For example:

```text
["https://your-dashboard.vercel.app","http://localhost:3000","http://127.0.0.1:3000"]
```

Save the setting and wait for Render to redeploy. Add preview deployment origins separately if browser login is needed on previews.

Verify `https://<your-api-host>/health` returns `{"status":"ok"}`, then use **Register** on the Vercel site to create an account and sign in. The Vercel frontend must not use `localhost:8000` as its API URL.

## Environment requirements

- backend `DATABASE_URL` pointing to production PostgreSQL
- `JWT_SECRET` set to a secure secret
- `AI_API_KEY` if an AI service is enabled later
- `MT5_CONFIG` or equivalent broker config

## Deployment checklist

1. configure production environment variables
2. verify backend tests and frontend build locally
3. deploy database first
4. deploy backend
5. deploy frontend
6. confirm health checks and auth flow
