from __future__ import annotations

from pydantic import BaseModel


class SignedMediaUrlResponse(BaseModel):
    asset_id: str
    signed_url: str
    expires_in_minutes: int
