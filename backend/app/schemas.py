from typing import Literal, Optional

from pydantic import BaseModel, Field


Stage = Literal["new", "contacted", "interested", "considering", "rejected", "dormant"]
Intent = Literal["unknown", "low", "medium", "high"]


class PinRequest(BaseModel):
    pinned: bool


class RejectRequest(BaseModel):
    feedback: str = ""
    cooldown_days: int = Field(default=30, ge=1, le=180)


class ConsiderRequest(BaseModel):
    feedback: str = ""
    follow_up_days: int = Field(default=3, ge=1, le=90)


class FollowUpRequest(BaseModel):
    action: str = Field(min_length=1, max_length=120)
    feedback: str = Field(default="", max_length=300)
    stage: Stage
    intent: Intent
    next_step: str = Field(default="", max_length=200)
    next_contact_at: Optional[str] = None
    contact_method: str = Field(default="电话", max_length=30)


class BehaviorSignalRequest(BaseModel):
    asset_change_30d_pct: Optional[float] = Field(default=None, ge=-100, le=500)
    recent_product_interest: Optional[str] = Field(default=None, max_length=100)
    recent_consult_topic: Optional[str] = Field(default=None, max_length=100)
