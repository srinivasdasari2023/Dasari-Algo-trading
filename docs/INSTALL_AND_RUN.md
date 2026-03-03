# Install and Run – CapitalGuard Algo Trader

Step-by-step instructions to install and run the application locally.

---

# First time? Start here (step-by-step)

This section is for beginners. It tells you **where** to do each step and **what** to type or click. Do the steps in order.

You will use:
- **File Explorer** – to open your project folder and files  
- **Terminal (PowerShell)** – a window where you type commands  
- **Browser** – to open the app (Chrome, Edge, etc.)  
- **Docker Desktop** – to run the database and Redis in the background  

---

## Step 0: Install the required software (one-time)

Do this once before anything else.

| # | What to install | Where to get it | What to do after installing |
|---|-----------------|-----------------|------------------------------|
| 1 | **Python 3.11 or newer** | https://www.python.org/downloads/ | Download "Windows installer (64-bit)". Run it. **Check the box "Add Python to PATH"** at the bottom, then click "Install Now". Close and reopen any terminal after this. |
| 2 | **Node.js 18 or newer (LTS)** | https://nodejs.org/ | Download the LTS version. Run the installer with default options. Close and reopen any terminal after this. |
| 3 | **Docker Desktop** | https://www.docker.com/products/docker-desktop/ | Download for Windows, install, and **start Docker Desktop**. Wait until it says "Docker Desktop is running" (whale icon in system tray). |

**Check that they work:**  
Open **PowerShell** (press Windows key, type `PowerShell`, press Enter). Type each line below and press Enter. You should see a version number, not "not recognized".

```powershell
python --version
node --version
docker --version
```

If any command says "not recognized", install that item again and make sure to restart PowerShell.

---

## Step 1: Open your project folder

**Where is the project?**  
Your project is in: `c:\Users\srini\Algo trade -cursor`

**What to do:**

1. Press **Windows + E** to open File Explorer.
2. In the address bar at the top, type: `c:\Users\srini\Algo trade -cursor` and press **Enter**.
3. You should see folders like `backend`, `web`, `docs` and files like `README.md`, `.env.example`. If you see them, you are in the right place.

**Open a terminal in this folder:**

1. In the same File Explorer window, **click once in the address bar** (where the path is shown).
2. Type: `powershell` and press **Enter**.
3. A blue (or black) window opens: this is **PowerShell**. It is already "in" your project folder. You will type commands here.

**You should see something like:**  
`PS C:\Users\srini\Algo trade -cursor>`

That `>` is the prompt. Everything you type goes after it.

---

## Step 2: Create and edit the `.env` file

**.env** is a config file the app needs. We will copy a template and then edit it.

**2.1 – Create the file**

In the **same PowerShell window** (project folder), type this **exactly** and press **Enter**:

```powershell
Copy-Item .env.example .env
```

You should see no error; the line just goes to the next prompt. That means a new file named `.env` was created.

**2.2 – Open `.env` in Notepad**

1. In **File Explorer**, go to `c:\Users\srini\Algo trade -cursor` again (if needed).
2. You might not see `.env` because it starts with a dot. In the top menu, click **View** → check **"Hidden items"** and **"File name extensions"** so you can see `.env`.
3. **Right-click** the file `.env` → **Open with** → **Notepad** (or any text editor).

**2.3 – Set the required values**

In Notepad you will see many lines. Find and set these (you can use Ctrl+F to search):

- Find the line that has **DATABASE_URL**. Replace the whole value so that line is **exactly**:
  ```
  DATABASE_URL=postgresql://capitalguard:capitalguard@localhost:5432/capitalguard
  ```
- Find **REDIS_URL**. Set it to:
  ```
  REDIS_URL=redis://localhost:6379/0
  ```
- Find **JWT_SECRET**. Replace the value with any long random string (at least 32 letters/numbers). For example you can use:
  ```
  JWT_SECRET=mysecretkey123456789012345678901234
  ```
  (For real use later, use a longer random string.)

**Save the file:** File → Save (or Ctrl+S). Then close Notepad.

---

## Step 3: Start the database and Redis (Docker)

The app needs a database (PostgreSQL) and a cache (Redis). We run them with Docker.

**3.1 – Start Docker Desktop**

1. Open **Docker Desktop** from the Start menu.
2. Wait until the whale icon in the system tray (bottom-right) shows Docker is running. It can take a minute the first time.

**3.2 – Run the database and Redis**

1. Go back to the **PowerShell** window where you ran the copy command (Step 2.1).
2. Make sure you are still in the project folder (you should see `Algo trade -cursor` in the path).
3. Type this and press **Enter**:

