# How to Run the Application

Clear step-by-step instructions to run the **Algo Trading** dashboard (backend + web).

- **PowerShell (one script):** [Clear 5-step run](#clear-5-step-run-full-setup-with-db--redis) then [Option A](#option-a-one-command-windows-powershell) (`.\Start-All.ps1`).
- **VS Code:** [Run from VS Code (clear steps)](#run-from-vs-code-clear-steps) — open folder, Run Task → Start All, then open http://localhost:3000.

---

## Clear 5-step run (full setup with DB + Redis)

Do these steps **in order**. Use **PowerShell** in the project folder: `c:\Users\srini\Algo trade -cursor`.

---

### Step 1: Create and edit the `.env` file

**1.1 – Create `.env` from the example**

In PowerShell (project folder):

```powershell
Copy-Item .env.example .env
```

**1.2 – Open `.env` in Notepad**

- In File Explorer go to: `c:\Users\srini\Algo trade -cursor`
- If you don’t see `.env`, turn on **View → Show → Hidden items**
- Right‑click **.env** → **Open with** → **Notepad**

**1.3 – Set these three values (use Ctrl+F to find each line)**

| Find this line | Replace the whole value with this (copy exactly) |
|----------------|----------------------------------------------------|
| `DATABASE_URL=...` | `DATABASE_URL=postgresql://capitalguard:capitalguard@localhost:5432/capitalguard` |
| `REDIS_URL=...`   | `REDIS_URL=redis://localhost:6379/0`               |
| `JWT_SECRET=...`  | `JWT_SECRET=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6` |

- **DATABASE_URL** — used when the app connects to PostgreSQL (Docker in Step 2).
- **REDIS_URL** — used when the app connects to Redis (Docker in Step 2).
- **JWT_SECRET** — a long random string; the value above is only an example (use your own in production).

**1.4 – Save and close:** File → Save (Ctrl+S), then close Notepad.

---

### Step 2: Start the database and Redis (Docker)

**2.1 – Start Docker Desktop**

- Open **Docker Desktop** from the Start menu and wait until it says it’s running.

**2.2 – In PowerShell (project folder), run:**

```powershell
docker-compose up -d db redis
```

- First time may take a few minutes (downloads images). When done you should see “done” or container names.

**2.3 – Check they are running:**

```powershell
docker-compose ps
```

You should see two rows (e.g. `db` and `redis`) with status **Up**. If yes, continue to Step 3.

---

### Step 3: Run the backend

**3.1 – Open a new PowerShell window** (keep it open for the rest of the run).

**3.2 – Go to the backend folder and activate the virtual environment:**

```powershell
cd "c:\Users\srini\Algo trade -cursor\backend"
.\.venv\Scripts\Activate.ps1
```

You should see `(.venv)` at the start of the line.

**3.3 – If you have never run the backend on this machine, install dependencies (once):**

```powershell
pip install -e ".[dev]"
```

**3.4 – Start the backend server:**

```powershell
$env:PYTHONPATH = (Get-Location).Path
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- When you see **“Uvicorn running on http://0.0.0.0:8000”**, the backend is running.
- **Leave this window open.** Closing it stops the backend.

**3.5 – Quick check:** In the browser open **http://localhost:8000/health** — you should see something like `{"status":"ok",...}`.

---

### Step 4: Run the web app

**4.1 – Open another new PowerShell window** (so you have: one for backend, one for web).

**4.2 – Go to the web folder:**

```powershell
cd "c:\Users\srini\Algo trade -cursor\web"
```

**4.3 – If you have never run the web app on this machine, install dependencies (once):**

```powershell
npm install
```

**4.4 – Start the web app:**

```powershell
npm run dev
```

- When you see **“Ready”** or **“localhost:3000”**, the web app is running.
- **Leave this window open.** Closing it stops the web app.

---

### Step 5: Open the app in the browser

- In your browser go to: **http://localhost:3000**
- You should see the Algo Trading dashboard.

**Summary:** You now have:

- **Terminal 1:** Backend (uvicorn) — don’t close.
- **Terminal 2:** Web (`npm run dev`) — don’t close.
- **Browser:** http://localhost:3000

To stop: close the two terminal windows or press **Ctrl+C** in each.

---

### Optional: Mobile app

Only if you need the React Native mobile client:

```powershell
cd "c:\Users\srini\Algo trade -cursor\mobile"
npm install
npx react-native start
```

Keep that terminal open. Use another terminal or your IDE to run the app on a device/emulator (e.g. `npx react-native run-android`).

---

## Run from VS Code (clear steps)

Use this when you want to start the **backend** and **web app** from inside VS Code. You still need the `.env` file and (if you use DB/Redis) Docker running.

---

### Before you start in VS Code

1. **Do Step 1 and Step 2** from the [Clear 5-step run](#clear-5-step-run-full-setup-with-db--redis) above:
   - Create `.env` and set `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET`.
   - Start Docker and run: `docker-compose up -d db redis`.

2. **First-time only:** Create the backend virtual environment and install dependencies (in PowerShell or VS Code terminal):
   - `cd backend` → `python -m venv .venv` → `.\.venv\Scripts\Activate.ps1` → `pip install -e ".[dev]"`
   - `cd web` → `npm install`

---

### Step 1: Open the project in VS Code

1. Open **VS Code** (Visual Studio Code).
2. **File → Open Folder** (or **Ctrl+K Ctrl+O**).
3. Select the **project root folder**: `c:\Users\srini\Algo trade -cursor`
4. Click **Select Folder**. The left sidebar should show folders like `backend`, `web`, `docs`.

---

### Step 2: Run both backend and web with one task

1. Press **Ctrl+Shift+P** (or **Cmd+Shift+P** on Mac) to open the Command Palette.
2. Type **Run Task** and press **Enter**.
3. From the list, choose **Start All**.
4. VS Code will:
   - Start the **backend** in a terminal (you’ll see “Uvicorn running on…”).
   - Then start the **web app** in a second terminal (you’ll see “Ready” or “localhost:3000”).

---

### Step 3: Open the app in your browser

- In your browser go to: **http://localhost:3000**
- You should see the Algo Trading dashboard.

---

### Step 4: Stop the servers when you’re done

1. In VS Code, open the **Terminal** panel (View → Terminal, or **Ctrl+`**).
2. You’ll see two terminals (Backend and Web). Click the one you want to stop.
3. Press **Ctrl+C** in that terminal. Repeat for the other terminal.

---

### VS Code tasks available

| Task | What it does |
|------|----------------------|
| **Start All** | Starts the backend, then the web app (use this to run the full app). |
| **Start Backend** | Starts only the FastAPI backend (port 8000). |
| **Start Web** | Starts only the Next.js web app (port 3000). |

To run a single task: **Ctrl+Shift+P** → **Run Task** → choose **Start Backend** or **Start Web**.

---

### If “Start All” or “Start Backend” fails

- **“python.exe not found” or “.venv not found”**  
  Create the backend venv from the project folder in a terminal:
  ```powershell
  cd backend
  python -m venv .venv
  .\.venv\Scripts\Activate.ps1
  pip install -e ".[dev]"
  ```
  Then try **Run Task → Start All** again.

- **Port 8000 or 3000 already in use**  
  Another app is using that port. Close the other terminal or app that’s running the backend/web, or stop the task that’s using the port.

---

## Prerequisites (one-time)

Install these if you don’t have them:

| Software   | Version | Check command   |
|-----------|---------|------------------|
| **Python** | 3.11+  | `python --version` |
| **Node.js** | 18+ LTS | `node --version`  |

- Python: https://www.python.org/downloads/ (tick **Add Python to PATH**)
- Node.js: https://nodejs.org/ (LTS)

**Optional:** Docker Desktop — only if you use PostgreSQL/Redis (see [docs/INSTALL_AND_RUN.md](docs/INSTALL_AND_RUN.md)).

---

## First-time setup (once per machine)

### 1. Open a terminal in the project folder

- **Path:** `c:\Users\srini\Algo trade -cursor`
- In File Explorer: go to that folder → click the address bar → type `powershell` → Enter.

### 2. Backend: create virtual environment and install dependencies

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
cd ..
```

(You should see `(.venv)` in the prompt after activate.)

### 3. Web: install dependencies

```powershell
cd web
npm install
cd ..
```

### 4. Environment file (optional for minimal run)

For Upstox and DB/Redis you need a `.env` file. Minimal run (no Upstox) can work without it. To create:

```powershell
Copy-Item .env.example .env
```

Then edit `.env` in Notepad/VS Code and set at least `JWT_SECRET` (and `DATABASE_URL`, `REDIS_URL` if you use Docker). See [docs/INSTALL_AND_RUN.md](docs/INSTALL_AND_RUN.md) for details.

---

## How to run (choose one)

### Option A: One command (Windows PowerShell)

From the **project root** in PowerShell:

```powershell
.\Start-All.ps1
```

- Starts the **backend** in a new window (port 8000).
- Starts the **web app** in another new window (port 3000).
- Opens **http://localhost:3000** in your browser.

**Keep both terminal windows open.** Close them to stop the servers.

---

### Option B: Run from VS Code

**→ See [Run from VS Code (clear steps)](#run-from-vs-code-clear-steps)** above for full instructions.

Short version: **File → Open Folder** (project root) → **Ctrl+Shift+P** → **Run Task** → **Start All** → open **http://localhost:3000**. Stop with **Ctrl+C** in each terminal.

---

### Option C: Manual (two terminals)

**Terminal 1 – Backend**

```powershell
cd "c:\Users\srini\Algo trade -cursor\backend"
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH = (Get-Location).Path
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Leave this window open.

**Terminal 2 – Web**

```powershell
cd "c:\Users\srini\Algo trade -cursor\web"
npm run dev
```

Leave this window open.

**Browser:** open **http://localhost:3000**.

---

## What runs where

| Service   | Port | URL                    |
|----------|------|------------------------|
| Backend  | 8000 | http://localhost:8000  |
| Web app  | 3000 | http://localhost:3000  |
| API docs | 8000 | http://localhost:8000/docs |
| Health   | 8000 | http://localhost:8000/health |

---

## Stopping the app

- **If you used Start-All.ps1:** Close the two PowerShell windows that are running the backend and the web app.
- **If you used VS Code:** In the Terminal panel, click each server terminal and press **Ctrl+C**.
- **If you ran manually:** In each terminal press **Ctrl+C**.

---

## Troubleshooting

### These errors mean the backend is not running or dropped

| Error | Meaning | What to do |
|-------|--------|------------|
| **`ECONNREFUSED 127.0.0.1:8000`** | Nothing is listening on port 8000. The **backend is not running**. | **Start the backend first**, then the web app. Use **Start-All.ps1** or **VS Code → Run Task → Start All**. Keep the **backend terminal/window open**; closing it stops the API. |
| **`socket hang up` / `ECONNRESET`** (e.g. on `/api/v1/portfolio/holdings/opportunities`) | The backend was reached but the connection closed (backend crashed, restarted, or timed out). | 1. **Restart the backend** (close its terminal, start it again from `backend` with `uvicorn ...` or Run Task **Start Backend**). 2. Make sure you **don’t close the backend terminal**. 3. If it keeps happening, check the **backend terminal** for Python errors and fix or report them. |

**Rule:** Always start the **backend** (port 8000) **before** or together with the web app, and **keep the backend running** while you use the dashboard.

---

### Other issues

| Problem | What to do |
|--------|------------|
| **“Backend unreachable”** | Backend is not running or not on port 8000. Start the backend (Option A, B, or C) and keep that window open. |
| **Port 8000 or 3000 already in use** | Stop the process using that port, or close the other terminal that’s running the backend/web. |
| **Script cannot be loaded / execution policy** | In PowerShell run: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` then try `.\Start-All.ps1` again. |
| **`python` or `node` not recognized** | Install Python/Node and **restart** the terminal. Ensure “Add to PATH” was checked. |
| **Upstox connect fails** | Add `UPSTOX_CLIENT_ID` and `UPSTOX_CLIENT_SECRET` to `.env` in the project root and restart the backend. |

More detail: [docs/INSTALL_AND_RUN.md](docs/INSTALL_AND_RUN.md).
