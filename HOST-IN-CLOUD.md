# Host Algo Trading in the Cloud – Step by Step

Follow this guide to host your app so you can open it from **any device** (laptop, phone) at one URL. You will deploy:

1. **Frontend (dashboard)** → **Vercel** (free)
2. **Backend (API)** → **Render** (free tier) or **Railway**

**Time:** about 15–20 minutes.

---

## Before you start

- [ ] Code is pushed to **GitHub** (e.g. `srinivasdasari2023/Dasari-Algo-trading`).
- [ ] You have an **Upstox** developer account and an app with **Client ID** and **Client Secret**.
- [ ] You have accounts on [Vercel](https://vercel.com) and [Render](https://render.com) (or [Railway](https://railway.app)) — sign up with GitHub.

---

## Part 1: Deploy backend (Render)

The backend serves the API. Deploy it first so you have a URL for the frontend.

### 1.1 Create the Web Service

1. Go to **[render.com](https://render.com)** and log in (e.g. with GitHub).
2. Click **Dashboard** → **New +** → **Web Service**.
3. **Connect your repo:**  
   If your repo is not listed, click **Connect account** and allow Render to access GitHub, then select **Dasari-Algo-trading** (or your repo name).
4. Click **Connect** next to the repo.

### 1.2 Configure the service

Use these **exact** values (adjust names if you prefer):

| Field | Value |
|-------|--------|
| **Name** | `algo-trading-api` (or any name) |
| **Region** | Choose closest to you (e.g. Singapore / Oregon) |
| **Branch** | `main` |
| **Root Directory** | **`backend`** (so Render runs build/start from the backend folder) |
| **Runtime** | **Python 3** |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |

Render sets `PORT` automatically. The repo has **`backend/requirements.txt`** so this build works. If you leave Root Directory empty instead, use Build: `cd backend && pip install -r requirements.txt` and Start: `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT`.

### 1.3 Environment variables

Click **Advanced** → **Add Environment Variable**. Add these **one by one** (use your real values):

| Key | Value | Notes |
|-----|--------|--------|
| `JWT_SECRET` | *(random long string, 32+ chars)* | e.g. use a password generator |
| `UPSTOX_CLIENT_ID` | *(from Upstox developer dashboard)* | Your app’s Client ID |
| `UPSTOX_CLIENT_SECRET` | *(from Upstox developer dashboard)* | Your app’s Client Secret |
| `UPSTOX_OAUTH_REDIRECT_URI` | `https://YOUR-VERCEL-URL/auth/callback` | **Replace** `YOUR-VERCEL-URL` in **Part 2** after you get it; then come back and add/update this in Render |
| `FRONTEND_URL` | `https://YOUR-VERCEL-URL` | Same: set after Part 2, no trailing slash |
| `APP_ENV` | `production` | Optional |
| `LOG_LEVEL` | `INFO` | Optional |

**Minimal for first deploy:** `JWT_SECRET`, `UPSTOX_CLIENT_ID`, `UPSTOX_CLIENT_SECRET`.  
**After Part 2:** add `UPSTOX_OAUTH_REDIRECT_URI` and `FRONTEND_URL` with your real Vercel URL.

If you use **PostgreSQL/Redis** in the cloud, add `DATABASE_URL` and `REDIS_URL` here too.

### 1.4 Deploy

1. Click **Create Web Service**.
2. Wait for the first deploy (a few minutes). The log should end with something like “Your service is live at …”.
3. Copy the **URL** (e.g. `https://algo-trading-api.onrender.com`). You need it for the frontend.

**Note:** On the free tier, the service may **spin down** after ~15 minutes of no traffic. The first request after that can take 30–60 seconds. Optional: use [cron-job.org](https://cron-job.org) to ping `https://YOUR-RENDER-URL/api/v1/health` every 10 minutes during market hours (see [docs/CLOUD_AND_SCHEDULE.md](docs/CLOUD_AND_SCHEDULE.md)).

---

## Part 2: Deploy frontend (Vercel)

The frontend is the dashboard you open in the browser.

### 2.1 Import the project

1. Go to **[vercel.com](https://vercel.com)** and log in (e.g. with GitHub).
2. Click **Add New…** → **Project**.
3. Import your **GitHub** repo (e.g. `Dasari-Algo-trading`). If you don’t see it, adjust Vercel’s GitHub permissions.
4. Click **Import** (don’t deploy yet).

### 2.2 Configure the project

| Field | Value |
|-------|--------|
| **Project Name** | e.g. `dasari-algo-trading` (Vercel will give a URL like `dasari-algo-trading.vercel.app`) |
| **Root Directory** | Click **Edit** → set to **`web`** → **Continue** |
| **Framework Preset** | Next.js (should be auto-detected) |
| **Build Command** | Leave default (`npm run build`) |
| **Output Directory** | Leave default |

### 2.3 Environment variable (required)

Add **one** variable:

| Key | Value |
|-----|--------|
| `NEXT_PUBLIC_API_URL` | `https://YOUR-RENDER-URL` |

Replace `YOUR-RENDER-URL` with the **backend URL** from Part 1 (e.g. `https://algo-trading-api.onrender.com`).  
**No trailing slash.**

### 2.4 Deploy

1. Click **Deploy**.
2. Wait for the build to finish (1–2 minutes).
3. Copy your **Vercel URL** (e.g. `https://dasari-algo-trading.vercel.app`).

### 2.5 Point backend to frontend (important)

1. Go back to **Render** → your **algo-trading-api** service → **Environment**.
2. Add or update:
   - `UPSTOX_OAUTH_REDIRECT_URI` = `https://YOUR-VERCEL-URL/auth/callback`  
     (e.g. `https://dasari-algo-trading.vercel.app/auth/callback`)
   - `FRONTEND_URL` = `https://YOUR-VERCEL-URL`  
     (e.g. `https://dasari-algo-trading.vercel.app`)
3. Save. Render will **redeploy** automatically.

### 2.6 Set Upstox Redirect URI

1. Open **[Upstox Developer Console](https://upstox.com/developer/dashboard)**.
2. Open your app → **Redirect URI**.
3. Add: `https://YOUR-VERCEL-URL/auth/callback`  
   (exactly the same as `UPSTOX_OAUTH_REDIRECT_URI`, no trailing slash).
4. Save.

---

## Part 3: Use the app

1. Open your **Vercel URL** in a browser (e.g. `https://dasari-algo-trading.vercel.app`).
2. Click **Connect** / **Login with Upstox** and complete OAuth.
3. You can use the **same URL** on your **laptop** and **phone** to start and monitor trades.

---

## Quick checklist

| Step | Done? |
|------|--------|
| 1. Backend on Render: Build `cd backend && pip install -e .`, Start `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT` | |
| 2. Render env: `JWT_SECRET`, `UPSTOX_CLIENT_ID`, `UPSTOX_CLIENT_SECRET` | |
| 3. Frontend on Vercel: Root = `web`, env `NEXT_PUBLIC_API_URL` = Render URL | |
| 4. Render env: `UPSTOX_OAUTH_REDIRECT_URI` and `FRONTEND_URL` = Vercel URL | |
| 5. Upstox: Redirect URI = `https://YOUR-VERCEL-URL/auth/callback` | |
| 6. Open Vercel URL and connect Upstox | |

---

## Troubleshooting

| Issue | What to do |
|--------|------------|
| **“Backend unreachable”** on dashboard | Check `NEXT_PUBLIC_API_URL` in Vercel (no trailing slash). Open `https://YOUR-RENDER-URL/api/v1/health` in a browser; you should see `{"status":"ok",...}`. |
| **Upstox login fails / redirect error** | Redirect URI in Upstox must match **exactly**: `https://YOUR-VERCEL-URL/auth/callback`. Same as `UPSTOX_OAUTH_REDIRECT_URI` in Render. |
| **Render build fails** | Ensure **Root Directory** is empty and Build Command is `cd backend && pip install -e .`. Check the build log for Python errors. |
| **Vercel build fails** | Ensure **Root Directory** is **`web`** so Vercel runs `npm run build` inside the Next.js app. |

For **market-hours only** (backend awake only 9:15–15:30 IST on weekdays), see [docs/CLOUD_AND_SCHEDULE.md](docs/CLOUD_AND_SCHEDULE.md).
