from __future__ import annotations

import json
from typing import Any, Dict, Mapping, Optional

from . import repository
from .ai_client import (
    BRIEF_SCHEMA,
    INTERACTION_SCHEMA,
    KimiClient,
    KimiError,
    brief_system_prompt,
    build_interaction_user_prompt,
    interaction_system_prompt,
)
from .db import PathLike, connect, transaction
from .time_utils import to_iso, utc_now, validate_datetime_string


AI_MUTABLE_FIELDS = {
    "relationship_stage",
    "intent_level",
    "current_need",
    "current_obstacle",
    "next_step",
    "next_contact_at",
}

VALID_RELATIONSHIP_STAGES = {
    "new", "contacted", "interested", "considering", "rejected", "dormant"
}
VALID_INTENT_LEVELS = {"unknown", "low", "medium", "high"}
VALID_OUTCOMES = {"completed", "waiting"}
VALID_WAITING_ON = {"none", "customer", "manager", "internal", "scheduled_time"}


def _validate_interaction_suggestion(data: Mapping[str, Any]) -> Dict[str, Any]:
    suggestion = dict(data)
    stage = suggestion.get("relationship_stage")
    intent = suggestion.get("intent_level")
    outcome = suggestion.get("outcome")
    waiting_on = suggestion.get("waiting_on")

    if stage not in VALID_RELATIONSHIP_STAGES:
        raise KimiError("Kimi returned an invalid relationship_stage")
    if intent not in VALID_INTENT_LEVELS:
        raise KimiError("Kimi returned an invalid intent_level")
    if outcome not in VALID_OUTCOMES:
        raise KimiError("Kimi returned an invalid outcome")
    if waiting_on not in VALID_WAITING_ON:
        raise KimiError("Kimi returned an invalid waiting_on")
    if outcome == "waiting" and waiting_on == "none":
        raise KimiError("Kimi returned waiting without a responsible party")
    if outcome == "completed":
        suggestion["waiting_on"] = "none"

    try:
        suggestion["next_contact_at"] = validate_datetime_string(
            suggestion.get("next_contact_at")
        )
        confidence = float(suggestion.get("confidence"))
    except (TypeError, ValueError) as exc:
        raise KimiError("Kimi returned invalid typed fields") from exc
    if not 0 <= confidence <= 1:
        raise KimiError("Kimi returned confidence outside 0..1")
    suggestion["confidence"] = confidence

    summary = str(suggestion.get("structured_summary") or "").strip()
    if not summary:
        raise KimiError("Kimi returned an empty structured_summary")
    suggestion["structured_summary"] = summary
    return suggestion


