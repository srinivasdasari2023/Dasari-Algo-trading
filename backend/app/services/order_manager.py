"""
Order Manager: Upstox order placement with idempotency.
No hardcoded credentials; token from auth/session.
"""
from dataclasses import dataclass
from typing import Literal


@dataclass
class PlaceOrderParams:
    idempotency_key: str
    instrument_key: str
    side: Literal["BUY", "SELL"]
    quantity: int
    order_type: str
    sl_trigger: float | None = None


@dataclass
class OrderResult:
    order_id: str
    broker_order_id: str | None
    status: str
    message: str | None = None


class OrderManager:
    """Upstox order API client. Idempotency handled by caller (Redis) before place."""

    def __init__(self, api_base_url: str, get_access_token: callable):  # type: ignore[type-arg]
        self.api_base_url = api_base_url
        self.get_access_token = get_access_token

    async def place(self, params: PlaceOrderParams) -> OrderResult:
        """
        Place order via Upstox. Caller must check idempotency_key first.
        On duplicate key, return existing order result instead of calling API.
        """
        # TODO: GET token, POST /order/place with instrument_key, quantity, order_type, sl
        return OrderResult(
            order_id="placeholder",
            broker_order_id=None,
            status="PENDING",
            message="Not implemented",
        )

    async def get_positions(self) -> list[dict]:
        """Fetch open positions from Upstox."""
        return []
