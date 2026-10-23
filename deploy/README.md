# Deployment preparation

This folder contains reviewed preparation files, not an active deployment.

- `render.yaml.example`: API + PostgreSQL + private Redis + worker + one beat scheduler. This full topology uses paid service plans; review current pricing before applying it.
- `backend/.env.example`: reference values for backend environment settings. Do not copy local credentials into source control.
- `frontend/scripts/configure-production.mjs`: run before creating the Vercel deployment, using the real Render HTTPS origin. It writes the API-first rewrite, SPA fallback and frontend response headers.

The existing minimal `frontend/vercel.json` now uses `build:vercel`, which deliberately rejects missing API routing. Local `npm run build` still works. Do not point production at localhost or the temporary webhook tunnel.

Before a Render Blueprint is applied, manually create a shared environment group named `sprintlens-production`. Set a stable, privately generated 50+ character `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=0`, exact backend `DJANGO_ALLOWED_HOSTS` and exact frontend `DJANGO_CSRF_TRUSTED_ORIGINS`. All three Python processes must use the same key. Do not use `sync: false` inside an environment group; Render ignores that form.

Build/release/start commands (service root: `backend`):

```text
Build:      bash scripts/build.sh
Pre-deploy: bash scripts/release.sh
Start:      bash scripts/start.sh
Health:     /health/ready/
Worker:     python -m celery -A config worker --loglevel=INFO --concurrency=2
Beat:       python -m celery -A config beat --loglevel=INFO --schedule=/tmp/sprintlens-beat
```

Migrations run once in the API release phase, not independently in every worker/start process. Run a single beat instance and wait for migrations before allowing new-schema workers to consume work. Notifications deduplicate database records after schedule replay. Render's pre-deploy/shell/worker availability and service plans must be confirmed when Step 29 provisions real resources.

Detailed Hinglish walkthrough: [Step 28](../docs/architecture.md).
