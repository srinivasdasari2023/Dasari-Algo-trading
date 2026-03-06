#!/bin/bash
# Stop backend after market hours. Run from cron on weekdays at 3:35 PM IST.

PID_FILE="${PID_FILE:-/tmp/algo-api.pid}"

if [ ! -f "$PID_FILE" ]; then
  echo "No PID file; backend may already be stopped"
  exit 0
fi

PID=$(cat "$PID_FILE")
if kill -0 "$PID" 2>/dev/null; then
  kill "$PID" 2>/dev/null || kill -9 "$PID" 2>/dev/null
  echo "Backend stopped (PID $PID)"
else
  echo "Process $PID not running"
fi
rm -f "$PID_FILE"
