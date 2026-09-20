from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from .time_utils import validate_datetime_string


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
Channel = Literal["phone", "wecom", "meeting", "app", "other"]
ImageMimeType = Literal["image/jpeg", "image/png", "image/webp"]


class ImageAttachmentInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    mime_type: ImageMimeType
    data_url: str = Field(min_length=20, max_length=9_000_000)


class AIExtractRequest(BaseModel):
    raw_content: str = Field(default="", max_length=8000)
    channel: Channel = "phone"
    attachments: List[ImageAttachmentInput] = Field(default_factory=list, max_length=4)

    @model_validator(mode="after")
    def require_content(self):
        if not self.raw_content.strip() and not self.attachments:
            raise ValueError("请先输入沟通内容或上传图片")
        return self


class QuickRecordPrepareRequest(BaseModel):
    raw_content: str = Field(min_length=1, max_length=8000)
    channel: Channel = "phone"
    attachments: List[ImageAttachmentInput] = Field(default_factory=list, max_length=4)


class PinRequest(BaseModel):
    pinned: bool


class DeferRequest(BaseModel):
    days: Optional[int] = Field(default=None, ge=1, le=90)
    next_contact_at: Optional[str] = None

    @field_validator("next_contact_at")
    @classmethod
    def validate_next_contact_at(cls, value: Optional[str]) -> Optional[str]:
        try:
            return validate_datetime_string(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("next_contact_at 必须是 ISO 8601 时间") from exc

    @model_validator(mode="after")
    def fill_default(self):
        if self.days is None and self.next_contact_at is None:
            self.days = 3
        return self


class InteractionRequest(BaseModel):
    raw_content: str = Field(default="", max_length=8000)
    structured_summary: str = Field(min_length=1, max_length=1500)
    customer_feedback: str = Field(default="", max_length=1500)
    action_taken: str = Field(default="客户跟进", max_length=120)
    relationship_stage: RelationshipStage
    intent_level: IntentLevel
    current_need: str = Field(default="", max_length=800)
    current_obstacle: str = Field(default="", max_length=800)
    manager_note: str = Field(default="", max_length=1200)
    next_step: str = Field(default="", max_length=800)
    next_contact_at: Optional[str] = None
    channel: Channel = "phone"
    outcome: InteractionOutcome = "completed"
    waiting_on: WaitingOn = "none"
    proposal_id: Optional[int] = None
    attachments: List[ImageAttachmentInput] = Field(default_factory=list, max_length=4)

    @field_validator("next_contact_at")
    @classmethod
    def validate_next_contact_at(cls, value: Optional[str]) -> Optional[str]:
        try:
            return validate_datetime_string(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("next_contact_at 必须是 ISO 8601 时间") from exc

    @model_validator(mode="after")
    def validate_record(self):
        if not self.raw_content.strip() and not self.attachments:
            raise ValueError("必须保留本次沟通文字或至少一张图片")
        if self.outcome == "waiting" and self.waiting_on == "none":
            raise ValueError("等待中必须说明当前在等谁或什么")
        return self


class ContextPackRequest(BaseModel):
    question: str = Field(default="", max_length=1000)


class DemoTimeRequest(BaseModel):
    days: int = Field(default=0, ge=-365, le=365)
    hours: int = Field(default=0, ge=-8760, le=8760)
