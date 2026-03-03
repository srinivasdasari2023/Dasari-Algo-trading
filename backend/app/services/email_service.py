"""Send email notifications (Gmail) for login, signals, orders, SL/TSL. Uses MAIL_* from config."""
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

_logged_disabled_once = False


def _from_email() -> str:
    return (getattr(settings, "MAIL_FROM", "") or getattr(settings, "GMAIL_USER", "") or "").strip()


def _to_email() -> str:
    return (getattr(settings, "MAIL_TO", "") or getattr(settings, "GMAIL_TO", "") or "").strip()


def _password() -> str:
    return (
        getattr(settings, "MAIL_APP_PASSWORD", "")
        or getattr(settings, "MAIL_PASSWORD", "")
        or getattr(settings, "PASSWORDKEY", "")
        or ""
    ).strip()


def _enabled() -> bool:
    from_email = _from_email()
    to_email = _to_email()
    pwd = _password()
    explicit = getattr(settings, "MAIL_ENABLED", False)
    ok = bool(from_email and to_email and pwd)
    return (explicit or ok) and ok


def log_email_status() -> None:
    """Call once at app startup to log whether email notifications are enabled."""
    if _enabled():
        logger.info("Email notifications enabled -> %s", _to_email())
    else:
        _log_disabled_reason()


def _log_disabled_reason() -> None:
    """Log at INFO once why email is disabled so user can fix .env."""
    global _logged_disabled_once
    if _enabled() or _logged_disabled_once:
        return
    _logged_disabled_once = True
    missing = []
    if not _from_email():
        missing.append("MAIL_FROM or GMAIL_USER")
    if not _to_email():
        missing.append("MAIL_TO or GMAIL_TO")
    if not _password():
        missing.append("MAIL_APP_PASSWORD or MAIL_PASSWORD or PASSWORDKEY")
    logger.info(
        "Email notifications disabled: missing %s. Set in .env and restart backend to get Upstox/trade emails.",
        ", ".join(missing),
    )


def send_mail(subject: str, body_plain: str, body_html: Optional[str] = None) -> bool:
    """Send one email. Returns True if sent, False if disabled or error."""
    if not _enabled():
        _log_disabled_reason()
        return False

    from_addr = _from_email()
    to_addr = _to_email()
    pwd = _password()

    try:
        msg = MIMEMultipart("alternative")
        app_name = getattr(settings, "APP_NAME", "Dasari's Algo Trading terminal")
        msg["Subject"] = f"[{app_name}] {subject}"
        msg["From"] = from_addr
        msg["To"] = to_addr
        msg.attach(MIMEText(body_plain, "plain", "utf-8"))
        if body_html:
            msg.attach(MIMEText(body_html, "html", "utf-8"))

        # Prefer 587 STARTTLS (works on more networks); fallback to 465 SSL
        try:
            with smtplib.SMTP("smtp.gmail.com", 587, timeout=15) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(from_addr, pwd)
                server.sendmail(from_addr, [to_addr], msg.as_string())
        except (smtplib.SMTPNotSupportedError, OSError) as e1:
            logger.debug("SMTP 587 failed (%s), trying 465", e1)
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as server:
                server.login(from_addr, pwd)
                server.sendmail(from_addr, [to_addr], msg.as_string())

        logger.info("Email sent: %s -> %s", subject, to_addr)
        return True
    except smtplib.SMTPAuthenticationError as e:
        logger.warning(
            "Email failed (auth): %s. Use Gmail App Password: https://myaccount.google.com/apppasswords",
            e,
        )
        return False
    except Exception as e:
        logger.warning("Email failed: %s", e, exc_info=True)
        return False


def _app_name() -> str:
    return getattr(settings, "APP_NAME", "Dasari's Algo Trading terminal")


def notify_connection(connected: bool, message: str = "") -> bool:
    """Notify on Upstox connect or disconnect."""
    name = _app_name()
    if connected:
        return send_mail(
            "Upstox connected",
            f"{name}: Upstox login/connection successful.\n\n{message}".strip(),
        )
    return send_mail(
        "Upstox disconnected",
        f"{name}: Upstox disconnected.\n\n{message}".strip(),
    )


def notify_signal(symbol: str, status: str, reason: str = "") -> bool:
    """Notify on trading signal (BUY/SELL/NO_SIGNAL)."""
    return send_mail(
        f"Signal {status} ({symbol})",
        f"{_app_name()} signal:\nSymbol: {symbol}\nStatus: {status}\nReason: {reason or '-'}",
    )


def notify_order_placed(symbol: str, side: str, quantity: int, order_id: str, sl_trigger: Optional[float] = None) -> bool:
    """Notify when an order is placed."""
    lines = [f"Order placed: {side} {quantity} {symbol}", f"Order ID: {order_id}"]
    if sl_trigger is not None:
        lines.append(f"SL trigger: {sl_trigger}")
    return send_mail("Order placed", "\n".join(lines))


def notify_sl_updated(symbol: str, position_id: str, old_sl: Optional[float], new_sl: float, reason: str = "Trailing SL") -> bool:
    """Notify when stop loss is updated (e.g. trailing)."""
    body = (
        f"{_app_name()}: Stop loss updated.\n"
        f"Symbol: {symbol}\nPosition: {position_id}\n"
        f"Previous SL: {old_sl}\nNew SL: {new_sl}\nReason: {reason}"
    )
    return send_mail("Stop loss updated (trailing)", body)


def notify_sl_hit(symbol: str, position_id: str, sl_price: float) -> bool:
    """Notify when SL is hit (position closed)."""
    return send_mail(
        "Stop loss hit",
        f"{_app_name()}: Stop loss hit.\nSymbol: {symbol}\nPosition: {position_id}\nSL price: {sl_price}",
    )
