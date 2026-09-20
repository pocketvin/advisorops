from datetime import datetime
from typing import Any, Callable, Dict, Mapping, Optional

from . import repository
from .db import PathLike, connect, transaction
from .priority import evaluate_discovery
from .seed import ensure_seeded, reset_demo_data
from .time_utils import business_day_window, to_iso, utc_now


class CustomerNotFoundError(KeyError):
    pass


class WorkItemNotFoundError(KeyError):
    pass


class InvalidWorkStateError(RuntimeError):
    pass


Clock = Callable[[], datetime]


class WorkbenchService:
    def __init__(
        self,
        db_path: Optional[PathLike] = None,
        clock: Clock = utc_now,
    ) -> None:
        self.db_path = db_path
        self.clock = clock
        ensure_seeded(self.db_path, now=self.clock())

    def _day_window_iso(self) -> tuple[str, str]:
        start, end = business_day_window(self.clock())
        return to_iso(start) or "", to_iso(end) or ""

    def workbench(self) -> Dict[str, Any]:
        now = self.clock()
        day_start, day_end = self._day_window_iso()

        with connect(self.db_path) as conn:
            active = repository.list_active_work(conn)
            completed = repository.list_completed_today(conn, day_start, day_end)
            active_customer_ids = {item["customer_id"] for item in active}
            completed_customer_ids = {item["customer_id"] for item in completed}

            discovery = []
            for customer in repository.list_customers(conn):
                if customer["customer_id"] in active_customer_ids:
                    continue
                if customer["customer_id"] in completed_customer_ids:
                    continue

                result = evaluate_discovery(customer, now=now)
                if result is None:
                    continue

                discovery.append(
                    {
                        "customer": customer,
                        "discovery": result.to_dict(),
                    }
                )

        discovery.sort(
            key=lambda item: (
                bool(item["discovery"]["pinned"]),
                item["discovery"]["score"],
            ),
            reverse=True,
        )

        action_required = [item for item in active if item["status"] == "action_required"]
        waiting = [item for item in active if item["status"] == "waiting"]

        return {
            "summary": {
                "action_required": len(action_required),
                "waiting": len(waiting),
                "completed_today": len(completed),
                "discovery": len(discovery),
            },
            "work_area": {
                "action_required": action_required,
                "waiting": waiting,
                "completed_today": completed,
            },
            "discovery": discovery,
        }

    def customer_detail(self, customer_id: str) -> Dict[str, Any]:
        with connect(self.db_path) as conn:
            customer = repository.get_customer(conn, customer_id)
            if customer is None:
                raise CustomerNotFoundError(customer_id)
            return {
                "customer": customer,
                "active_work_item": repository.get_active_work_for_customer(
                    conn,
                    customer_id,
                ),
                "activities": repository.list_activities(conn, customer_id),
                "field_changes": repository.list_audits(conn, customer_id),
            }

    def start_work(self, customer_id: str) -> Dict[str, Any]:
        now = self.clock()
        now_iso = to_iso(now) or ""

        with transaction(self.db_path) as conn:
            customer = repository.get_customer(conn, customer_id)
            if customer is None:
                raise CustomerNotFoundError(customer_id)

            existing = repository.get_active_work_for_customer(conn, customer_id)
            if existing is not None:
                return existing

            discovery = evaluate_discovery(customer, now=now)
            if discovery is None:
                raise InvalidWorkStateError("该客户当前没有新的可执行发现理由")

            work_item_id = repository.create_work_item(
                conn,
                {
                    "customer_id": customer_id,
                    "title": discovery.suggested_action,
                    "status": "action_required",
                    "waiting_on": "manager",
                    "current_progress": customer.get("current_progress") or "",
                    "next_action": discovery.suggested_action,
                    "due_at": customer.get("next_contact_at"),
                    "started_at": now_iso,
                    "completed_at": None,
                    "completion_activity_id": None,
                    "created_at": now_iso,
                    "updated_at": now_iso,
                },
            )

            repository.insert_activity(
                conn,
                {
                    "customer_id": customer_id,
                    "source": "manual",
                    "channel": "system",
                    "activity_type": "work_started",
                    "occurred_at": now_iso,
                    "raw_content": "",
                    "structured_summary": f"开始处理：{discovery.suggested_action}",
                    "customer_feedback": "",
                    "action_taken": "开始跟进",
                    "next_step": discovery.suggested_action,
                    "next_contact_at": customer.get("next_contact_at"),
                    "stage_after": customer.get("relationship_stage"),
                    "intent_after": customer.get("intent_level"),
                    "metadata": {
                        "discovery_score": discovery.score,
                        "actionable_reason": discovery.actionable_reason,
                    },
                    "created_at": now_iso,
                },
            )

            work_item = repository.get_work_item(conn, work_item_id)
            assert work_item is not None
            return work_item

    def record_interaction(
        self,
        work_item_id: int,
        payload: Mapping[str, Any],
    ) -> Dict[str, Any]:
        now = self.clock()
        now_iso = to_iso(now) or ""

        with transaction(self.db_path) as conn:
            work_item = repository.get_work_item(conn, work_item_id)
            if work_item is None:
                raise WorkItemNotFoundError(work_item_id)
            if work_item["status"] not in {"action_required", "waiting"}:
                raise InvalidWorkStateError("只有进行中的工作项可以记录新的处理结果")

            customer = repository.get_customer(conn, work_item["customer_id"])
            if customer is None:
                raise CustomerNotFoundError(work_item["customer_id"])

            stage = str(payload.get("relationship_stage") or customer["relationship_stage"])
            intent = str(payload.get("intent_level") or customer["intent_level"])
            raw_content = str(payload.get("raw_content") or "").strip()
            summary = str(payload.get("structured_summary") or "").strip()
            feedback = str(payload.get("customer_feedback") or "").strip()
            next_step = str(payload.get("next_step") or "").strip()
            next_contact_at = payload.get("next_contact_at") or None
            current_need = str(payload.get("current_need") or customer.get("current_need") or "").strip()
            current_obstacle = str(
                payload.get("current_obstacle") or customer.get("current_obstacle") or ""
            ).strip()
            channel = str(payload.get("channel") or "phone")
            outcome = str(payload.get("outcome") or "completed")
            waiting_on = str(payload.get("waiting_on") or "none")

            if not raw_content:
                raise ValueError("必须保留本次沟通的原始记录")
            if not summary:
                raise ValueError("必须确认本次沟通的结构化摘要")
            if outcome not in {"completed", "waiting"}:
                raise ValueError("outcome 必须为 completed 或 waiting")
            if outcome == "waiting" and waiting_on == "none":
                raise ValueError("等待中必须说明 waiting_on")

            activity_id = repository.insert_activity(
                conn,
                {
                    "customer_id": customer["customer_id"],
                    "source": "manual",
                    "channel": channel,
                    "activity_type": "interaction",
                    "occurred_at": now_iso,
                    "raw_content": raw_content,
                    "structured_summary": summary,
                    "customer_feedback": feedback,
                    "action_taken": str(payload.get("action_taken") or "客户跟进").strip(),
                    "next_step": next_step,
                    "next_contact_at": next_contact_at,
                    "stage_after": stage,
                    "intent_after": intent,
                    "metadata": {
                        "confirmation_mode": "human_confirmed",
                        "ai_extraction": False,
                    },
                    "created_at": now_iso,
                },
            )

            customer_updates = {
                "relationship_stage": stage,
                "intent_level": intent,
                "current_need": current_need,
                "current_obstacle": current_obstacle,
                "current_progress": summary,
                "next_step": next_step,
                "next_contact_at": next_contact_at,
                "last_contact_at": now_iso,
                "recent_signal": "",
                "updated_at": now_iso,
            }

            auditable_fields = (
                "relationship_stage",
                "intent_level",
                "current_need",
                "current_obstacle",
                "current_progress",
                "next_step",
                "next_contact_at",
            )
            audits = []
            for field in auditable_fields:
                old_value = customer.get(field)
                new_value = customer_updates.get(field)
                if old_value == new_value:
                    continue
                audits.append(
                    {
                        "customer_id": customer["customer_id"],
                        "source_activity_id": activity_id,
                        "field_name": field,
                        "old_value": None if old_value is None else str(old_value),
                        "new_value": None if new_value is None else str(new_value),
                        "changed_by": "relationship_manager",
                        "changed_at": now_iso,
                    }
                )

            repository.update_customer(
                conn,
                customer["customer_id"],
                customer_updates,
            )
            repository.insert_audits(conn, audits)

            if outcome == "waiting":
                repository.update_work_item(
                    conn,
                    work_item_id,
                    {
                        "status": "waiting",
                        "waiting_on": waiting_on,
                        "current_progress": summary,
                        "next_action": next_step,
                        "due_at": next_contact_at,
                        "updated_at": now_iso,
                    },
                )
            else:
                repository.update_work_item(
                    conn,
                    work_item_id,
                    {
                        "status": "completed_today",
                        "waiting_on": "none",
                        "current_progress": summary,
                        "next_action": next_step,
                        "due_at": next_contact_at,
                        "completed_at": now_iso,
                        "completion_activity_id": activity_id,
                        "updated_at": now_iso,
                    },
                )

            updated_work = repository.get_work_item(conn, work_item_id)
            updated_customer = repository.get_customer(conn, customer["customer_id"])
            assert updated_work is not None
            assert updated_customer is not None

            return {
                "work_item": updated_work,
                "customer": updated_customer,
                "activity_id": activity_id,
                "applied_changes": audits,
            }

    def reset_demo(self) -> Dict[str, Any]:
        reset_demo_data(self.db_path, now=self.clock())
        return self.workbench()
