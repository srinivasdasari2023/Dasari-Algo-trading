"""Auth and RBAC. Upstox OAuth + Access Token; Trader / Admin roles."""
import urllib.parse
from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
import httpx

from app.core.config import settings
from app.services.email_service import notify_connection, send_mail, _enabled as email_enabled

router = APIRouter()

# In-memory store for Upstox access token (use Redis/DB in production per user/session)
_upstox_token_store: dict[str, str] = {}


def get_upstox_token() -> str | None:
    """Return stored Upstox access token for use by market/order services. None if not connected."""
    return _upstox_token_store.get("default")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UpstoxTokenRequest(BaseModel):
    access_token: str


class UpstoxExchangeRequest(BaseModel):
    code: str


class UpstoxStatusResponse(BaseModel):
    connected: bool
    message: str | None = None


def _upstox_headers(access_token: str) -> dict[str, str]:
    return {"Accept": "application/json", "Authorization": f"Bearer {access_token}"}


@router.get("/upstox/login")
def upstox_login(state: str | None = None):
    """
    Redirects user to Upstox OAuth dialog.
    Uses API Key (Client ID) and Redirect URI from env. After login, Upstox redirects to /upstox/callback with code.
    """
    if not settings.UPSTOX_CLIENT_ID:
        raise HTTPException(status_code=503, detail="Upstox API Key (Client ID) not configured")
    params = {
        "response_type": "code",
        "client_id": settings.UPSTOX_CLIENT_ID,
        "redirect_uri": settings.UPSTOX_OAUTH_REDIRECT_URI,
    }
    if state:
        params["state"] = state
    url = f"{settings.UPSTOX_API_BASE_URL}/login/authorization/dialog?{urllib.parse.urlencode(params)}"
    return RedirectResponse(url=url, status_code=302)


@router.get("/upstox/callback")
async def upstox_callback(code: str | None = None, state: str | None = None):
    """
    Backend callback (if Upstox redirect_uri points to backend). Otherwise use POST /upstox/exchange from frontend.
    """
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")
    if not settings.UPSTOX_CLIENT_ID or not settings.UPSTOX_CLIENT_SECRET:
        raise HTTPException(status_code=503, detail="Upstox API Key or Secret not configured")

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{settings.UPSTOX_API_BASE_URL}/login/authorization/token",
            headers={"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"},
            data={
                "code": code,
                "client_id": settings.UPSTOX_CLIENT_ID,
                "client_secret": settings.UPSTOX_CLIENT_SECRET,
                "redirect_uri": settings.UPSTOX_OAUTH_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=400, detail=f"Upstox token exchange failed: {resp.text}")

    data = resp.json()
    access_token = data.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="No access_token in Upstox response")

    _upstox_token_store["default"] = access_token
    notify_connection(True, "OAuth callback login")
    frontend = settings.FRONTEND_URL.rstrip("/")
    return RedirectResponse(url=f"{frontend}/?upstox=connected", status_code=302)


