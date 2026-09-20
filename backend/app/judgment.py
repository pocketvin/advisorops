from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List, Mapping, Optional, Sequence

from .time_utils import to_iso


STAGE_LABELS = {
    "new": "新客户",
    "contacted": "已联系",
    "interested": "有明确兴趣",
    "considering": "考虑中",
    "rejected": "近期明确拒绝",
    "dormant": "长期沉默",
}

INTENT_LABELS = {
    "unknown": "意向待确认",
    "low": "低意向",
    "medium": "中意向",
    "high": "高意向",
}

WAITING_LABELS = {
    "customer": "正在等待客户反馈",
    "manager": "下一步在客户经理侧",
    "internal": "正在等待内部资料或支持",
    "scheduled_time": "正在等待约定时间",
}


@dataclass(frozen=True)
class JudgmentEvidence:
    source: str
    text: str
    kind: str = "confirmed"
    activity_id: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class JudgmentItem:
    text: str
    evidence: List[JudgmentEvidence]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "evidence": [item.to_dict() for item in self.evidence],
        }


@dataclass(frozen=True)
class ActionBrief:
    mode: str
    objective: str
    questions: List[str]
    completion_criteria: str
    opening_line: str
    evidence: List[JudgmentEvidence]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode,
            "objective": self.objective,
            "questions": list(self.questions),
            "completion_criteria": self.completion_criteria,
            "opening_line": self.opening_line,
            "evidence": [item.to_dict() for item in self.evidence],
        }


def _text(value: Any) -> str:
    return str(value or "").strip()


def _profile(customer: Mapping[str, Any], section: str) -> Mapping[str, Any]:
    profile = customer.get("profile")
    if not isinstance(profile, Mapping):
        return {}
    value = profile.get(section)
    return value if isinstance(value, Mapping) else {}


def _first_list_value(value: Any) -> str:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return ""
    for item in value:
        text = _text(item)
        if text:
            return text
    return ""


def _latest_interaction(
    activities: Sequence[Mapping[str, Any]],
) -> Optional[Mapping[str, Any]]:
    for activity in activities:
        if activity.get("activity_type") != "interaction":
            continue
        if (
            _text(activity.get("structured_summary"))
            or _text(activity.get("customer_feedback"))
            or _text(activity.get("raw_content"))
        ):
            return activity
    return None


def _latest_activity_evidence(
    activities: Sequence[Mapping[str, Any]],
) -> Optional[JudgmentEvidence]:
    activity = _latest_interaction(activities)
    if activity is None:
        return None
    content = (
        _text(activity.get("customer_feedback"))
        or _text(activity.get("structured_summary"))
        or _text(activity.get("raw_content"))
    )
    return JudgmentEvidence(
        source="最近沟通",
        text=content,
        activity_id=int(activity["id"]) if activity.get("id") is not None else None,
    )


def _current_state(
    customer: Mapping[str, Any],
    active_work: Optional[Mapping[str, Any]],
    activities: Sequence[Mapping[str, Any]],
) -> JudgmentItem:
    stage = _text(customer.get("relationship_stage")) or "new"
    intent = _text(customer.get("intent_level")) or "unknown"
    state = f"{STAGE_LABELS.get(stage, stage)} · {INTENT_LABELS.get(intent, intent)}"

    evidence = [
        JudgmentEvidence(
            source="当前状态",
            text=(
                f"关系阶段：{STAGE_LABELS.get(stage, stage)}；"
                f"当前意向：{INTENT_LABELS.get(intent, intent)}"
            ),
        )
    ]

    if active_work:
        status = _text(active_work.get("status"))
        waiting_on = _text(active_work.get("waiting_on"))
        if status == "waiting":
            work_text = WAITING_LABELS.get(waiting_on, "当前工作项处于等待中")
            state += f"；{work_text}"
        elif status == "action_required":
            state += "；下一步动作在客户经理侧"
        evidence.append(
            JudgmentEvidence(
                source="当前工作项",
                text=(
                    _text(active_work.get("current_progress"))
                    or _text(active_work.get("title"))
                    or "存在进行中的客户经营工作"
                ),
            )
        )
    else:
        latest = _latest_activity_evidence(activities)
        if latest:
            evidence.append(latest)

    return JudgmentItem(text=state, evidence=evidence[:3])