```powershell
docker-compose up -d db redis
```

**What you might see:**  
Docker may download some images the first time (this can take a few minutes). At the end you should see lines like "Creating ... done" or container names and "Started".

**Check they are running:**  
Type:

```powershell
docker-compose ps
```

You should see two rows: one for `db` (or postgres) and one for `redis`, both with status **Up**. If you see that, continue. If you see errors, make sure Docker Desktop is running and try `docker-compose up -d db redis` again.

---

## Step 4: Run the backend (API) server

The **backend** is the Python server that does the trading logic. We need a **new** terminal for it so it can keep running.

**4.1 – Open a second PowerShell in the project folder**

1. Open **File Explorer** again and go to `c:\Users\srini\Algo trade -cursor`.
2. In the address bar, type `powershell` and press **Enter**. A **new** PowerShell window opens.

**4.2 – Go into the backend folder**

Type and press **Enter**:

```powershell
cd backend
```

The prompt should now end with `\backend>`.

**4.3 – Create a Python virtual environment (one-time)**

Type and press **Enter**:

```powershell
python -m venv .venv
```

Nothing exciting will show; that’s OK.

**4.4 – Turn on the virtual environment**

Type and press **Enter**:

```powershell
.\.venv\Scripts\Activate.ps1
```

After this, the start of your line should show `(.venv)`, for example:  
`(.venv) PS C:\...\backend>`

**4.5 – Install Python packages**

Type and press **Enter**:

```powershell
pip install -e ".[dev]"
```

Wait until it finishes (you’ll see "Successfully installed ..." or similar).

**4.6 – Start the API server**

Type and press **Enter**:

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**What you should see:**  
Lines like "Uvicorn running on http://0.0.0.0:8000" and "Application startup complete". **Leave this window open.** The backend is now running. If you close the window, the server stops.

**Quick check:**  
Open your **browser** and go to: **http://localhost:8000/health**  
You should see something like: `{"status":"ok","service":"capitalguard-api"}`. That means the backend is working.

**Important:** You must run uvicorn from inside the **backend** folder. If you run it from the project root (`Algo trade -cursor`), Python may load a different project’s `app` and the server will crash or behave wrongly. Always `cd backend` first.

**Alternative (from project root):**  
From the project root you can start the backend with:  
`.\backend\run.ps1`  
This script changes into `backend`, activates the venv, and runs uvicorn.

---

## Step 5: Run the web app (frontend)

The **web app** is the dashboard you see in the browser. We run it in **another** terminal so it can stay on.

**5.1 – Open a third PowerShell in the project folder**

1. File Explorer → go to `c:\Users\srini\Algo trade -cursor`.
2. In the address bar type `powershell` and press **Enter**. You now have a **third** window.

**5.2 – Go into the web folder**

Type and press **Enter**:

```powershell
cd web
```

The prompt should end with `\web>`.

**5.3 – Install web dependencies (first time only)**

Type and press **Enter**:

```powershell
npm install
```

Wait until it finishes (can take 1–2 minutes). You’ll see a lot of text; at the end there should be no red errors.

**5.4 – Start the web app**

Type and press **Enter**:

```powershell
npm run dev
```

**What you should see:**  
Lines like "Ready on http://localhost:3000" or "Local: http://localhost:3000". **Leave this window open** so the web app keeps running.

---

## Step 6: Open the app in your browser

1. Open **Chrome** or **Edge** (or any browser).
2. In the address bar type: **http://localhost:3000** and press **Enter**.

You should see the **CapitalGuard Algo Trader** dashboard (title and placeholder sections for Market Context, Signal Panel, etc.). That means both the backend and the web app are running correctly.

**Summary of what’s running:**

| What        | Where it runs     | URL                    |
|------------|-------------------|------------------------|
| Database   | Docker            | (no browser; internal) |
| Redis      | Docker            | (no browser; internal) |
| Backend API| PowerShell #2     | http://localhost:8000  |
| Web app    | PowerShell #3     | http://localhost:3000  |

- **API docs:** http://localhost:8000/docs  
- **Health check:** http://localhost:8000/health  

When you are done, you can close the two PowerShell windows where `uvicorn` and `npm run dev` are running. To run the app again later, repeat from **Step 3** (Docker), then **Step 4** (backend), then **Step 5** (web), then **Step 6** (browser).

---

## Prerequisites (reference)

Install these before starting:

| Tool | Version | Purpose |
|------|---------|---------|
| **Python** | 3.11+ | Backend API |
| **Node.js** | 18+ (LTS) | Web app (Next.js) |
| **Docker Desktop** | Latest | PostgreSQL + Redis (and optional full stack) |
| **Git** | Any | Clone repo |

