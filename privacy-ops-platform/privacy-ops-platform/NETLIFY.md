# Hosting on Netlify — read this first

Netlify is a **static-site / JAMstack host with serverless functions**. It
does not run long-lived containers, a persistent PostgreSQL database, Redis,
or a FastAPI process. That means **this repository's backend cannot run on
Netlify as-is** — there is nowhere for `docker-compose.yml`, Postgres, or
the FastAPI app to live.

What Netlify *can* host from this repo, and what it can't:

| Piece | Works on Netlify? | Notes |
|---|---|---|
| `frontend/` (Next.js) | ✅ Yes, with caveats | Netlify supports Next.js via its Next Runtime, but this scaffold's frontend is a plain client-rendered app that expects an API at `/api/*`. On Netlify there is no Nginx/FastAPI behind that path, so every page will fail to fetch data unless you also stand up the backend somewhere else and point the frontend at it (see below). |
| `backend/` (FastAPI + Postgres + Redis + MinIO) | ❌ No | Needs a real container host. Options: a VM/VPS with Docker Compose (matches this repo as-is), a managed container service (AWS ECS/Fargate, Azure Container Apps, Google Cloud Run), or Kubernetes (the architecture doc notes the migration path). |
| `docker-compose.yml` | ❌ No | Netlify has no Docker Compose support at all. |

## If you want to see the frontend live on Netlify anyway

1. Deploy the `backend/` (and Postgres/Redis/MinIO) somewhere that runs
   containers — e.g. a small VPS with `docker compose up -d`, or a managed
   platform.
2. Point the frontend at that backend's public URL instead of the local
   Nginx proxy: replace the `rewrites()` block in
   `frontend/next.config.js` with your deployed API's URL, or set an
   environment variable the app reads at build time.
3. In Netlify: **New site from Git** → point at this repo → set the base
   directory to `frontend` → build command `npm run build` → publish
   directory `.next` (Netlify's Next Runtime handles the rest).
4. Set `OIDC_REDIRECT_URI` and CORS (`CORS_ALLOWED_ORIGINS` on the backend)
   to match the Netlify URL you're deploying to, or auth and API calls
   will fail with CORS/redirect errors.

## Recommended path instead

Because this is an internal, self-hosted privacy tool handling sensitive
compliance data (per the architecture's "self-hosted, company-controlled
infrastructure" requirement — see `docs/architecture.md` Section 30), the
more consistent option is to skip Netlify entirely and deploy the whole
`docker-compose.yml` stack to your own infrastructure (a company VM,
Azure/AWS VM, or later Kubernetes), which is what this scaffold is actually
built for.