def _core_concern(
    customer: Mapping[str, Any],
    activities: Sequence[Mapping[str, Any]],
) -> JudgmentItem:
    need = _text(customer.get("current_need"))
    investment = _profile(customer, "investment_context")
    financial = _profile(customer, "financial_context")
    family = _profile(customer, "family_and_life")

    goal = _text(investment.get("primary_goal"))
    liquidity = _text(financial.get("liquidity_preference"))
    major_plan = _text(family.get("major_plan"))

    stage = _text(customer.get("relationship_stage"))
    if stage == "rejected" or need == "暂无主动经营需求":
        text = "当前没有主动经营需求；核心是尊重触达边界并等待合适的服务复核时机"
    elif need and need != "待确认":
        text = need
    elif goal:
        text = f"围绕“{goal}”确认真实资金目标和优先级"
    elif major_plan:
        text = f"先理解“{major_plan}”对资金安排的影响"
    else:
        text = "当前核心需求尚未明确，下一步应先完成需求确认"

    evidence: List[JudgmentEvidence] = []
    if need:
        evidence.append(JudgmentEvidence(source="当前需求", text=need))
    if goal:
        evidence.append(JudgmentEvidence(source="投资目标", text=goal))
    if liquidity:
        evidence.append(
            JudgmentEvidence(
                source="流动性偏好",
                text=f"客户当前流动性偏好：{liquidity}",
            )
        )
    if major_plan:
        evidence.append(JudgmentEvidence(source="未来安排", text=major_plan))
    latest = _latest_activity_evidence(activities)
    if latest and len(evidence) < 3:
        evidence.append(latest)

    return JudgmentItem(text=text, evidence=evidence[:3])


def _decision_barrier(
    customer: Mapping[str, Any],
    active_work: Optional[Mapping[str, Any]],
    activities: Sequence[Mapping[str, Any]],
) -> JudgmentItem:
    obstacle = _text(customer.get("current_obstacle"))
    relationship = _profile(customer, "relationship_context")
    concern = _first_list_value(relationship.get("key_concerns"))

    hypotheses = customer.get("profile_hypotheses")
    hypothesis = None
    if isinstance(hypotheses, Sequence) and not isinstance(hypotheses, (str, bytes)):
        for item in hypotheses:
            if isinstance(item, Mapping) and _text(item.get("value")):
                hypothesis = item
                break

    evidence: List[JudgmentEvidence] = []
    if obstacle:
        text = obstacle
        evidence.append(JudgmentEvidence(source="当前障碍", text=obstacle))
    elif active_work and _text(active_work.get("status")) == "waiting":
        waiting_on = _text(active_work.get("waiting_on"))
        text = WAITING_LABELS.get(waiting_on, "本轮推进仍在等待外部条件")
        evidence.append(
            JudgmentEvidence(
                source="当前工作项",
                text=_text(active_work.get("current_progress")) or text,
            )
        )
    elif concern:
        text = f"暂无明确阻塞；沟通中需要重点验证客户对“{concern}”的顾虑"
        evidence.append(JudgmentEvidence(source="主要顾虑", text=concern))
    elif hypothesis is not None:
        hypothesis_text = _text(hypothesis.get("value"))
        text = f"暂无明确阻塞；可继续验证“{hypothesis_text}”是否影响决策"
        evidence.append(
            JudgmentEvidence(
                source="待验证假设",
                text=hypothesis_text,
                kind="hypothesis",
            )
        )
    else:
        text = "暂无明确决策障碍；不要为了补字段而假设客户存在异议"

    latest = _latest_activity_evidence(activities)
    if latest and len(evidence) < 2:
        evidence.append(latest)

    if hypothesis is not None and all(item.kind != "hypothesis" for item in evidence):
        evidence.append(
            JudgmentEvidence(
                source="待验证假设",
                text=_text(hypothesis.get("value")),
                kind="hypothesis",
            )
        )

    return JudgmentItem(text=text, evidence=evidence[:3])