class AIService:
    def __init__(
        self,
        db_path: Optional[PathLike] = None,
        client: Optional[KimiClient] = None,
    ) -> None:
        self.db_path = db_path
        self.client = client or KimiClient()

    def status(self) -> Dict[str, Any]:
        return self.client.status()

    def preview_interaction(
        self,
        *,
        customer_id: str,
        raw_content: str,
        channel: str,
        now=None,
    ) -> Dict[str, Any]:
        current_time = now or utc_now()
        with connect(self.db_path) as conn:
            customer = repository.get_customer(conn, customer_id)
        if customer is None:
            raise KeyError(customer_id)

        result = None
        for attempt in range(2):
            try:
                result = self.client.json_schema(
                    system=interaction_system_prompt(),
                    user=build_interaction_user_prompt(
                        customer=customer,
                        raw_content=raw_content,
                        channel=channel,
                        now=current_time,
                    ),
                    schema_name="interaction_extraction",
                    schema=INTERACTION_SCHEMA,
                    max_completion_tokens=2400,
                )
                break
            except KimiError as exc:
                if attempt == 0 and "structured response was invalid" in str(exc):
                    continue
                raise
        assert result is not None

        return {
            "suggested_interaction": _validate_interaction_suggestion(result.data),
            "usage": result.usage,
        }

    def extract_interaction(
        self,
        *,
        customer_id: str,
        raw_content: str,
        channel: str,
        now=None,
        source: str = "manual_interaction",
        activity_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        current_time = now or utc_now()
        with connect(self.db_path) as conn:
            customer = repository.get_customer(conn, customer_id)
        if customer is None:
            raise KeyError(customer_id)

        result = None
        for attempt in range(2):
            try:
                result = self.client.json_schema(
                    system=interaction_system_prompt(),
                    user=build_interaction_user_prompt(
                        customer=customer,
                        raw_content=raw_content,
                        channel=channel,
                        now=current_time,
                    ),
                    schema_name="interaction_extraction",
                    schema=INTERACTION_SCHEMA,
                    max_completion_tokens=2400,
                )
                break
            except KimiError as exc:
                if (
                    attempt == 0
                    and "structured response was invalid" in str(exc)
                ):
                    continue
                raise
        assert result is not None

        suggestion = _validate_interaction_suggestion(result.data)
        proposed_changes: Dict[str, Dict[str, Any]] = {}
        reason = str(suggestion.get("reasoning_summary") or "").strip()
        for field in AI_MUTABLE_FIELDS:
            new_value = suggestion.get(field)
            old_value = customer.get(field)
            if old_value == new_value:
                continue
            proposed_changes[field] = {
                "from": old_value,
                "to": new_value,
                "reason": reason,
            }

        created_at = to_iso(current_time) or ""
        with transaction(self.db_path) as conn:
            proposal_id = repository.insert_change_proposal(
                conn,
                {
                    "customer_id": customer_id,
                    "activity_id": activity_id,
                    "status": "pending",
                    "source": source,
                    "raw_content": raw_content,
                    "proposed_changes": proposed_changes,
                    "extraction_summary": str(
                        suggestion.get("structured_summary") or ""
                    ).strip(),
                    "confidence": float(suggestion.get("confidence") or 0),
                    "model": result.model,
                    "created_at": created_at,
                    "reviewed_at": None,
                    "applied_at": None,
                    "reviewer_note": "",
                },
            )
            proposal = repository.get_change_proposal(conn, proposal_id)

        assert proposal is not None
        return {
            "proposal": proposal,
            "suggested_interaction": suggestion,
            "usage": result.usage,
        }

    def customer_brief(
        self,
        customer_id: str,
        *,
        now=None,
    ) -> Dict[str, Any]:
        current_time = now or utc_now()
        with connect(self.db_path) as conn:
            customer = repository.get_customer(conn, customer_id)
            if customer is None:
                raise KeyError(customer_id)
            activities = repository.list_activities(conn, customer_id, limit=12)
            active_work = repository.get_active_work_for_customer(conn, customer_id)

        payload = {
            "current_time": to_iso(current_time),
            "customer_snapshot": {
                "customer_id": customer["customer_id"],
                "age_band": customer["age_band"],
                "customer_level": customer["customer_level"],
                "risk_level": customer["risk_level"],
                "total_assets_band": customer["total_assets_band"],
                "investable_funds_band": customer["investable_funds_band"],
                "holdings_summary": customer["holdings_summary"],
                "recent_login_at": customer["recent_login_at"],
                "recent_trade_at": customer["recent_trade_at"],
                "asset_change_30d_pct": customer["asset_change_30d_pct"],
                "recent_product_interest": customer["recent_product_interest"],
                "recent_consult_topic": customer["recent_consult_topic"],
                "relationship_stage": customer["relationship_stage"],
                "intent_level": customer["intent_level"],
                "current_need": customer["current_need"],
                "current_obstacle": customer["current_obstacle"],
                "current_progress": customer["current_progress"],
                "next_step": customer["next_step"],
                "next_contact_at": customer["next_contact_at"],
                "profile": customer.get("profile") or {},
                "profile_hypotheses": customer.get("profile_hypotheses") or [],
            },
            "active_work": active_work,
            "recent_activities": [
                {
                    "occurred_at": item["occurred_at"],
                    "channel": item["channel"],
                    "structured_summary": item["structured_summary"],
                    "customer_feedback": item["customer_feedback"],
                    "action_taken": item["action_taken"],
                    "next_step": item["next_step"],
                }
                for item in activities
            ],
        }

        result = None
        for attempt in range(2):
            try:
                result = self.client.json_schema(
                    system=brief_system_prompt(),
                    user=json.dumps(payload, ensure_ascii=False, indent=2),
                    schema_name="customer_brief",
                    schema=BRIEF_SCHEMA,
                    max_completion_tokens=1600,
                )
                break
            except KimiError as exc:
                if (
                    attempt == 0
                    and "structured response was invalid" in str(exc)
                ):
                    continue
                raise
        assert result is not None
        return {
            **result.data,
            "model": result.model,
            "generated_at": to_iso(current_time),
        }
