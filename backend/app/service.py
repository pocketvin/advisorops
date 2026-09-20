from datetime import timedelta
from typing import Any, Dict, List, Mapping, Optional

from . import repository
from .db import PathLike
from .priority import evaluate_priority
from .seed import ensure_seeded, reset_demo_data
from .time_utils import to_iso, utc_now


class CustomerNotFoundError(KeyError):
    pass


class WorkbenchService:
    def __init__(self, db_path: Optional[PathLike] = None) -> None:
        self.db_path = db_path
        ensure_seeded(self.db_path)

    def _get(self, customer_id: str) -> Dict[str, Any]:
        customer = repository.get_customer(customer_id, self.db_path)
        if customer is None:
            raise CustomerNotFoundError(customer_id)
        return customer

    def _decorate(self, customer: Mapping[str, Any]) -> Dict[str, Any]:
        priority = evaluate_priority(customer)
        return {"customer": dict(customer), "priority": priority.to_dict()}

    def workbench(self, limit: int = 12) -> Dict[str, Any]:
        decorated = [self._decorate(item) for item in repository.list_customers(self.db_path)]
        decorated.sort(
            key=lambda item: (
                bool(item["customer"].get("pinned")),
                item["priority"]["score"],
                item["customer"].get("next_contact_at") or "9999",
            ),
            reverse=True,
        )
        items = decorated[: max(1, min(limit, 50))]
        return {
            "summary": {
                "total_customers": len(decorated),
                "high_priority": sum(1 for item in decorated if item["priority"]["level"] == "high"),
                "follow_up_due": sum(
                    1 for item in decorated if item["priority"]["effective_stage"] == "follow_up_due"
                ),
                "pinned": sum(1 for item in decorated if item["customer"].get("pinned")),
            },
            "items": items,
        }

    def list_customers(
        self,
        search: str = "",
        stage: str = "",
        risk_level: str = "",
        intent: str = "",
        customer_level: str = "",
    ) -> List[Dict[str, Any]]:
        search_norm = search.strip().lower()
        results: List[Dict[str, Any]] = []
        for customer in repository.list_customers(self.db_path):
            decorated = self._decorate(customer)
            effective_stage = decorated["priority"]["effective_stage"]
            if search_norm and search_norm not in (
                f"{customer['name']} {customer['customer_id']} {customer.get('manager_note', '')}".lower()
            ):
                continue
            if stage and effective_stage != stage:
                continue
            if risk_level and customer.get("risk_level") != risk_level:
                continue
            if intent and customer.get("intent") != intent:
                continue
            if customer_level and customer.get("customer_level") != customer_level:
                continue
            results.append(decorated)
        results.sort(
            key=lambda item: (
                bool(item["customer"].get("pinned")),
                item["priority"]["score"],
            ),
            reverse=True,
        )
        return results

    def detail(self, customer_id: str) -> Dict[str, Any]:
        customer = self._get(customer_id)
        decorated = self._decorate(customer)
        decorated["timeline"] = repository.list_timeline(customer_id, self.db_path)
        return decorated

    def set_pin(self, customer_id: str, pinned: bool) -> Dict[str, Any]:
        customer = self._get(customer_id)
        now = utc_now()
        repository.update_customer(
            customer_id,
            {
                "pinned": pinned,
                "pinned_at": to_iso(now) if pinned else None,
                "updated_at": to_iso(now),
            },
            self.db_path,
        )
        repository.add_timeline_event(
            {
                "customer_id": customer_id,
                "event_type": "manual_priority",
                "title": "人工置顶" if pinned else "取消置顶",
                "detail": "客户经理手动调整当前工作关注顺序。",
                "feedback": "",
                "stage_after": customer["stage"],
                "next_contact_at": customer.get("next_contact_at"),
                "metadata": {"pinned": pinned},
                "created_at": to_iso(now),
            },
            self.db_path,
        )
        return self.detail(customer_id)

    def reject(
        self,
        customer_id: str,
        feedback: str,
        cooldown_days: int = 30,
    ) -> Dict[str, Any]:
        customer = self._get(customer_id)
        now = utc_now()
        measures = list(customer.get("measures") or [])
        measures.append("记录客户明确拒绝")
        next_contact = now + timedelta(days=max(1, min(cooldown_days, 180)))
        repository.update_customer(
            customer_id,
            {
                "stage": "rejected",
                "intent": "low",
                "last_feedback": feedback.strip() or "客户近期明确表示暂无需求。",
                "last_contact_at": to_iso(now),
                "historical_contact_count": int(customer.get("historical_contact_count") or 0) + 1,
                "measures": measures[-8:],
                "next_step": "进入冷静期，后续仅做必要服务维护",
                "next_contact_at": to_iso(next_contact),
                "pinned": False,
                "pinned_at": None,
                "updated_at": to_iso(now),
            },
            self.db_path,
        )
        repository.add_timeline_event(
            {
                "customer_id": customer_id,
                "event_type": "contact",
                "title": "客户明确拒绝",
                "detail": f"进入 {max(1, min(cooldown_days, 180))} 天冷静期，避免短期重复触达。",
                "feedback": feedback.strip(),
                "stage_after": "rejected",
                "next_contact_at": to_iso(next_contact),
                "metadata": {"cooldown_days": cooldown_days},
                "created_at": to_iso(now),
            },
            self.db_path,
        )
        return self.detail(customer_id)

    def mark_considering(
        self,
        customer_id: str,
        feedback: str,
        follow_up_days: int = 3,
    ) -> Dict[str, Any]:
        customer = self._get(customer_id)
        now = utc_now()
        days = max(1, min(follow_up_days, 90))
        next_contact = now + timedelta(days=days)
        measures = list(customer.get("measures") or [])
        measures.append(f"约定 {days} 天后回访")
        current_intent = customer.get("intent") or "unknown"
        intent = "medium" if current_intent in {"unknown", "low"} else current_intent
        repository.update_customer(
            customer_id,
            {
                "stage": "considering",
                "intent": intent,
                "last_feedback": feedback.strip() or f"客户表示再考虑 {days} 天。",
                "last_contact_at": to_iso(now),
                "historical_contact_count": int(customer.get("historical_contact_count") or 0) + 1,
                "measures": measures[-8:],
                "next_step": f"{days} 天后按约定回访",
                "next_contact_at": to_iso(next_contact),
                "updated_at": to_iso(now),
            },
            self.db_path,
        )
        repository.add_timeline_event(
            {
                "customer_id": customer_id,
                "event_type": "contact",
                "title": "客户表示再考虑",
                "detail": f"已约定 {days} 天后再次联系；到期前降低工作优先级。",
                "feedback": feedback.strip(),
                "stage_after": "considering",
                "next_contact_at": to_iso(next_contact),
                "metadata": {"follow_up_days": days},
                "created_at": to_iso(now),
            },
            self.db_path,
        )
        return self.detail(customer_id)

    def record_follow_up(self, customer_id: str, payload: Mapping[str, Any]) -> Dict[str, Any]:
        customer = self._get(customer_id)
        now = utc_now()
        action = str(payload.get("action") or "完成一次客户跟进").strip()
        feedback = str(payload.get("feedback") or "").strip()
        stage = str(payload.get("stage") or customer["stage"])
        intent = str(payload.get("intent") or customer["intent"])
        next_step = str(payload.get("next_step") or "").strip()
        next_contact_at = payload.get("next_contact_at")
        contact_method = str(payload.get("contact_method") or customer.get("contact_method") or "电话")
        measures = list(customer.get("measures") or [])
        measures.append(action)

        repository.update_customer(
            customer_id,
            {
                "stage": stage,
                "intent": intent,
                "last_feedback": feedback,
                "last_contact_at": to_iso(now),
                "contact_method": contact_method,
                "historical_contact_count": int(customer.get("historical_contact_count") or 0) + 1,
                "measures": measures[-8:],
                "next_step": next_step,
                "next_contact_at": next_contact_at or None,
                "updated_at": to_iso(now),
            },
            self.db_path,
        )
        repository.add_timeline_event(
            {
                "customer_id": customer_id,
                "event_type": "contact",
                "title": action,
                "detail": next_step,
                "feedback": feedback,
                "stage_after": stage,
                "next_contact_at": next_contact_at or None,
                "metadata": {"contact_method": contact_method, "intent": intent},
                "created_at": to_iso(now),
            },
            self.db_path,
        )
        return self.detail(customer_id)

    def add_behavior_signal(
        self,
        customer_id: str,
        asset_change_30d_pct: Optional[float] = None,
        recent_product_interest: Optional[str] = None,
        recent_consult_topic: Optional[str] = None,
    ) -> Dict[str, Any]:
        customer = self._get(customer_id)
        now = utc_now()
        updates: Dict[str, Any] = {"updated_at": to_iso(now)}
        detail_parts: List[str] = []
        if asset_change_30d_pct is not None:
            updates["asset_change_30d_pct"] = float(asset_change_30d_pct)
            detail_parts.append(f"近30日资产变化 {float(asset_change_30d_pct):+.1f}%")
        if recent_product_interest is not None:
            updates["recent_product_interest"] = recent_product_interest.strip()
            if recent_product_interest.strip():
                detail_parts.append(f"新增关注：{recent_product_interest.strip()}")
        if recent_consult_topic is not None:
            updates["recent_consult_topic"] = recent_consult_topic.strip()
            if recent_consult_topic.strip():
                detail_parts.append(f"咨询主题：{recent_consult_topic.strip()}")
        repository.update_customer(customer_id, updates, self.db_path)
        repository.add_timeline_event(
            {
                "customer_id": customer_id,
                "event_type": "behavior_signal",
                "title": "客户行为信号更新",
                "detail": "；".join(detail_parts) or "更新近期行为信号。",
                "feedback": "",
                "stage_after": customer["stage"],
                "next_contact_at": customer.get("next_contact_at"),
                "metadata": {"source": "demo_simulation"},
                "created_at": to_iso(now),
            },
            self.db_path,
        )
        return self.detail(customer_id)

    def reset_demo(self) -> Dict[str, Any]:
        reset_demo_data(self.db_path)
        return self.workbench()