def _next_confirmation(
    customer: Mapping[str, Any],
    active_work: Optional[Mapping[str, Any]],
) -> JudgmentItem:
    stage = _text(customer.get("relationship_stage"))
    need = _text(customer.get("current_need"))
    next_step = _text(customer.get("next_step"))
    lower = need.casefold()

    evidence: List[JudgmentEvidence] = []
    if need:
        evidence.append(JudgmentEvidence(source="当前需求", text=need))
    if next_step:
        evidence.append(JudgmentEvidence(source="已安排下一步", text=next_step))
    if active_work:
        work_next = _text(active_work.get("next_action"))
        if work_next and work_next != next_step:
            evidence.append(JudgmentEvidence(source="当前工作项", text=work_next))

    if stage == "rejected":
        text = "先确认客户是否愿意恢复低打扰的服务沟通，不直接进入产品讨论"
    elif any(word in lower for word in ("流动性", "资金", "期限", "现金流", "配置")):
        text = "优先确认资金用途、使用时间和流动性边界，再判断后续沟通深度"
    elif any(word in lower for word in ("家庭", "子女", "养老", "退休")):
        text = "确认家庭目标对应的时间点、资金责任和实际决策参与者"
    elif any(word in lower for word in ("资料", "反馈", "考虑", "确认")):
        text = "确认客户对已沟通内容的真实反馈、仍未解决的问题和是否愿意继续推进"
    elif stage == "new":
        text = "先确认主要资金目标、使用期限、风险边界和当前最关心的问题"
    elif next_step:
        text = f"围绕“{next_step}”确认客户最新变化，不重复上一轮已经确认的信息"
    else:
        text = "先确认当前最重要的资金目标和下一次可执行动作"

    return JudgmentItem(text=text, evidence=evidence[:3])


