"""Trade logging and daily email reports.

Writes one CSV file per day under backend/app/logs/trades:
  trades-YYYY-MM-DD.csv

Each row records either an OPEN or CLOSE event for a position, including
expected SL/target at entry and what actually happened at exit.
"""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone, timedelta
from pathlib import Path
from typing import Literal, Optional

from app.services.email_service import send_mail


IST = timezone(timedelta(hours=5, minutes=30))


@dataclass
class TradeEvent:
    event_type: Literal["OPEN", "CLOSE"]
    at: datetime
    position_id: str
    symbol: str
    side: Literal["BUY", "SELL"]
    quantity: int
    signal_id: str | None = None
    signal_type: str | None = None
    entry_index: float | None = None
    expected_sl_index: float | None = None
    expected_target_index: float | None = None
    entry_premium: float | None = None
    sl_premium: float | None = None
    target_premium: float | None = None
    exit_index: float | None = None
    exit_premium: float | None = None
    exit_reason: str | None = None
    pnl_rupees: float | None = None
    pnl_R: float | None = None


def _logs_dir() -> Path:
    base = Path(__file__).resolve().parent.parent / "logs" / "trades"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _file_for(d: date) -> Path:
    return _logs_dir() / f"trades-{d.isoformat()}.csv"


def _ensure_header(path: Path, fieldnames: list[str]) -> None:
    if path.exists():
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()


def _write_event(ev: TradeEvent) -> None:
    d = ev.at.date()
    path = _file_for(d)
    data = asdict(ev)
    # Flatten datetime to ISO string
    data["at"] = ev.at.isoformat()
    fieldnames = list(data.keys())
    _ensure_header(path, fieldnames)
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writerow(data)


def log_trade_open(
    *,
    position_id: str,
    symbol: str,
    side: Literal["BUY", "SELL"],
    quantity: int,
    signal_id: Optional[str],
    signal_type: Optional[str] = None,
    entry_index: Optional[float] = None,
    expected_sl_index: Optional[float] = None,
    expected_target_index: Optional[float] = None,
    entry_premium: Optional[float] = None,
    sl_premium: Optional[float] = None,
    target_premium: Optional[float] = None,
) -> None:
    """Log when a trade is opened."""
    ev = TradeEvent(
        event_type="OPEN",
        at=datetime.now(IST),
        position_id=position_id,
        symbol=symbol,
        side=side,
        quantity=quantity,
        signal_id=signal_id,
        signal_type=signal_type,
        entry_index=entry_index,
        expected_sl_index=expected_sl_index,
        expected_target_index=expected_target_index,
        entry_premium=entry_premium,
        sl_premium=sl_premium,
        target_premium=target_premium,
    )
    _write_event(ev)


def log_trade_close(
    *,
    position_id: str,
    symbol: str,
    side: Literal["BUY", "SELL"],
    quantity: int,
    exit_reason: str,
    exit_index: Optional[float] = None,
    exit_premium: Optional[float] = None,
    pnl_rupees: Optional[float] = None,
    pnl_R: Optional[float] = None,
) -> None:
    """Log when a trade is closed (SL hit, target hit, manual, etc.)."""
    ev = TradeEvent(
        event_type="CLOSE",
        at=datetime.now(IST),
        position_id=position_id,
        symbol=symbol,
        side=side,
        quantity=quantity,
        exit_reason=exit_reason,
        exit_index=exit_index,
        exit_premium=exit_premium,
        pnl_rupees=pnl_rupees,
        pnl_R=pnl_R,
    )
    _write_event(ev)


def send_daily_trade_report_email(report_date: Optional[date] = None) -> bool:
    """Read the day's CSV and send a consolidated email with all trades.

    This does not try to be perfect P&L accounting. It simply summarizes
    what was logged (OPEN/CLOSE events) and attaches a per-trade table.
    """
    report_date = report_date or datetime.now(IST).date()
    path = _file_for(report_date)
    if not path.exists():
        return send_mail(
            "Daily trade report",
            f"No trades recorded on {report_date.isoformat()} (file {path.name} does not exist).",
        )

    rows: list[dict[str, str]] = []
    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    total_trades = sum(1 for r in rows if r.get("event_type") == "OPEN")
    closed_events = [r for r in rows if r.get("event_type") == "CLOSE"]

    # Basic closed trade stats based on pnl_R if present
    wins = [r for r in closed_events if r.get("pnl_R") not in (None, "", "0") and float(r["pnl_R"]) > 0]
    losses = [r for r in closed_events if r.get("pnl_R") not in (None, "", "0") and float(r["pnl_R"]) < 0]
    win_rate = (len(wins) / len(wins + losses) * 100.0) if (wins or losses) else 0.0

    body_lines = [
        f"Daily trade report for {report_date.isoformat()}",
        "",
        f"Total trades opened: {total_trades}",
        f"Closed trades: {len(closed_events)}",
        f"Win rate (by R where available): {win_rate:.1f}%",
        "",
        "Per-event log (OPEN and CLOSE rows):",
        "",
    ]

    # Append a simple table-style text
    if rows:
        headers = list(rows[0].keys())
        body_lines.append(",".join(headers))
        for r in rows:
            body_lines.append(",".join(str(r.get(h, "")) for h in headers))
    else:
        body_lines.append("No rows in log file.")

    body = "\n".join(body_lines)
    return send_mail("Daily trade report", body)

