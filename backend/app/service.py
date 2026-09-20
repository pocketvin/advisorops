from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Mapping, Optional, Sequence

from . import repository
from .ai_client import KimiError
from .ai_service import AIService, AI_MUTABLE_FIELDS
from .context_pack import ContextPackService
from .db import PathLike, connect, transaction
from .priority import evaluate_discovery
from .seed import ensure_seeded, reset_demo_data
from .sync_service import SyncService
from .time_utils import business_day_window, to_iso, utc_now


class CustomerNotFoundError(KeyError):
    pass


class WorkItemNotFoundError(KeyError):
    pass


class ProposalNotFoundError(KeyError):
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
        self.ai = AIService(db_path=self.db_path)
        self.context_pack = ContextPackService(db_path=self.db_path)
        self.sync = SyncService(db_path=self.db_path, ai_service=self.ai)

    def _now(self) -> datetime:
        base = self.clock()
        with connect(self.db_path) as conn:
            offset_raw = repository.get_demo_state(
                conn,
                "time_offset_seconds",
                "0",
            )
        try:
            offset_seconds = int(offset_raw)
        except ValueError:
            offset_seconds = 0
        return base + timedelta(seconds=offset_seconds)

    def _day_window_iso(self) -> tuple[str, str]:
        start, end = business_day_window(self._now())
        return to_iso(start) or "", to_iso(end) or ""

    def meta(self) -> Dict[str, Any]:
        return {
            "product_name": "客户经营工作台",
            "working_name": True,
            "positioning": "证券客户经理日常客户经营辅助原型",
            "data_notice": "全部客户均为模拟数据，不连接任何券商内部系统。",
            "ai": {"configured": self.ai.status()["configured"]},
            "demo_time": to_iso(self._now()),
            "compliance": [
                "发现区优先级仅用于安排客户经理工作顺序",
                "涉及具体产品时仍需遵循真实机构适当性流程",
                "AI 只提出候选变化，解释性字段保留人工确认",
                "不自动发送金融建议，不自动替客户做投资决策",
            ],
        }

    def workbench(self) -> Dict[str, Any]:
        now = self._now()
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
                item["customer"].get("next_contact_at") or "9999",
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
            "demo_time": to_iso(now),
        }

    def customers(
        self,
        *,
        search: str = "",
        stage: str = "",
        risk_level: str = "",
        intent: str = "",
        customer_level: str = "",
        total_assets_band: str = "",
        sort_by: str = "priority",
    ) -> list[Dict[str, Any]]:
        now = self._now()
        with connect(self.db_path) as conn:
            customers = repository.customer_search(
                conn,
                search=search,
                stage=stage,
                risk_level=risk_level,
                intent=intent,
                customer_level=customer_level,
                total_assets_band=total_assets_band,
            )
            result: list[Dict[str, Any]] = []
            for customer in customers:
                discovery = evaluate_discovery(customer, now=now)
                work_item = repository.get_active_work_for_customer(
                    conn,
                    customer["customer_id"],
                )
                result.append(
                    {
                        "customer": customer,
                        "active_work_item": work_item,
                        "discovery": discovery.to_dict() if discovery else None,
                    }
                )
        if sort_by == "priority":
            result.sort(
                key=lambda item: (
                    bool(item["customer"].get("pinned")),
                    item["discovery"]["score"] if item["discovery"] else -1,
                    item["customer"].get("updated_at") or "",
                ),
                reverse=True,
            )
        elif sort_by == "name":
            result.sort(key=lambda item: item["customer"]["name"])
        elif sort_by == "recent":
            result.sort(
                key=lambda item: item["customer"].get("last_contact_at") or "",
                reverse=True,
            )
        return result

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
                "pending_proposals": repository.list_change_proposals(
                    conn,
                    customer_id=customer_id,
                    status="pending",
                ),
            }

    def quick_record_prepare(
        self,
        *,
        raw_content: str,
        channel: str,
    ) -> Dict[str, Any]:
        content = raw_content.strip()
        if not content:
            raise ValueError("请先输入客户姓名和本次发生的事情")

        normalized = content.casefold()
        with connect(self.db_path) as conn:
            customers = repository.list_customers(conn)

        matches = [
            customer
            for customer in customers
            if customer["name"] in content
            or customer["customer_id"].casefold() in normalized
        ]

        if not matches:
            raise ValueError("没有识别到客户，请在记录里写明客户姓名或客户编号")
        unique = {customer["customer_id"]: customer for customer in matches}
        if len(unique) > 1:
            names = "、".join(customer["name"] for customer in unique.values())
            raise ValueError(f"识别到多个客户（{names}），请一次只记录一位客户")

        customer = next(iter(unique.values()))
        try:
            preview = self.ai.preview_interaction(
                customer_id=customer["customer_id"],
                raw_content=content,
                channel=channel,
                now=self._now(),
            )
            return {
                "customer": customer,
                "ai_ready": True,
                "warning": None,
                **preview,
            }
        except KimiError:
            return {
                "customer": customer,
                "ai_ready": False,
                "warning": "智能整理暂不可用，已识别客户；可以手工补全后直接保存。",
                "suggested_interaction": {
                    "structured_summary": "",
                    "customer_feedback": "",
                    "relationship_stage": customer["relationship_stage"],
                    "intent_level": customer["intent_level"],
                    "current_need": customer["current_need"],
                    "current_obstacle": customer["current_obstacle"],
                    "next_step": customer["next_step"],
                    "next_contact_at": customer["next_contact_at"],
                    "outcome": "completed",
                    "waiting_on": "none",
                    "reasoning_summary": "",
                    "confidence": 0,
                },
                "usage": {},
            }

    def start_work(self, customer_id: str) -> Dict[str, Any]:
        now = self._now()
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

    def ensure_manual_work(self, customer_id: str) -> Dict[str, Any]:
        now = self._now()
        now_iso = to_iso(now) or ""
        with transaction(self.db_path) as conn:
            customer = repository.get_customer(conn, customer_id)
            if customer is None:
                raise CustomerNotFoundError(customer_id)
            existing = repository.get_active_work_for_customer(conn, customer_id)
            if existing is not None:
                return existing
            work_item_id = repository.create_work_item(
                conn,
                {
                    "customer_id": customer_id,
                    "title": "记录本次客户沟通",
                    "status": "action_required",
                    "waiting_on": "manager",
                    "current_progress": customer.get("current_progress") or "",
                    "next_action": "记录刚刚发生的客户沟通",
                    "due_at": None,
                    "started_at": now_iso,
                    "completed_at": None,
                    "completion_activity_id": None,
                    "created_at": now_iso,
                    "updated_at": now_iso,
                },
            )
            work_item = repository.get_work_item(conn, work_item_id)
            assert work_item is not None
            return work_item

    def set_pin(self, customer_id: str, pinned: bool) -> Dict[str, Any]:
        now_iso = to_iso(self._now()) or ""
        with transaction(self.db_path) as conn:
            customer = repository.get_customer(conn, customer_id)
            if customer is None:
                raise CustomerNotFoundError(customer_id)
            repository.update_customer(
                conn,
                customer_id,
                {
                    "pinned": pinned,
                    "updated_at": now_iso,
                },
            )
            repository.insert_activity(
                conn,
                {
                    "customer_id": customer_id,
                    "source": "manual",
                    "channel": "system",
                    "activity_type": "state_change",
                    "occurred_at": now_iso,
                    "raw_content": "",
                    "structured_summary": "人工置顶当前客户" if pinned else "取消人工置顶",
                    "customer_feedback": "",
                    "action_taken": "人工置顶" if pinned else "取消置顶",
                    "next_step": customer.get("next_step") or "",
                    "next_contact_at": customer.get("next_contact_at"),
                    "stage_after": customer.get("relationship_stage"),
                    "intent_after": customer.get("intent_level"),
                    "metadata": {"pinned": pinned},
                    "created_at": now_iso,
                },
            )
            updated = repository.get_customer(conn, customer_id)
            assert updated is not None
            return updated

    def defer_customer(self, customer_id: str, days: int = 3) -> Dict[str, Any]:
        now = self._now()
        now_iso = to_iso(now) or ""
        days = max(1, min(days, 90))
        next_contact = to_iso(now + timedelta(days=days))
        with transaction(self.db_path) as conn:
            customer = repository.get_customer(conn, customer_id)
            if customer is None:
                raise CustomerNotFoundError(customer_id)
            if repository.get_active_work_for_customer(conn, customer_id):
                raise InvalidWorkStateError("客户已在工作区，请在当前工作项中调整时间")
            repository.update_customer(
                conn,
                customer_id,
                {
                    "next_contact_at": next_contact,
                    "next_step": f"{days} 天后重新查看",
                    "recent_signal": "",
                    "pinned": False,
                    "updated_at": now_iso,
                },
            )
            repository.insert_activity(
                conn,
                {
                    "customer_id": customer_id,
                    "source": "manual",
                    "channel": "system",
                    "activity_type": "state_change",
                    "occurred_at": now_iso,
                    "raw_content": "",
                    "structured_summary": f"客户经理暂缓处理，{days} 天后重新查看。",
                    "customer_feedback": "",
                    "action_taken": "暂缓",
                    "next_step": f"{days} 天后重新查看",
                    "next_contact_at": next_contact,
                    "stage_after": customer.get("relationship_stage"),
                    "intent_after": customer.get("intent_level"),
                    "metadata": {"defer_days": days},
                    "created_at": now_iso,
                },
            )
            updated = repository.get_customer(conn, customer_id)
            assert updated is not None
            return updated

    def ai_extract_interaction(
        self,
        customer_id: str,
        *,
        raw_content: str,
        channel: str,
    ) -> Dict[str, Any]:
        try:
            return self.ai.extract_interaction(
                customer_id=customer_id,
                raw_content=raw_content,
                channel=channel,
                now=self._now(),
            )
        except KeyError as exc:
            raise CustomerNotFoundError(customer_id) from exc

    def ai_customer_brief(self, customer_id: str) -> Dict[str, Any]:
        try:
            return self.ai.customer_brief(customer_id, now=self._now())
        except KeyError as exc:
            raise CustomerNotFoundError(customer_id) from exc

    def ai_context(
        self,
        customer_id: str,
        *,
        question: str = "",
    ) -> Dict[str, Any]:
        try:
            return self.context_pack.build(customer_id, question=question)
        except KeyError as exc:
            raise CustomerNotFoundError(customer_id) from exc

    def _validate_proposal_for_customer(
        self,
        conn,
        proposal_id: Optional[int],
        customer_id: str,
    ) -> Optional[Dict[str, Any]]:
        if proposal_id is None:
            return None
        proposal = repository.get_change_proposal(conn, proposal_id)
        if proposal is None:
            raise ProposalNotFoundError(proposal_id)
        if proposal["customer_id"] != customer_id:
            raise InvalidWorkStateError("AI Proposal 不属于当前客户")
        if proposal["status"] != "pending":
            raise InvalidWorkStateError("AI Proposal 已经被处理")
        return proposal

    def record_interaction(
        self,
        work_item_id: int,
        payload: Mapping[str, Any],
    ) -> Dict[str, Any]:
        now = self._now()
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

            proposal_id = payload.get("proposal_id")
            proposal = self._validate_proposal_for_customer(
                conn,
                int(proposal_id) if proposal_id is not None else None,
                customer["customer_id"],
            )

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
            manager_note = str(
                payload.get("manager_note")
                if payload.get("manager_note") is not None
                else customer.get("manager_note") or ""
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

            cooldown_until = customer.get("cooldown_until")
            pinned = customer.get("pinned")
            if stage == "rejected":
                cooldown_until = to_iso(now + timedelta(days=30))
                pinned = False
                if not next_contact_at:
                    next_contact_at = cooldown_until
                if not next_step:
                    next_step = "30 天冷静期结束后再做低打扰服务复核"
            elif customer.get("relationship_stage") == "rejected":
                cooldown_until = None

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
                        "ai_proposal_id": proposal["id"] if proposal else None,
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
                "manager_note": manager_note,
                "next_step": next_step,
                "next_contact_at": next_contact_at,
                "last_contact_at": now_iso,
                "recent_signal": "",
                "cooldown_until": cooldown_until,
                "pinned": pinned,
                "updated_at": now_iso,
            }

            auditable_fields = (
                "relationship_stage",
                "intent_level",
                "current_need",
                "current_obstacle",
                "current_progress",
                "manager_note",
                "next_step",
                "next_contact_at",
                "cooldown_until",
                "pinned",
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

            if proposal:
                repository.update_change_proposal(
                    conn,
                    proposal["id"],
                    {
                        "status": "applied",
                        "activity_id": activity_id,
                        "reviewed_at": now_iso,
                        "applied_at": now_iso,
                        "reviewer_note": "客户经理确认后随本次沟通记录应用",
                    },
                )

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

    def apply_change_proposal(self, proposal_id: int) -> Dict[str, Any]:
        now = self._now()
        now_iso = to_iso(now) or ""
        with transaction(self.db_path) as conn:
            proposal = repository.get_change_proposal(conn, proposal_id)
            if proposal is None:
                raise ProposalNotFoundError(proposal_id)
            if proposal["status"] != "pending":
                raise InvalidWorkStateError("该 Proposal 已经被处理")

            customer = repository.get_customer(conn, proposal["customer_id"])
            if customer is None:
                raise CustomerNotFoundError(proposal["customer_id"])

            updates: Dict[str, Any] = {
                "updated_at": now_iso,
                "current_progress": proposal["extraction_summary"]
                or customer.get("current_progress")
                or "",
            }
            audits = []
            for field, change in proposal["proposed_changes"].items():
                if field not in AI_MUTABLE_FIELDS or not isinstance(change, dict):
                    continue
                new_value = change.get("to")
                old_value = customer.get(field)
                if old_value == new_value:
                    continue
                updates[field] = new_value
                audits.append(
                    {
                        "customer_id": customer["customer_id"],
                        "source_activity_id": proposal.get("activity_id"),
                        "field_name": field,
                        "old_value": None if old_value is None else str(old_value),
                        "new_value": None if new_value is None else str(new_value),
                        "changed_by": "relationship_manager_confirmed_ai",
                        "changed_at": now_iso,
                    }
                )

            if proposal["extraction_summary"] != customer.get("current_progress"):
                audits.append(
                    {
                        "customer_id": customer["customer_id"],
                        "source_activity_id": proposal.get("activity_id"),
                        "field_name": "current_progress",
                        "old_value": customer.get("current_progress"),
                        "new_value": proposal["extraction_summary"],
                        "changed_by": "relationship_manager_confirmed_ai",
                        "changed_at": now_iso,
                    }
                )

            proposed_stage = updates.get(
                "relationship_stage",
                customer.get("relationship_stage"),
            )
            if proposed_stage == "rejected":
                cooldown_until = to_iso(now + timedelta(days=30))
                updates["cooldown_until"] = cooldown_until
                updates["pinned"] = False
                if not updates.get("next_contact_at"):
                    updates["next_contact_at"] = cooldown_until
                if not updates.get("next_step"):
                    updates["next_step"] = (
                        "30 天冷静期结束后再做低打扰服务复核"
                    )
            elif customer.get("relationship_stage") == "rejected":
                updates["cooldown_until"] = None

            audited_fields = {item["field_name"] for item in audits}
            for field in (
                "cooldown_until",
                "pinned",
                "next_contact_at",
                "next_step",
            ):
                if field not in updates or field in audited_fields:
                    continue
                old_value = customer.get(field)
                new_value = updates.get(field)
                if old_value == new_value:
                    continue
                audits.append(
                    {
                        "customer_id": customer["customer_id"],
                        "source_activity_id": proposal.get("activity_id"),
                        "field_name": field,
                        "old_value": (
                            None if old_value is None else str(old_value)
                        ),
                        "new_value": (
                            None if new_value is None else str(new_value)
                        ),
                        "changed_by": "relationship_manager_confirmed_ai",
                        "changed_at": now_iso,
                    }
                )

            repository.update_customer(
                conn,
                customer["customer_id"],
                updates,
            )
            repository.insert_audits(conn, audits)

            if proposal.get("activity_id"):
                repository.update_activity(
                    conn,
                    int(proposal["activity_id"]),
                    {
                        "structured_summary": proposal["extraction_summary"],
                        "next_step": updates.get("next_step", customer.get("next_step")),
                        "next_contact_at": updates.get(
                            "next_contact_at",
                            customer.get("next_contact_at"),
                        ),
                        "stage_after": updates.get(
                            "relationship_stage",
                            customer.get("relationship_stage"),
                        ),
                        "intent_after": updates.get(
                            "intent_level",
                            customer.get("intent_level"),
                        ),
                    },
                )

            repository.update_change_proposal(
                conn,
                proposal_id,
                {
                    "status": "applied",
                    "reviewed_at": now_iso,
                    "applied_at": now_iso,
                    "reviewer_note": "客户经理确认全部候选变化",
                },
            )
            updated = repository.get_customer(conn, customer["customer_id"])
            assert updated is not None

        return {
            "proposal_id": proposal_id,
            "status": "applied",
            "customer": updated,
            "applied_changes": audits,
        }

    def reject_change_proposal(self, proposal_id: int) -> Dict[str, Any]:
        now_iso = to_iso(self._now()) or ""
        with transaction(self.db_path) as conn:
            proposal = repository.get_change_proposal(conn, proposal_id)
            if proposal is None:
                raise ProposalNotFoundError(proposal_id)
            if proposal["status"] != "pending":
                raise InvalidWorkStateError("该 Proposal 已经被处理")
            repository.update_change_proposal(
                conn,
                proposal_id,
                {
                    "status": "rejected",
                    "reviewed_at": now_iso,
                    "reviewer_note": "客户经理拒绝候选变化",
                },
            )
        return {"proposal_id": proposal_id, "status": "rejected"}

    def activity_feed(self, *, limit: int = 50) -> Dict[str, Any]:
        with connect(self.db_path) as conn:
            activities = repository.latest_activities(conn, limit=limit)
            proposals = repository.list_change_proposals(
                conn,
                status="pending",
                limit=50,
            )
            names = {
                customer["customer_id"]: customer["name"]
                for customer in repository.list_customers(conn)
            }
        for proposal in proposals:
            proposal["customer_name"] = names.get(
                proposal["customer_id"],
                proposal["customer_id"],
            )
        return {
            "activities": activities,
            "pending_proposals": proposals,
            "sync": self.sync.status(),
        }

    def refresh_sources(self) -> Dict[str, Any]:
        return self.sync.refresh(now=self._now())

    def sync_status(self) -> Dict[str, Any]:
        return self.sync.status()

    def advance_demo_time(
        self,
        *,
        days: int = 0,
        hours: int = 0,
    ) -> Dict[str, Any]:
        delta_seconds = days * 86400 + hours * 3600
        with transaction(self.db_path) as conn:
            current_raw = repository.get_demo_state(
                conn,
                "time_offset_seconds",
                "0",
            )
            try:
                current = int(current_raw)
            except ValueError:
                current = 0
            repository.set_demo_state(
                conn,
                "time_offset_seconds",
                str(current + delta_seconds),
            )
        return {
            "demo_time": to_iso(self._now()),
            "workbench": self.workbench(),
        }

    def reset_demo(self) -> Dict[str, Any]:
        reset_demo_data(self.db_path, now=self.clock())
        return self.workbench()