def _action_brief(
    customer: Mapping[str, Any],
    active_work: Optional[Mapping[str, Any]],
) -> ActionBrief:
    stage = _text(customer.get("relationship_stage"))
    need = _text(customer.get("current_need"))
    next_step = _text(customer.get("next_step"))
    lower = need.casefold()

    work_status = _text(active_work.get("status")) if active_work else ""
    waiting_on = _text(active_work.get("waiting_on")) if active_work else ""
    work_next = _text(active_work.get("next_action")) if active_work else ""

    evidence: List[JudgmentEvidence] = []
    if need:
        evidence.append(JudgmentEvidence(source="当前需求", text=need))
    if work_next:
        evidence.append(JudgmentEvidence(source="当前工作项", text=work_next))
    elif next_step:
        evidence.append(JudgmentEvidence(source="已安排下一步", text=next_step))

    if stage == "rejected":
        return ActionBrief(
            mode="wait",
            objective="暂不主动营销触达；冷静期结束后再做低打扰服务复核",
            questions=[
                "近期是否愿意恢复必要的服务沟通？",
                "近期资金安排或服务需求是否发生了变化？",
            ],
            completion_criteria="只确认是否愿意恢复沟通和是否出现新需求；若仍不愿意，继续保持低打扰。",
            opening_line="如果后续恢复服务沟通，先从近期资金安排有没有变化开始，不直接进入产品讨论。",
            evidence=evidence[:3],
        )

    if work_status == "waiting" and waiting_on in {"customer", "scheduled_time"}:
        objective = work_next or next_step or "等待客户反馈或约定时间"
        return ActionBrief(
            mode="wait",
            objective=objective,
            questions=[],
            completion_criteria="等到客户回复或约定时间后，再根据最新反馈决定是否继续推进；当前不重复催促。",
            opening_line="当前不建议主动重新开场；等客户回复或到约定时间后，从上次未解决的问题继续。",
            evidence=evidence[:3],
        )

    if work_status == "waiting" and waiting_on == "internal":
        objective = work_next or next_step or "补齐内部资料后再联系客户"
        return ActionBrief(
            mode="prepare",
            objective=objective,
            questions=[],
            completion_criteria="先把内部资料或支持准备完整，再一次性回到客户问题，避免反复补充。",
            opening_line="资料准备齐全后，从客户上次明确的问题继续，不需要重新做需求开场。",
            evidence=evidence[:3],
        )

    if any(word in lower for word in ("流动性", "资金", "期限", "现金流", "配置")):
        questions = [
            "这笔资金大概什么时候可能需要使用？",
            "哪些资金必须保持随时可用或短期可用？",
            "剩余资金可以接受多长的使用期限？",
        ]
        objective = work_next or next_step or "确认资金用途、使用时间和流动性边界"
        criteria = "至少确认资金用途、时间范围和流动性要求，再决定是否进入后续配置讨论。"
        opening = "上次我们聊到资金使用安排，我想再确认一下，您近期有没有比较明确的用款时间，或者需要提前预留的部分？"
    elif any(word in lower for word in ("家庭", "子女", "养老", "退休")):
        questions = [
            "这个目标大概对应什么时间点？",
            "需要承担的资金责任大概是什么范围？",
            "这次安排还有谁会一起参与决策？",
        ]
        objective = work_next or next_step or "确认家庭目标、时间点和实际资金责任"
        criteria = "把家庭目标对应的时间、资金责任和主要决策参与者确认到可继续推进的程度。"
        opening = "上次提到家庭这边的安排，我想再确认一下，现在时间点和资金需求有没有更明确一些？"
    elif any(word in lower for word in ("资料", "反馈", "考虑", "确认")):
        questions = [
            "上次沟通或资料里，哪些部分已经比较清楚？",
            "现在还有什么问题或顾虑没有解决？",
            "如果继续推进，下一步您更希望先确认什么？",
        ]
        objective = work_next or next_step or "确认客户真实反馈和未解决问题"
        criteria = "明确客户是否愿意继续推进、当前未解决问题，以及双方认可的下一步。"
        opening = "上次聊的内容您大概看过了吗？我更想先听听，现在哪些地方还没解决您的顾虑。"
    elif stage == "new":
        questions = [
            "近期最重要的资金目标是什么？",
            "这笔资金大概多久不会使用？",
            "对波动和流动性最在意哪一项？",
        ]
        objective = work_next or next_step or "完成第一次有效需求了解"
        criteria = "至少确认主要资金目标、使用期限和风险/流动性边界，并形成明确下一步。"
        opening = "我先不急着聊具体方案，想先了解一下，您近期最希望解决的资金问题是什么？"
    else:
        questions = [
            "上次沟通以后，您的情况有没有新的变化？",
            "目前最需要先解决的是什么？",
            "我们下一步具体做到什么程度比较合适？",
        ]
        objective = work_next or next_step or "确认当前变化并形成明确下一步"
        criteria = "确认最新需求变化，并约定一个具体、可执行的下一步和时间。"
        opening = "我想沿着上次聊到的事情确认一下，您这边最近有没有新的变化？"

    return ActionBrief(
        mode="contact",
        objective=objective,
        questions=questions,
        completion_criteria=criteria,
        opening_line=opening,
        evidence=evidence[:3],
    )