@router.post("/upstox/exchange", response_model=UpstoxStatusResponse)
async def upstox_exchange(body: UpstoxExchangeRequest):
    """
    Exchange authorization code for access token. Use this when Upstox redirect_uri is the frontend
    (e.g. http://localhost:3000/auth/callback). Frontend receives ?code=..., calls this with the code.
    """
    code = (body.code or "").strip()
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code is required")
    if not settings.UPSTOX_CLIENT_ID or not settings.UPSTOX_CLIENT_SECRET:
        raise HTTPException(status_code=503, detail="Upstox API Key or Secret not configured")

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{settings.UPSTOX_API_BASE_URL}/login/authorization/token",
            headers={"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"},
            data={
                "code": code,
                "client_id": settings.UPSTOX_CLIENT_ID,
                "client_secret": settings.UPSTOX_CLIENT_SECRET,
                "redirect_uri": settings.UPSTOX_OAUTH_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )
    if resp.status_code != 200:
        try:
            err_body = resp.json()
            errors = err_body.get("errors") or []
            upstox_msg = err_body.get("error_description") or err_body.get("error")
            if not upstox_msg and errors:
                upstox_msg = errors[0].get("message") or errors[0].get("errorCode") or str(errors[0])
            if not upstox_msg:
                upstox_msg = resp.text or "Unknown error"
            if isinstance(upstox_msg, dict):
                upstox_msg = upstox_msg.get("message") or upstox_msg.get("errorCode") or str(upstox_msg)
        except Exception:
            err_body = {}
            upstox_msg = resp.text or "Unknown error"
        detail = (
            "Token exchange failed. Code may be expired or already used (use it once, then click Connect Upstox again for a new code). "
            f"Upstox: {upstox_msg}"
        )
        upstox_str = str(upstox_msg) + str(err_body)
        if "Invalid Auth code" in upstox_str or "UDAPI100057" in upstox_str:
            detail += (
                " Fix: In Upstox Developer Console, set Redirect URI to exactly: "
                f"{settings.UPSTOX_OAUTH_REDIRECT_URI} (no trailing slash). Or connect using Access Token on the dashboard."
            )
        raise HTTPException(status_code=400, detail=detail)

    data = resp.json()
    access_token = data.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="No access_token in Upstox response")

    _upstox_token_store["default"] = access_token
    notify_connection(True, "Code exchange successful")
    return UpstoxStatusResponse(connected=True, message="Connected successfully")


@router.post("/upstox/token", response_model=UpstoxStatusResponse)
async def upstox_set_token(body: UpstoxTokenRequest):
    """
    Manually set Upstox Access Token (e.g. pasted from user).
    Validates token by calling Upstox user profile; stores on success.
    """
    token = (body.access_token or "").strip()
    if not token:
        raise HTTPException(status_code=400, detail="Access token is required")

    async with httpx.AsyncClient() as client:
        profile_resp = await client.get(
            f"{settings.UPSTOX_API_BASE_URL}/user/profile",
            headers=_upstox_headers(token),
        )
    if profile_resp.status_code != 200:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired access token. Upstox returned an error.",
        )

    _upstox_token_store["default"] = token
    notify_connection(True, "Access token set and validated")
    return UpstoxStatusResponse(connected=True, message="Access token validated and saved")


@router.get("/redirect-uri")
def get_redirect_uri():
    """Return the redirect URI the backend uses. Set this exact value in Upstox Developer Console."""
    return {"redirect_uri": settings.UPSTOX_OAUTH_REDIRECT_URI}


@router.get("/upstox/status", response_model=UpstoxStatusResponse)
def upstox_status():
    """Returns whether Upstox is connected (we have a stored access token)."""
    connected = bool(_upstox_token_store.get("default"))
    return UpstoxStatusResponse(connected=connected)


@router.post("/upstox/disconnect", response_model=UpstoxStatusResponse)
def upstox_disconnect():
    """Clear stored Upstox token (disconnect)."""
    _upstox_token_store.pop("default", None)
    notify_connection(False, "User disconnected")
    return UpstoxStatusResponse(connected=False, message="Disconnected")


@router.get("/test-email")
def test_email():
    """Send a test email to verify MAIL_* config. Check your inbox (and spam)."""
    if not email_enabled():
        return {"ok": False, "message": "Email disabled. Set MAIL_FROM, MAIL_TO, and MAIL_APP_PASSWORD (or MAIL_PASSWORD or PASSWORDKEY) in .env"}
    app_name = getattr(settings, "APP_NAME", "Dasari's Algo Trading terminal")
    ok = send_mail(f"Test from {app_name}", "This is a test email. If you received this, notifications are working.")
    return {"ok": ok, "message": "Test email sent. Check your inbox and spam folder." if ok else "Send failed. Check backend logs."}


@router.post("/token", response_model=TokenResponse)
def login():
    """Placeholder app login. Replace with real JWT after user/session model."""
    return TokenResponse(access_token="placeholder")
