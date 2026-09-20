from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List, Mapping, Optional

from .time_utils import parse_datetime, utc_now


@dataclass(frozen=True)
class PriorityFactor:
    code: str
    label: str
    points: int
    evidence: str


@dataclass(frozen=True)
class PriorityResult:
    score: int
    level: str
    effective_stage: str
    factors: List[PriorityFactor]
    next_best_action: str
    suitability_check_required: bool
    compliance_note: str

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["factors"] = [asdict(item) for item in self.factors]
        return payload


INTENT_POINTS = {"high": 25, "medium": 15, "low": 5, "unknown": 0}
STAGE_POINTS = {
    "new": 8,
    "contacted": 5,
    "interested": 15,
    "considering": 8,
    "follow_up_due": 18,
    "rejected": -45,
    "dormant": -8,
}
LEVEL_LABELS = {"high": "高", "medium": "中", "low": "低"}


def _add(
    factors: List[PriorityFactor],
    code: str,
    label: str,
    points: int,
    evidence: str,
) -> None:
    if points:
        factors.append(PriorityFactor(code=code, label=label, points=points, evidence=evidence))


def _hours_until(value: Optional[str], now: datetime) -> Optional[float]:
    parsed = parse_datetime(value)
    if parsed is None:
        return None
    return (parsed - now).total_seconds() / 3600


def _days_since(value: Optional[str], now: datetime) -> Optional[float]:
    parsed = parse_datetime(value)
    if parsed is None:
        return None
    return (now - parsed).total_seconds() / 86400


def _priority_level(score: int) -> str:
    if score >= 70:
        return "high"
    if score >= 40:
        return "medium"
    return "low"


def _next_best_action(
    customer: Mapping[str, Any],
    effective_stage: str,
    due: bool,
    behavior_signal: bool,
) -> tuple:
    feedback = (customer.get("last_feedback") or "").strip()
    if effective_stage == "rejected":
        return (
            "进入冷静期，保留服务关系，暂不进行主动营销触达。",
            False,
        )
    if due:
        if "考虑" in feedback or customer.get("stage") == "considering":
            return (
                "按上次约定回访，先确认客户考虑结果和当前需求是否发生变化。",
                False,
            )
        return ("完成到期回访，先确认客户当前需求与上次沟通是否一致。", False)
    if effective_stage == "interested":
        return (
            "继续澄清投资目标、期限和风险承受能力；如进入具体产品讨论，先完成适当性核验。",
            True,
        )
    if behavior_signal:
        return (
            "先核实近期资产或关注行为变化背后的真实需求，再决定是否进入后续沟通。",
            False,
        )
    if effective_stage == "considering":
        return (
            "按约定时间等待，不提前反复打扰；到期后系统会自动把客户重新前移。",
            False,
        )
    if effective_stage == "dormant":
        return ("以服务回访重新确认需求，不以成交为唯一目标。", False)
    if effective_stage == "new":
        return ("先完成首次需求了解，补齐客户目标、期限和风险偏好信息。", False)
    return ("继续维护当前沟通进度，并明确下一次可执行的跟进动作。", False)


