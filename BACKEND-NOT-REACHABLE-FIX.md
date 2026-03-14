# Backend Not Reachable / Dashboard Errors – Fix Checklist

Use this checklist to **remove** "Backend unreachable" and dashboard errors. Do the steps **in order**.

---

## 1. Backend must be running and stay running

The dashboard (Next.js on port 3000) talks to the **backend API** (FastAPI on port **8000**). If nothing is listening on 8000, you get:

- **"Backend unreachable"** on the dashboard  
- **ECONNREFUSED 127.0.0.1:8000** in the browser or terminal  
- **socket hang up / ECONNRESET** if the backend was up but then stopped or crashed  

**Rule:** Start the **backend first** (or together with the web app) and **keep its window open**. Closing the backend window stops the API and causes these errors.

---

## 2. Checklist to fix “Backend not reachable”

Do these in order. Tick when done.

### Step A: Start the backend (choose one)

- [ ] **Option 1 – One script (easiest)**  
  From project root in PowerShell:
  ```powershell
  .\Start-All.ps1
  ```
  This opens **two** windows (backend + web) and the browser. **Keep both windows open.**

- [ ] **Option 2 – Backend only, then web**  
  **Terminal 1** (project root):
  ```powershell
  .\Start-Backend.ps1
  ```
  Leave this window open.  
  **Terminal 2** (project root):
  ```powershell
  cd web; npm run dev
  ```
  Leave this window open.

- [ ] **Option 3 – VS Code**  
  Open project folder in VS Code → **Ctrl+Shift+P** → **Run Task** → **Start All**.  
  Keep both terminals in the Terminal panel open. Open **http://localhost:3000** in the browser.

### Step B: Confirm backend is running

- [ ] In the **backend** terminal you should see something like:
  ```text
  Uvicorn running on http://0.0.0.0:8000
  ```
- [ ] In the browser open: **http://localhost:8000/api/v1/health**  
  You should see: `{"status":"ok","service":"capitalguard-api"}`  
  If you see that, the backend is reachable. If the page fails to load, the backend is **not** running or not on port 8000.

### Step C: Open the dashboard (not the API)

- [ ] In the browser open: **http://localhost:3000**  
  Do **not** use port 8000 for the dashboard. Port 3000 = dashboard; port 8000 = API.

### Step D: If the dashboard still shows “Backend unreachable”

- [ ] Click **Retry** on the dashboard (it will re-check the backend).
- [ ] If you just started the backend, wait a few seconds and click **Retry** again.
- [ ] Confirm no firewall or antivirus is blocking **localhost:8000**.
- [ ] Restart: close the **backend** terminal, start it again (Step A), then reload **http://localhost:3000**.

---

## 3. First-time setup (if backend won’t start)

If the backend script fails or you see “python not found” / “.venv not found”:

- [ ] **Python 3.11+** installed and in PATH. Check: `python --version`
- [ ] **Create backend virtual environment** (from project root):
  ```powershell
  cd backend
  python -m venv .venv
  .\.venv\Scripts\Activate.ps1
  pip install -e ".[dev]"
  cd ..
  ```
- [ ] Then start the backend again (Step A).

---

## 4. “Socket hang up” / ECONNRESET on holdings or other API calls

This usually means the backend **closed the connection** (crashed, restarted, or request took too long).

- [ ] **Restart the backend:** in its terminal press **Ctrl+C**, then start it again (Step A).
- [ ] **Keep the backend window open**; don’t close it while using the dashboard.
- [ ] On the dashboard, click **Retry** after the backend is back.
- [ ] If it keeps happening, check the **backend terminal** for Python errors and fix or report them.

---

## 5. Quick reference

| What you want           | What to run / open |
|-------------------------|--------------------|
| Backend + web together  | `.\Start-All.ps1` (from project root) |
| Backend only            | `.\Start-Backend.ps1` (from project root) |
| Web only                | `cd web; npm run dev` (backend must already be running) |
| Check backend is up     | Open **http://localhost:8000/api/v1/health** in browser |
| Open dashboard          | **http://localhost:3000** |
| Stop everything         | Close the backend and web terminal windows (or Ctrl+C in each) |

---

## 6. Summary

1. **Start the backend** (and keep it running).  
2. **Start the web app** if not using `Start-All.ps1`.  
3. Open **http://localhost:3000** for the dashboard.  
4. If you see “Backend unreachable”, use **Retry** or restart the backend and try again.  

For full run instructions and troubleshooting, see **[HOW-TO-RUN.md](HOW-TO-RUN.md)**.