- **Windows:** Install [Python](https://www.python.org/downloads/), [Node.js](https://nodejs.org/), and [Docker Desktop](https://www.docker.com/products/docker-desktop/). Use PowerShell or Command Prompt.
- **macOS/Linux:** `python3.11`, `node`, `docker` / `docker compose` available in PATH.

---

## 1. Get the code

```bash
cd "c:\Users\srini\Algo trade -cursor"
# If from git: git clone <repo-url> "Algo trade -cursor" && cd "Algo trade -cursor"
```

---

## 2. Environment file

Create your local environment file (never commit this file):

```bash
copy .env.example .env
```

**Windows (PowerShell):**
```powershell
Copy-Item .env.example .env
```

Then **edit `.env`** in a text editor (Notepad, VS Code, etc.). Below is what each variable means and exactly what to put in.

---

### What is the `.env` file?

The `.env` file holds **configuration and secrets** for the app (database URL, Redis URL, API keys). The app reads these when it starts. **Do not commit `.env` to git**—it is in `.gitignore` and should stay on your machine only.

---

### Variables to set (detailed)

#### 1. DATABASE_URL

- **What it is:** The connection string the backend uses to talk to **PostgreSQL** (where trades, signals, and audit logs are stored).
- **When to use this value:** You are running PostgreSQL via Docker (Step 3 in this guide). The `docker-compose.yml` creates a database with a fixed username, password, and database name.
- **What to put in `.env`:**

  ```
  DATABASE_URL=postgresql://capitalguard:capitalguard@localhost:5432/capitalguard
  ```

- **Meaning of the parts:**
  - `postgresql://` – protocol
  - `capitalguard` (first) – **username** to log in to PostgreSQL
  - `capitalguard` (second) – **password**
  - `@localhost:5432` – **host** (your machine) and **port** (5432 is default for Postgres)
  - `/capitalguard` – **database name**

If you use a different Postgres (e.g. cloud or another Docker setup), change this string to match (user, password, host, port, database name).

---

#### 2. REDIS_URL

- **What it is:** The connection string the backend uses to talk to **Redis** (used for live state, locks, and caching).
- **When to use this value:** You are running Redis via Docker (Step 3). The compose file exposes Redis on your machine’s port 6379.
- **What to put in `.env`:**

  ```
  REDIS_URL=redis://localhost:6379/0
  ```

- **Meaning of the parts:**
  - `redis://` – protocol
  - `localhost:6379` – **host** and **port** (6379 is default for Redis)
  - `/0` – **database number** (0 is the first logical database inside Redis; you can use 0 for local dev)

If Redis is elsewhere (e.g. cloud), use that host and port instead.

---

#### 3. JWT_SECRET

- **What it is:** A **secret key** used to sign and verify **JWT tokens** (the tokens the app uses to know which user is logged in). Anyone with this value can create valid tokens, so it must stay private.
- **What to do:** Replace the placeholder in `.env` with a **long, random string** (at least 32 characters). Do not use a simple word or a short password.
- **Example (do not use this exact value; generate your own):**

  ```
  JWT_SECRET=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6
  ```

- **How to generate one (optional):**
  - **PowerShell:** `[Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Maximum 256 }) -as [byte[]])`
  - **Python:** `python -c "import secrets; print(secrets.token_hex(32))"`
  - Or use any password generator that gives 32+ random characters.

---

#### 4. UPSTOX_CLIENT_ID and UPSTOX_CLIENT_SECRET

- **What they are:** Credentials for the **Upstox API** (broker). The app uses them to let users log in with Upstox (OAuth) and to fetch market data and place orders.
- **When you need them:** Optional for the **first run** (you can leave them empty to start the API and web app). You **need** them when you want to connect to Upstox (live or sandbox) for market data and trading.
- **Where to get them:**
  1. Go to [Upstox Developer](https://upstox.com/developer/) (or the Upstox API portal you use).
  2. Log in and create an **application** (or use an existing one).
  3. In the app details you will see **Client ID** and **Client Secret**. Copy them.
- **What to put in `.env`:**

  ```
  UPSTOX_CLIENT_ID=your_client_id_here
  UPSTOX_CLIENT_SECRET=your_client_secret_here
  ```

- **Security:** Never commit these to git or share them. Keep them only in `.env` on your machine (and in secure storage for production).

---

### Example `.env` (minimal for local run with Docker)

After editing, the **top part** of your `.env` might look like this (with your own `JWT_SECRET` and, when needed, real Upstox values):

```
# App
APP_ENV=development
LOG_LEVEL=INFO
API_PORT=8000

# Database (Docker Postgres from Step 3)
DATABASE_URL=postgresql://capitalguard:capitalguard@localhost:5432/capitalguard

# Redis (Docker Redis from Step 3)
REDIS_URL=redis://localhost:6379/0

# JWT – use your own long random string
JWT_SECRET=your-32-or-more-character-secret-here

# Upstox – leave empty at first; add when you connect to Upstox
UPSTOX_CLIENT_ID=
UPSTOX_CLIENT_SECRET=
```

Save the file and continue to **Step 3** (Start database and Redis).

---

## 3. Start database and Redis (Docker)

Open a terminal in the project root and run:

```bash
docker-compose up -d db redis
```

Check that both are running:

```bash
docker-compose ps
```

You should see `db` and `redis` with state “Up”. The API will use `localhost:5432` (PostgreSQL) and `localhost:6379` (Redis) with the URLs you set in `.env`.

---

## 4. Backend API

### 4.1 Create virtual environment (recommended)

**Windows:**
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS/Linux:**
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
```

### 4.2 Install dependencies and run

From the `backend` folder (with venv active):

```bash
pip install -e ".[dev]"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- API base URL: **http://localhost:8000**
- Health check: **http://localhost:8000/health**
- API docs (dev): **http://localhost:8000/docs**

Leave this terminal open while developing.

---

## 5. Web app (Next.js)

Open a **new** terminal. From the project root:

```bash
cd web
npm install
npm run dev
```

- Web app: **http://localhost:3000**

Leave this terminal open. The dashboard will load; market data and signals will work once the backend is connected to Upstox and the strategy is implemented.

---

## 6. Optional: run everything with Docker

To run API + DB + Redis in Docker (no local Python needed for API):

```bash
docker-compose up --build
```

- API: **http://localhost:8000**
- DB: `localhost:5432`, Redis: `localhost:6379` (from host).  
Create `.env` as in Step 2; `docker-compose` passes it to the API container.

Then run the web app locally (Step 5) so you can develop the UI with hot reload.

---

## 7. Optional: Mobile app (React Native)

Only if you need the mobile client:

```bash
cd mobile
npm install
npx react-native start
```

In another terminal:

- Android: `npx react-native run-android`
- iOS (macOS only): `npx react-native run-ios`

Requires Android Studio / Xcode and device or emulator.

---

## Quick reference

| What | Command | URL |
|------|---------|-----|
| DB + Redis | `docker-compose up -d db redis` | — |
| Backend | `cd backend` then `uvicorn app.main:app --reload ...` or from root `.\backend\run.ps1` | http://localhost:8000 |
| Web | `cd web && npm run dev` | http://localhost:3000 |
| Health | — | http://localhost:8000/health |
| API docs | — | http://localhost:8000/docs |

---

## Troubleshooting

- **“Connection refused” to PostgreSQL or Redis**  
  Ensure Docker containers are up: `docker-compose ps`. Use `DATABASE_URL` and `REDIS_URL` in `.env` as in Step 2.

- **Port 8000 or 3000 already in use**  
  Stop the process using that port or change `API_PORT` / Next.js port (e.g. `npm run dev -- -p 3001`).

- **Backend crashes with TypeError or wrong app (e.g. genaiversion01, OPENAI_API_KEY)**  
  You started uvicorn from the **project root** instead of the **backend** folder. Always run the backend from inside `backend`:  
  `cd backend` → then `.\\.venv\Scripts\Activate.ps1` → then `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`.  
  Or from project root run: `.\backend\run.ps1`.

- **“.venv not recognized” when in project root**  
  The virtual environment lives inside `backend`. Either `cd backend` first and then run `.\\.venv\Scripts\Activate.ps1`, or use `.\backend\run.ps1` from project root.

- **“Upstox API Key (Client ID) not configured” (503 on Connect Upstox)**  
  The backend reads `UPSTOX_CLIENT_ID` and `UPSTOX_CLIENT_SECRET` from `.env`. Put `.env` in the **project root** (`Algo trade -cursor\\.env`) with exactly:  
  `UPSTOX_CLIENT_ID=your_key` and `UPSTOX_CLIENT_SECRET=your_secret` (no quotes, no spaces around `=`). Then **restart** the backend (Ctrl+C, then start uvicorn again from **backend** folder).

- **Backend tests**  
  From `backend`: `pytest -v tests/`

- **Lint backend**  
  From `backend`: `ruff check app tests`
