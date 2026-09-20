from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List, Mapping, Optional

from .time_utils import parse_datetime, utc_now


@dataclass(frozen=True)
class DiscoveryFactor:
    code: str
    label: str
    points: int
    evidence: str


@dataclass(frozen=True)
class DiscoveryResult:
    score: int
    level: str
    follow_up_state: str
    actionable_reason: str
    factors: List[DiscoveryFactor]
    suggested_action: str
    pinned: bool
    compliance_note: str

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["factors"] = [asdict(item) for item in self.factors]
        return payload


def _days_since(value: Optional[str], now: datetime) -> Optional[float]:
    parsed = parse_datetime(value)
    if parsed is None:
        return None
    return (now - parsed).total_seconds() / 86400


def _hours_until(value: Optional[str], now: datetime) -> Optional[float]:
    parsed = parse_datetime(value)
    if parsed is None:
        return None
    return (parsed - now).total_seconds() / 3600


def _add(
    factors: List[DiscoveryFactor],
    code: str,
    label: str,
    points: int,
    evidence: str,
) -> None:
    if points:
        factors.append(
            DiscoveryFactor(
                code=code,
                label=label,
                points=points,
                evidence=evidence,
            )
        )


def _level(score: int) -> str:
    if score >= 65:
        return "high"
    if score >= 45:
        return "medium"
    return "low"


def evaluate_discovery(
    customer: Mapping[str, Any],
    now: Optional[datetime] = None,
) -> Optional[DiscoveryResult]:
    current = now or utc_now()
    factors: List[DiscoveryFactor] = []

    cooldown_until = parse_datetime(customer.get("cooldown_until"))
    if cooldown_until is not None and cooldown_until > current:
        return None

    stage = customer.get("relationship_stage") or "new"
    intent = customer.get("intent_level") or "unknown"
    pinned = bool(customer.get("pinned"))

    next_contact_hours = _hours_until(customer.get("next_contact_at"), current)
    last_contact_days = _days_since(customer.get("last_contact_at"), current)

    follow_up_state = "none"
    actionable_reason = ""
    suggested_action = ""
    primary_action_code = ""

    if (
        stage == "rejected"
        and cooldown_until is not None
        and cooldown_until <= current
    ):
        follow_up_state = "due"
        actionable_reason = "触达冷静期已结束，可以进行低打扰服务复核"
        suggested_action = "先做低打扰服务回访，确认客户近期需求是否发生变化；不要直接进入产品推介。"
        primary_action_code = "service_review_after_cooldown"
        _add(
            factors,
            primary_action_code,
            "冷静期结束",
            18,
            "已到可重新进行服务关系复核的时间",
        )
    elif next_contact_hours is not None:
        if next_contact_hours <= -24:
            follow_up_state = "overdue"
            overdue_days = max(1, int(abs(next_contact_hours) // 24))
            actionable_reason = f"约定回访已逾期约 {overdue_days} 天"
            suggested_action = "按原约定尽快回访，先确认客户当前需求是否发生变化。"
            primary_action_code = "follow_up_overdue"
            _add(
                factors,
                primary_action_code,
                "跟进已逾期",
                35,
                actionable_reason,
            )
        elif next_contact_hours <= 0:
            follow_up_state = "due"
            actionable_reason = "今天已到约定回访时间"
            suggested_action = "按约定回访，确认上次沟通事项的最新进展。"
            primary_action_code = "follow_up_due"
            _add(
                factors,
                primary_action_code,
                "约定跟进已到期",
                30,
                actionable_reason,
            )
        else:
            follow_up_state = "scheduled"

    recent_signal = (customer.get("recent_signal") or "").strip()
    if recent_signal and stage != "rejected":
        if not actionable_reason:
            actionable_reason = "出现新的客户经营信号"
            suggested_action = "先核实新信号背后的真实需求，再决定后续沟通。"
            primary_action_code = "new_signal"
        _add(
            factors,
            "new_signal",
            "新增经营信号",
            22,
            recent_signal,
        )

    if pinned and not actionable_reason:
        actionable_reason = "客户经理已主动标记为当前关注对象"
        suggested_action = customer.get("next_step") or "确认当前进展并推进下一步。"
        primary_action_code = "manual_focus"

    if (
        not actionable_reason
        and stage == "interested"
        and intent == "high"
        and next_contact_hours is None
    ):
        actionable_reason = "客户意向较高，但当前没有明确的下一次联系时间"
        suggested_action = (
            customer.get("next_step")
            if customer.get("next_step") and customer.get("next_step") != "按当前经营节奏继续跟进"
            else "明确下一步动作，并约定下一次联系时间。"
        )
        primary_action_code = "missing_follow_up_time"
        _add(
            factors,
            primary_action_code,
            "高意向但缺少跟进时间",
            24,
            actionable_reason,
        )

    if not actionable_reason and stage == "dormant":
        if last_contact_days is not None and last_contact_days >= 30:
            actionable_reason = "较长时间没有有效互动"
            suggested_action = "以服务回访重新确认需求，不以成交为唯一目标。"
            primary_action_code = "service_review"
            _add(
                factors,
                primary_action_code,
                "服务关系需要复核",
                18,
                f"距离上次联系约 {int(last_contact_days)} 天",
            )

    if not actionable_reason:
        return None

    # 已有明确未来约定时，除非出现新信号或人工置顶，否则不提前打扰。
    if (
        follow_up_state == "scheduled"
        and primary_action_code not in {"new_signal", "manual_focus"}
    ):
        return None

    # 最近刚有效联系时，没有新的到期约定/新信号就抑制重复触达。
    if (
        last_contact_days is not None
        and 0 <= last_contact_days < 1
        and primary_action_code not in {"follow_up_due", "follow_up_overdue", "new_signal"}
        and not pinned
    ):
        return None

    intent_points = {"high": 20, "medium": 10, "low": 2, "unknown": 0}.get(intent, 0)
    _add(
        factors,
        "intent",
        "当前意向",
        intent_points,
        {
            "high": "当前意向较明确",
            "medium": "仍存在继续沟通空间",
            "low": "当前意向较低",
        }.get(intent, "暂无明确意向"),
    )

    stage_points = {
        "interested": 12,
        "considering": 8,
        "contacted": 5,
        "new": 4,
        "dormant": 0,
        "rejected": -20,
    }.get(stage, 0)
    _add(
        factors,
        "relationship_stage",
        "当前关系阶段",
        stage_points,
        {
            "interested": "客户已表达明确兴趣",
            "considering": "客户仍在考虑",
            "contacted": "已有有效沟通基础",
            "new": "仍需完成首次有效需求了解",
            "rejected": "近期明确拒绝，应降低主动触达",
        }.get(stage, "当前阶段"),
    )

    value_points = {"钻石": 8, "铂金": 6, "金卡": 4}.get(
        customer.get("customer_level"),
        0,
    )
    _add(
        factors,
        "service_value",
        "客户服务价值",
        value_points,
        f"客户等级：{customer.get('customer_level') or '普通'}；仅作轻权重辅助",
    )

    score = max(0, min(100, sum(item.points for item in factors)))
    return DiscoveryResult(
        score=score,
        level=_level(score),
        follow_up_state=follow_up_state,
        actionable_reason=actionable_reason,
        factors=factors,
        suggested_action=suggested_action,
        pinned=pinned,
        compliance_note="该排序仅用于安排客户经理工作顺序，不代表成交概率或投资建议。",
    )
