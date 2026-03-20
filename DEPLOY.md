# Deployment Guide — Free Hosting (Vercel + Fly.io)

## Architecture
```
Browser → Vercel (Next.js frontend)
              ↓
       Fly.io (Flask backend + aria2 + SQLite)
              ↓ (volume)
       /app/data   — persistent SQLite + poster cache
       /app/downloads — download dir
```

Both platforms give you **free TLS (HTTPS)** automatically.

---

## Prerequisites (one-time installs)

```bash
# Node (for frontend deploy)
# Install from: https://nodejs.org

# Vercel CLI
npm install -g vercel

# Fly.io CLI
# Windows: winget install flyio.flyctl
# or: iwr https://fly.io/install.ps1 -useb | iex

# Git (project must be in a GitHub repo)
```

---

## Step 1 — Push project to GitHub

```bash
cd "F:\Softwares\projects\movie project"
git init          # skip if already a repo
git add .
git commit -m "initial deploy"

# Create a NEW repo on https://github.com/new then:
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

---

## Step 2 — Deploy backend to Fly.io

```bash
# Login
fly auth login

# Create the app (run once)
fly launch --name movie-project-backend --region ord --no-deploy

# Create a persistent volume (keeps DB + posters alive across redeploys)
fly volumes create movie_data --size 5 --region ord

# Set secrets (NEVER commit these to git)
fly secrets set `
  SECRET_KEY="$(openssl rand -hex 32)" `
  ARIA2_RPC_SECRET="$(openssl rand -hex 24)" `
  ALLOWED_ORIGINS="https://YOUR_VERCEL_APP.vercel.app"

# Deploy
fly deploy

# Check it's healthy
fly open /api/health
```

> After deploy, note your backend URL: `https://movie-project-backend.fly.dev`

---

## Step 3 — Deploy frontend to Vercel

```bash
cd "F:\Softwares\projects\movie project\web"

# Login
vercel login

# Deploy (follow prompts — select the web/ folder as root)
vercel --prod

# When asked for env variables, add:
#   NEXT_PUBLIC_API_URL = https://movie-project-backend.fly.dev
```

Or use the web dashboard:
1. Go to https://vercel.com/new
2. Import your GitHub repo, set **Root Directory** = `web`
3. Add env var: `NEXT_PUBLIC_API_URL` = `https://movie-project-backend.fly.dev`
4. Click **Deploy**

---

## Step 4 — Update ALLOWED_ORIGINS with real Vercel URL

Once Vercel assigns your URL (e.g. `https://my-movie.vercel.app`):

```bash
fly secrets set ALLOWED_ORIGINS="https://my-movie.vercel.app"
fly deploy
```

---

## Step 5 — Verify everything works

```bash
# Backend health
curl https://movie-project-backend.fly.dev/api/health

# Movie list
curl "https://movie-project-backend.fly.dev/api/movies?limit=10"

# Frontend
open https://YOUR_VERCEL_APP.vercel.app
```

---

## Ongoing operations

| Task | Command |
|---|---|
| Redeploy backend | `fly deploy` |
| View backend logs | `fly logs` |
| SSH into backend | `fly ssh console` |
| Redeploy frontend | `vercel --prod` (from `web/`) |
| Rotate secrets | `fly secrets set KEY=newvalue` |
| Resize volume | `fly volumes extend VOLUME_ID --size 10` |

---

## Security checklist

- [x] TLS — automatic on both Vercel (frontend) and Fly (backend)
- [x] CORS — locked to your Vercel origin via `ALLOWED_ORIGINS`
- [x] Flask `SECRET_KEY` — set via fly secret (not hardcoded)
- [x] aria2 RPC — binds to `127.0.0.1` only (not exposed publicly)
- [x] aria2 `--rpc-secret` — set via env var
- [x] No secrets committed to git (`.gitignore` + `.env.example`)
- [ ] Optional: add a simple API key check to download endpoints
- [ ] Optional: set up SQLite backup to Cloudflare R2 / Backblaze B2

---

## Free tier limits (as of 2026)

| Platform | Free limit |
|---|---|
| Vercel | 100 GB bandwidth/mo, unlimited deploys |
| Fly.io | 3 shared VMs, 3 GB volume storage, 160 GB transfer/mo |