def evaluate_priority(
    customer: Mapping[str, Any],
    now: Optional[datetime] = None,
) -> PriorityResult:
    current = now or utc_now()
    factors: List[PriorityFactor] = []

    stage = customer.get("stage") or "new"
    intent = customer.get("intent") or "unknown"
    hours_until_follow_up = _hours_until(customer.get("next_contact_at"), current)
    due = bool(
        stage != "rejected"
        and hours_until_follow_up is not None
        and hours_until_follow_up <= 0
    )
    effective_stage = "follow_up_due" if due else stage

    intent_points = INTENT_POINTS.get(intent, 0)
    _add(
        factors,
        "intent",
        "客户当前意向",
        intent_points,
        {"high": "当前意向较明确", "medium": "存在继续沟通空间", "low": "当前意向较低"}.get(intent, "暂无明确意向"),
    )

    if hours_until_follow_up is not None:
        if due and hours_until_follow_up <= -24:
            overdue_days = max(1, int(abs(hours_until_follow_up) // 24))
            _add(factors, "follow_up_overdue", "约定跟进已逾期", 25, f"已超过约定时间约 {overdue_days} 天")
        elif due:
            _add(factors, "follow_up_due", "约定跟进已到期", 20, "现在已到约定回访时间")
        elif hours_until_follow_up <= 24:
            _add(factors, "follow_up_soon", "即将到跟进时间", 10, "24 小时内需要回访")
        elif hours_until_follow_up <= 24 * 7:
            _add(factors, "follow_up_not_due", "尚未到约定时间", -5, "已有明确后续时间，暂不需要提前打扰")
        else:
            _add(factors, "follow_up_later", "跟进时间较远", -10, "近期无需重复联系")

    stage_points = STAGE_POINTS.get(effective_stage, 0)
    stage_evidence = {
        "new": "仍需完成首次有效需求了解",
        "contacted": "已有沟通基础",
        "interested": "客户已表达明确需求或兴趣",
        "considering": "客户处于考虑阶段",
        "follow_up_due": "客户已进入到期回访窗口",
        "rejected": "近期已明确拒绝，应降低打扰频率",
        "dormant": "近期缺少有效互动",
    }.get(effective_stage, "当前阶段")
    _add(factors, "stage", "当前沟通阶段", stage_points, stage_evidence)

    behavior_signal = False
    asset_change = float(customer.get("asset_change_30d_pct") or 0)
    if asset_change >= 10:
        behavior_signal = True
        _add(factors, "asset_increase", "近期资产明显增加", 15, f"近 30 日资产变化 +{asset_change:.1f}%")
    elif asset_change >= 5:
        behavior_signal = True
        _add(factors, "asset_increase", "近期资产有所增加", 8, f"近 30 日资产变化 +{asset_change:.1f}%")
    elif asset_change <= -10:
        behavior_signal = True
        _add(factors, "asset_outflow", "近期资产明显下降", 12, f"近 30 日资产变化 {asset_change:.1f}%，需要先核实原因")

    login_days = _days_since(customer.get("last_login_at"), current)
    if login_days is not None and 0 <= login_days <= 2:
        behavior_signal = True
        _add(factors, "recent_login", "近期活跃", 5, "2 天内有登录行为")

    trade_days = _days_since(customer.get("last_trade_at"), current)
    if trade_days is not None and 0 <= trade_days <= 3:
        behavior_signal = True
        _add(factors, "recent_trade", "近期有交易行为", 5, "3 天内有交易记录")

    if (customer.get("recent_product_interest") or "").strip():
        behavior_signal = True
        _add(factors, "product_interest", "出现新的关注主题", 6, str(customer.get("recent_product_interest")))

    if (customer.get("recent_consult_topic") or "").strip():
        _add(factors, "consult_topic", "近期有咨询主题", 4, str(customer.get("recent_consult_topic")))

    value_points = {"钻石": 8, "铂金": 6, "金卡": 4}.get(customer.get("customer_level"), 0)
    _add(
        factors,
        "customer_value",
        "客户服务价值",
        value_points,
        f"客户等级：{customer.get('customer_level') or '普通'}；仅作为轻权重辅助",
    )

    if bool(customer.get("pinned")):
        _add(factors, "manual_pin", "客户经理人工置顶", 100, "客户经理已主动确认当前为重点经营对象")

    last_contact_days = _days_since(customer.get("last_contact_at"), current)
    if not due and stage != "rejected" and last_contact_days is not None and last_contact_days >= 0:
        if last_contact_days <= 1:
            _add(factors, "contact_cooldown", "近期刚联系", -18, "24 小时内已联系，避免高频打扰")
        elif last_contact_days <= 3:
            _add(factors, "contact_cooldown", "近期已联系", -10, "3 天内已有沟通，且尚未到新的约定回访时间")

    raw_score = sum(item.points for item in factors)
    score = max(0, min(200, raw_score))
    level = _priority_level(score)
    next_action, suitability_required = _next_best_action(
        customer=customer,
        effective_stage=effective_stage,
        due=due,
        behavior_signal=behavior_signal,
    )

    return PriorityResult(
        score=score,
        level=level,
        effective_stage=effective_stage,
        factors=factors,
        next_best_action=next_action,
        suitability_check_required=suitability_required,
        compliance_note="该优先级仅用于安排客户经理工作顺序，不代表成交概率或投资建议。",
    )