def _communication_approach(
    customer: Mapping[str, Any],
    active_work: Optional[Mapping[str, Any]],
) -> JudgmentItem:
    service = _profile(customer, "service_preferences")
    relationship = _profile(customer, "relationship_context")

    stage = _text(customer.get("relationship_stage"))
    channel = _text(service.get("preferred_channel"))
    time = _text(service.get("preferred_contact_time"))
    style = _text(service.get("communication_style"))
    trust = _first_list_value(relationship.get("trust_factors"))

    parts: List[str] = []
    if channel:
        parts.append(f"优先使用{channel}")
    if time:
        parts.append(f"尽量在{time}联系")
    if style:
        parts.append(style)
    if trust:
        parts.append(f"沟通时注意“{trust}”")

    preference_text = (
        "；".join(parts)
        if parts
        else "按照客户最近有效的沟通方式推进，先确认需求再展开讨论"
    )
    if stage == "rejected":
        text = f"冷静期内不主动营销触达；后续若恢复服务沟通，{preference_text}"
    elif (
        active_work
        and _text(active_work.get("status")) == "waiting"
        and _text(active_work.get("waiting_on")) in {"customer", "scheduled_time"}
    ):
        text = f"当前先等待客户/约定时间；需要再次联系时，{preference_text}"
    else:
        text = preference_text

    evidence: List[JudgmentEvidence] = []
    if channel:
        evidence.append(JudgmentEvidence(source="偏好渠道", text=channel))
    if time:
        evidence.append(JudgmentEvidence(source="偏好联系时间", text=time))
    if style:
        evidence.append(JudgmentEvidence(source="沟通偏好", text=style))
    if trust and len(evidence) < 3:
        evidence.append(JudgmentEvidence(source="信任因素", text=trust))

    return JudgmentItem(text=text, evidence=evidence[:3])


def _avoid_action(
    customer: Mapping[str, Any],
    active_work: Optional[Mapping[str, Any]],
) -> JudgmentItem:
    stage = _text(customer.get("relationship_stage"))
    need = _text(customer.get("current_need"))
    financial = _profile(customer, "financial_context")
    relationship = _profile(customer, "relationship_context")

    liquidity = _text(financial.get("liquidity_preference"))
    concern = _first_list_value(relationship.get("key_concerns"))

    evidence: List[JudgmentEvidence] = []

    if stage == "rejected":
        text = "避免产品推介和高频主动触达；冷静期内只保留必要服务"
        evidence.append(
            JudgmentEvidence(source="关系阶段", text="客户近期已明确拒绝")
        )
    elif active_work and _text(active_work.get("status")) == "waiting" and _text(
        active_work.get("waiting_on")
    ) in {"customer", "scheduled_time"}:
        text = "避免在客户约定回复或联系时间之前重复催促"
        evidence.append(
            JudgmentEvidence(
                source="当前工作项",
                text=_text(active_work.get("current_progress"))
                or "当前正在等待客户/约定时间",
            )
        )
    elif stage == "considering":
        text = "避免把“考虑中”直接解释成拒绝，也避免连续催促；先把顾虑和决策条件问清楚"
        evidence.append(
            JudgmentEvidence(source="关系阶段", text="客户当前仍处于考虑阶段")
        )
    elif "高" in liquidity or "流动性" in concern or "流动性" in need:
        text = "避免在资金用途和可使用时间尚未确认前，过早进入具体产品或长期锁定方案讨论"
        if liquidity:
            evidence.append(
                JudgmentEvidence(source="流动性偏好", text=liquidity)
            )
        if concern:
            evidence.append(JudgmentEvidence(source="主要顾虑", text=concern))
    else:
        text = "避免把画像标签或待验证假设当成客户事实；先确认需求、期限和顾虑再讨论具体方案"
        evidence.append(
            JudgmentEvidence(
                source="经营原则",
                text="画像与待验证假设只用于辅助提问，不替代客户明确表达",
            )
        )

    return JudgmentItem(text=text, evidence=evidence[:3])


def build_operating_judgment(
    customer: Mapping[str, Any],
    *,
    activities: Sequence[Mapping[str, Any]],
    active_work: Optional[Mapping[str, Any]],
    now: datetime,
) -> Dict[str, Any]:
    return {
        "generated_at": to_iso(now),
        "mode": "deterministic",
        "current_state": _current_state(customer, active_work, activities).to_dict(),
        "core_concern": _core_concern(customer, activities).to_dict(),
        "decision_barrier": _decision_barrier(
            customer,
            active_work,
            activities,
        ).to_dict(),
        "next_confirmation": _next_confirmation(customer, active_work).to_dict(),
        "action_brief": _action_brief(customer, active_work).to_dict(),
        "communication_approach": _communication_approach(
            customer,
            active_work,
        ).to_dict(),
        "avoid_action": _avoid_action(customer, active_work).to_dict(),
    }
