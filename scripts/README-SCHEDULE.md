# Schedule scripts (weekday market hours)

Use these with a VPS so the backend **starts before 9:15 AM** and **stops after 3:30 PM IST** on **Mon–Fri** only.

- `start-backend.sh` – start the FastAPI backend (run at 9:00 AM IST weekdays).
- `stop-backend.sh` – stop the backend (run at 3:35 PM IST weekdays).

## Setup on Linux VPS

1. Clone the repo and install backend deps (see main README / docs/INSTALL_AND_RUN.md).
2. Create `.env` in the **project root** with Upstox and other settings.
3. Make scripts executable:
   ```bash
   chmod +x scripts/start-backend.sh scripts/stop-backend.sh
   ```
4. Add crontab (server in IST):
   ```bash
   crontab -e
   ```
   Add:
   ```
   0 9 * * 1-5 /path/to/Algo-trade-cursor/scripts/start-backend.sh
   35 15 * * 1-5 /path/to/Algo-trade-cursor/scripts/stop-backend.sh
   ```
   If the server uses **UTC**, use:
   ```
   30 3 * * 1-5 /path/to/.../start-backend.sh
   5 10 * * 1-5 /path/to/.../stop-backend.sh
   ```

See **docs/CLOUD_AND_SCHEDULE.md** for full cloud deployment and Render/Railway keep-alive options.
