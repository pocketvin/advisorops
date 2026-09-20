from typing import Literal, Optional

from pydantic import BaseModel, Field


RelationshipStage = Literal[
    "new",
    "contacted",
    "interested",
    "considering",
    "rejected",
    "dormant",
]
IntentLevel = Literal["unknown", "low", "medium", "high"]
InteractionOutcome = Literal["completed", "waiting"]
WaitingOn = Literal["none", "customer", "manager", "internal", "scheduled_time"]


class InteractionRequest(BaseModel):
    raw_content: str = Field(min_length=1, max_length=4000)
    structured_summary: str = Field(min_length=1, max_length=1000)
    customer_feedback: str = Field(default="", max_length=1000)
    action_taken: str = Field(default="客户跟进", max_length=120)
    relationship_stage: RelationshipStage
    intent_level: IntentLevel
    current_need: str = Field(default="", max_length=500)
    current_obstacle: str = Field(default="", max_length=500)
    next_step: str = Field(default="", max_length=500)
    next_contact_at: Optional[str] = None
    channel: Literal["phone", "wecom", "meeting", "app", "other"] = "phone"
    outcome: InteractionOutcome = "completed"
    waiting_on: WaitingOn = "none"
