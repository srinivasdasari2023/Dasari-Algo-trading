#!/bin/bash
# Start backend for market hours. Run from cron on weekdays at 9:00 AM IST.
# Usage: run from project root or set ALGO_TRADE_ROOT to project root.

set -e
ROOT="${ALGO_TRADE_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
cd "$ROOT/backend"
LOG="${LOG:-/tmp/algo-api.log}"
PID_FILE="${PID_FILE:-/tmp/algo-api.pid}"

if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  echo "Backend already running (PID $(cat "$PID_FILE"))"
  exit 0
fi

if [ -d ".venv" ]; then
  source .venv/bin/activate
elif [ -n "$VIRTUAL_ENV" ]; then
  : # already in venv
else
  echo "Warning: no .venv found in $ROOT/backend; using system python"
fi

[ -f "$ROOT/.env" ] && export $(grep -v '^#' "$ROOT/.env" | xargs)
[ -f "$ROOT/backend/.env" ] && export $(grep -v '^#' "$ROOT/backend/.env" | xargs)
nohup uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" >> "$LOG" 2>&1 &
echo $! > "$PID_FILE"
echo "Backend started (PID $(cat "$PID_FILE")), log: $LOG"
