# Run in Cloud – Weekday Market Hours (9:15 AM–3:30 PM IST)

Deploy the app to the cloud and run it **only on weekdays**, **starting in the morning** and **ending at 3:30 PM** after market hours.

**→ For a step-by-step hosting guide (Vercel + Render, copy-paste ready), see [HOST-IN-CLOUD.md](../HOST-IN-CLOUD.md) in the project root.**

---

## 1. Architecture

| Component | Where to host | Notes |
|-----------|----------------|------|
| **Frontend (Next.js)** | [Vercel](https://vercel.com) | Free tier, always on. Set `NEXT_PUBLIC_API_URL` to your backend URL. |
| **Backend (FastAPI)** | [Render](https://render.com) or [Railway](https://railway.app) | Free/low-cost. Use **scheduled keep-alive** so it runs only during market hours (see below). |

**Upstox:** In the [Upstox Developer Console](https://upstox.com/developer/dashboard), set the **Redirect URI** to your **deployed frontend** callback, e.g. `https://your-app.vercel.app/auth/callback` (no trailing slash).

---

## 2. Deploy Frontend (Vercel)

1. Push your code to GitHub (you already have the repo).
2. Go to [vercel.com](https://vercel.com) → **Add New** → **Project** → import your repo.
3. **Root Directory:** set to `web` (or leave default and set in build settings).
4. **Build settings:** Framework Preset = Next.js; build command `npm run build`; output = default.
5. **Environment variable:**  
   `NEXT_PUBLIC_API_URL` = `https://your-backend-url.onrender.com` (or your Railway backend URL). No trailing slash.
6. Deploy. After deploy, set Upstox Redirect URI to `https://<your-vercel-domain>/auth/callback`.

---

## 3. Deploy Backend (Render or Railway)

### 3a. Render

1. [render.com](https://render.com) → **New** → **Web Service**.
2. Connect your repo. **Root Directory:** leave empty or set to repo root.
3. **Build Command:** (optional) if using Docker, use Docker; else e.g. `cd backend && pip install -e .`
4. **Start Command:** `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT` (Render sets `PORT`).
5. **Environment:** Add all vars from your `.env` (e.g. `UPSTOX_CLIENT_ID`, `UPSTOX_CLIENT_SECRET`, `UPSTOX_OAUTH_REDIRECT_URI` = `https://your-vercel-app.vercel.app/auth/callback`, `FRONTEND_URL`, etc.). No secrets in the repo.
6. **Free tier:** Service may **spin down after ~15 min inactivity**. We will keep it awake only during market hours with a scheduled ping (see §5).

### 3b. Railway

1. [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub** → select repo.
2. Set **Root Directory** to `backend` if needed, or use a Dockerfile in repo root that builds the API.
3. Add **Variables** from `.env` (same as above).
4. Expose port (Railway usually detects 8000). Note the public URL.

---

## 4. Weekday Schedule (Mon–Fri, 9:15 AM–3:30 PM IST)

- **Market open:** 9:15 AM IST  
- **Market close:** 3:30 PM IST  
- **Goal:** Backend is **up only on weekdays**, from before 9:15 AM until after 3:30 PM.

Two ways to achieve this:

- **A. Render/Railway + keep-alive:** Backend is allowed to spin down when idle. An external cron **pings the backend only on weekdays between 9:00 and 15:30 IST** so it stays awake during market hours. After 15:30, we stop pinging → backend spins down.
- **B. VPS + start/stop:** Backend runs on a small VPS (e.g. DigitalOcean, Linode). A system cron **starts** the backend before 9:15 and **stops** it after 3:30 on weekdays only.

---

## 5. Option A – Keep-Alive During Market Hours (Render/Railway)

Use a free cron service to call your backend **only on weekdays** and **only between 9:00 and 15:30 IST** so the service stays awake during market hours and spins down after.

### 5.1 Cron-job.org (free)

1. Go to [cron-job.org](https://cron-job.org) and create an account.
2. **Create Cronjob:**
   - **URL:** `https://YOUR-BACKEND-URL/api/v1/health`  
     Example: `https://your-app.onrender.com/api/v1/health`
   - **Schedule:** Every **10 minutes** (so the backend doesn’t spin down).
   - **Time range:** Only between **9:00 and 15:30** in your timezone.

Cron-job.org uses **server time**. IST = UTC+5:30.

- **9:00 IST** = 3:30 UTC  
- **15:30 IST** = 10:00 UTC  

So in cron-job.org (if it uses UTC):

- **From:** 03:30  
- **To:** 10:00  
- **Days:** Mon–Fri  

If the site uses “local” time, set your profile to **Asia/Kolkata** and use 9:00–15:30.

### 5.2 UptimeRobot (free)

1. [uptimerobot.com](https://uptimerobot.com) → **Add New Monitor**.
2. **Monitor Type:** HTTP(s).  
3. **URL:** `https://YOUR-BACKEND-URL/api/v1/health`  
4. **Monitoring Interval:** 5 minutes.  
5. UptimeRobot does **not** support “only weekdays 9–15:30” out of the box; it pings 24/7. So the backend will stay up all the time unless you use a different tool (e.g. cron-job.org) or a small script (see §6).

**Recommendation:** Use **cron-job.org** with the 9:00–15:30 IST window and Mon–Fri so the backend is only woken during market hours.

---

## 6. Option B – VPS with Start/Stop (Mon–Fri 9:15–3:30 IST)

On a Linux VPS you can start the backend in the morning and stop it after 3:30 PM on weekdays.

### 6.1 One-time setup on VPS

- Install Python 3.11+, create a venv, clone repo, install backend deps, add `.env`.
- Use a process manager so the API runs in the background (e.g. `systemd` or a simple `nohup`/`screen`).

### 6.2 Start/stop scripts (IST, weekdays only)

**Start (e.g. `/opt/algo-trading/start-backend.sh`):**

```bash
#!/bin/bash
# Run before 9:15 AM IST on weekdays
cd /opt/algo-trading/backend
source .venv/bin/activate
export $(grep -v '^#' .env | xargs)
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 >> /var/log/algo-api.log 2>&1 &
echo $! > /tmp/algo-api.pid
```

**Stop (e.g. `/opt/algo-trading/stop-backend.sh`):**

```bash
#!/bin/bash
# Run after 3:30 PM IST on weekdays
if [ -f /tmp/algo-api.pid ]; then
  kill $(cat /tmp/algo-api.pid) 2>/dev/null
  rm -f /tmp/algo-api.pid
fi
```

Make them executable: `chmod +x start-backend.sh stop-backend.sh`

### 6.3 Crontab (IST assumed; adjust if server is UTC)

Server in **IST** (or use `TZ=Asia/Kolkata` in cron):

```cron
# Start backend on weekdays at 9:00 AM IST
0 9 * * 1-5 /opt/algo-trading/start-backend.sh

# Stop backend on weekdays at 3:35 PM IST
35 15 * * 1-5 /opt/algo-trading/stop-backend.sh
```

If the server uses **UTC**, 9:00 IST = 3:30 UTC and 15:35 IST = 10:05 UTC:

```cron
30 3 * * 1-5 /opt/algo-trading/start-backend.sh
5 10 * * 1-5 /opt/algo-trading/stop-backend.sh
```

---

## 7. Summary

| Goal | Solution |
|------|----------|
| Run in cloud | Deploy frontend on Vercel, backend on Render or Railway (or VPS). |
| Start in the morning | **Render/Railway:** Keep-alive cron from 9:00 IST. **VPS:** Cron runs `start-backend.sh` at 9:00 IST. |
| End at 3:30 PM (weekdays) | **Render/Railway:** Stop pinging after 15:30 IST → backend spins down. **VPS:** Cron runs `stop-backend.sh` at 15:35 IST. |
| Weekdays only (Mon–Fri) | **Cron-job.org:** Set schedule to Mon–Fri. **VPS crontab:** Use `1-5` in the day-of-week field. |

After setup, open your **Vercel frontend URL** in the morning on a weekday; the backend will be up during market hours and will stop (or spin down) after 3:30 PM.

---

## 8. Start and monitor from mobile and laptop (one URL)

Once the app is deployed (frontend on Vercel, backend on Render/Railway), you use **one dashboard URL** from both your **mobile** and **laptop**. No need to “start” the app on each device — it’s already running in the cloud.

### One URL for all devices

| Device   | What to do |
|----------|------------|
| **Laptop** | Open your Vercel URL in Chrome, Edge, or Safari (e.g. `https://your-app.vercel.app`). |
| **Mobile** | Open the **same URL** in your phone’s browser (Chrome or Safari). You can also **Add to Home Screen** for an app-like icon. |

The dashboard is responsive: it works on phone and laptop. You can start your session from either device and monitor from the other.

### What you can do from both devices

- **Connect Upstox** — Log in with Upstox (OAuth) once from either device. The backend stores the session, so both devices see the same connected account.
- **Monitor trades** — View **Positions**, **Order history**, **Signals**, and **Holdings / opportunities** from the same dashboard.
- **Market context** — NIFTY / SENSEX LTP, bias, and extended context (when the backend is up).
- **Trade settings** — Adjust strike, target premium, and holdings strategy from either device.

### Tips

- **Bookmark** the Vercel URL on both phone and laptop so you can open it quickly.
- **Mobile:** For a full-screen experience, use “Add to Home Screen” (Chrome: menu → Add to Home screen; Safari: Share → Add to Home Screen).
- **Backend spin-down:** If you use Render/Railway free tier with keep-alive only during market hours, the first load after a spin-down may take 30–60 seconds. After that, both devices use the same live backend.
