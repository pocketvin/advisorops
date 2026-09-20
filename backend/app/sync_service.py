from __future__ import annotations

from typing import Any, Dict, List, Optional

from . import repository
from .ai_client import KimiError
from .ai_service import AIService
from .db import PathLike, connect, transaction
from .time_utils import to_iso, utc_now


SOURCES = ("mock_wecom", "mock_behavior", "mock_crm")


class SyncService:
    def __init__(
        self,
        db_path: Optional[PathLike] = None,
        ai_service: Optional[AIService] = None,
    ) -> None:
        self.db_path = db_path
        self.ai_service = ai_service or AIService(db_path=db_path)

    def status(self) -> Dict[str, Any]:
        with connect(self.db_path) as conn:
            states = repository.list_sync_states(conn)
        return {
            "sources": states,
            "configured_sources": list(SOURCES),
        }

    def refresh(self, *, now=None) -> Dict[str, Any]:
        current = now or utc_now()
        now_iso = to_iso(current) or ""
        ingested: List[Dict[str, Any]] = []
        extraction_jobs: List[Dict[str, Any]] = []
        source_results: List[Dict[str, Any]] = []

        for source in SOURCES:
            with connect(self.db_path) as conn:
                state = repository.get_sync_state(conn, source) or {
                    "cursor": 0,
                    "last_success_at": None,
                }
                cursor = int(state.get("cursor") or 0)
                events = repository.fetch_external_events(
                    conn,
                    source,
                    cursor,
                    limit=1,
                )

            if not events:
                with transaction(self.db_path) as conn:
                    repository.upsert_sync_state(
                        conn,
                        source=source,
                        cursor=cursor,
                        last_attempt_at=now_iso,
                        last_success_at=state.get("last_success_at"),
                        last_error="",
                        last_result_count=0,
                    )
                source_results.append(
                    {
                        "source": source,
                        "count": 0,
                        "cursor": cursor,
                        "status": "up_to_date",
                    }
                )
                continue

            event = events[0]
            activity_id: Optional[int] = None
            new_cursor = cursor
            try:
                with transaction(self.db_path) as conn:
                    if repository.external_event_ingested(
                        conn,
                        source,
                        event["source_event_id"],
                    ):
                        new_cursor = max(cursor, int(event["sequence_number"]))
                    else:
                        summary = {
                            "message": "收到新的客户沟通信息，等待确认状态变化。",
                            "behavior_signal": "收到新的客户行为信号。",
                            "fact": "收到外部系统的确定事实。",
                        }.get(event["event_kind"], "收到新的外部客户动态。")

                        activity_id = repository.insert_activity(
                            conn,
                            {
                                "customer_id": event["customer_id"],
                                "source": source,
                                "channel": event["channel"],
                                "activity_type": (
                                    "behavior_signal"
                                    if event["event_kind"] == "behavior_signal"
                                    else "sync_fact"
                                ),
                                "occurred_at": event["occurred_at"],
                                "raw_content": event["raw_content"],
                                "structured_summary": summary,
                                "customer_feedback": (
                                    event["raw_content"]
                                    if event["event_kind"] == "message"
                                    else ""
                                ),
                                "action_taken": "外部信息同步",
                                "next_step": "",
                                "next_contact_at": None,
                                "stage_after": None,
                                "intent_after": None,
                                "metadata": {
                                    "source_event_id": event["source_event_id"],
                                    "event_kind": event["event_kind"],
                                },
                                "created_at": now_iso,
                            },
                        )
                        repository.mark_external_event_ingested(
                            conn,
                            source=source,
                            source_event_id=event["source_event_id"],
                            activity_id=activity_id,
                            ingested_at=now_iso,
                        )

                        if event["event_kind"] == "behavior_signal":
                            payload = event.get("payload", {})
                            signal = str(
                                payload.get("signal")
                                or event["raw_content"]
                            ).strip()
                            updates = {
                                "recent_signal": signal,
                                "updated_at": now_iso,
                            }
                            for field in (
                                "recent_login_at",
                                "recent_trade_at",
                                "asset_change_30d_pct",
                                "recent_product_interest",
                                "recent_consult_topic",
                            ):
                                if field in payload:
                                    updates[field] = payload[field]
                            repository.update_customer(
                                conn,
                                event["customer_id"],
                                updates,
                            )
                        elif event["event_kind"] == "message":
                            repository.update_customer(
                                conn,
                                event["customer_id"],
                                {
                                    "last_contact_at": event["occurred_at"],
                                    "updated_at": now_iso,
                                },
                            )

                        new_cursor = max(cursor, int(event["sequence_number"]))

                    repository.upsert_sync_state(
                        conn,
                        source=source,
                        cursor=new_cursor,
                        last_attempt_at=now_iso,
                        last_success_at=now_iso,
                        last_error="",
                        last_result_count=1 if activity_id else 0,
                    )

                if activity_id:
                    ingested.append(
                        {
                            "source": source,
                            "source_event_id": event["source_event_id"],
                            "customer_id": event["customer_id"],
                            "activity_id": activity_id,
                            "event_kind": event["event_kind"],
                        }
                    )
                    if event["event_kind"] == "message":
                        extraction_jobs.append(
                            {
                                "customer_id": event["customer_id"],
                                "raw_content": event["raw_content"],
                                "channel": event["channel"],
                                "activity_id": activity_id,
                                "source": f"sync:{source}",
                            }
                        )

                source_results.append(
                    {
                        "source": source,
                        "count": 1 if activity_id else 0,
                        "cursor": new_cursor,
                        "status": "ok",
                    }
                )
            except Exception as exc:
                with transaction(self.db_path) as conn:
                    repository.upsert_sync_state(
                        conn,
                        source=source,
                        cursor=cursor,
                        last_attempt_at=now_iso,
                        last_success_at=state.get("last_success_at"),
                        last_error=str(exc)[:500],
                        last_result_count=0,
                    )
                source_results.append(
                    {
                        "source": source,
                        "count": 0,
                        "cursor": cursor,
                        "status": "error",
                        "error": str(exc)[:300],
                    }
                )

        ai_results: List[Dict[str, Any]] = []
        for job in extraction_jobs:
            try:
                result = self.ai_service.extract_interaction(
                    customer_id=job["customer_id"],
                    raw_content=job["raw_content"],
                    channel=job["channel"],
                    now=current,
                    source=job["source"],
                    activity_id=job["activity_id"],
                )
                ai_results.append(
                    {
                        "activity_id": job["activity_id"],
                        "customer_id": job["customer_id"],
                        "proposal_id": result["proposal"]["id"],
                        "status": "pending_confirmation",
                    }
                )
            except KimiError as exc:
                ai_results.append(
                    {
                        "activity_id": job["activity_id"],
                        "customer_id": job["customer_id"],
                        "proposal_id": None,
                        "status": "ai_failed",
                        "error": str(exc)[:300],
                    }
                )

        return {
            "refreshed_at": now_iso,
            "sources": source_results,
            "ingested": ingested,
            "ai_results": ai_results,
            "new_count": len(ingested),
            "pending_proposals_created": sum(
                1 for item in ai_results if item["proposal_id"] is not None
            ),
        }
