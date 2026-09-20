import random
from datetime import timedelta
from typing import Any, Dict, List, Optional

from . import repository
from .db import PathLike, init_db
from .time_utils import to_iso, utc_now


NAMES = [
    "张明远", "陈可欣", "李卓", "王启航", "周婷", "赵然", "孙嘉宁", "林泽宇",
    "吴思涵", "徐嘉树", "黄晨曦", "许安然", "郑一鸣", "冯诗雨", "沈知行", "韩若曦",
    "唐俊杰", "曹予安", "潘书瑶", "袁景川", "程语桐", "吕承泽", "邵雨辰", "蒋沐阳",
    "蔡宁", "叶之航", "杜若", "苏景然", "魏清越", "罗伊宁", "顾泽", "梁嘉禾",
    "宋知微", "马启辰", "谢雨凡", "邓知夏", "方一诺", "江予舟", "白安琪", "高云帆",
]

HOLDING_OPTIONS = [
    ["现金管理", "权益基金"],
    ["股票", "现金管理"],
    ["固收类", "基金"],
    ["ETF", "股票"],
    ["现金管理"],
    ["基金", "债券"],
]
INTEREST_OPTIONS = ["", "", "", "指数ETF", "固收类配置", "基金定投", "现金管理"]
CONSULT_OPTIONS = ["", "", "资产配置", "市场波动", "流动性安排", "长期投资计划"]
LEVELS = ["普通", "银卡", "金卡", "铂金", "钻石"]
RISKS = ["C2", "C3", "C3", "C4"]
ASSET_BANDS = ["10-30万", "30-80万", "80-150万", "150-300万", "300万以上"]
FUND_BANDS = ["5万以内", "5-20万", "20-50万", "50-100万", "100万以上"]


def _iso_delta(days: int = 0, hours: int = 0) -> str:
    return to_iso(utc_now() + timedelta(days=days, hours=hours)) or ""


def _base_customer(index: int, rng: random.Random) -> Dict[str, Any]:
    customer_id = f"C{index + 1:03d}"
    stage = rng.choices(
        ["new", "contacted", "interested", "considering", "rejected", "dormant"],
        weights=[2, 6, 5, 5, 2, 3],
        k=1,
    )[0]
    default_intent = {
        "new": "unknown",
        "contacted": "medium",
        "interested": "high",
        "considering": "medium",
        "rejected": "low",
        "dormant": "low",
    }[stage]
    last_contact_days = rng.randint(1, 18)
    next_contact: Optional[str] = None
    if stage in {"contacted", "interested"}:
        next_contact = _iso_delta(days=rng.randint(-2, 5))
    elif stage == "considering":
        next_contact = _iso_delta(days=rng.randint(1, 7))
    elif stage == "rejected":
        next_contact = _iso_delta(days=rng.randint(20, 45))

    now_iso = to_iso(utc_now()) or ""
    action = rng.choice(["完成需求回访", "补充客户画像", "确认近期关注主题", "发送服务资料"])
    return {
        "customer_id": customer_id,
        "name": NAMES[index],
        "age_band": rng.choice(["25-35", "35-45", "45-55", "55+"]),
        "customer_level": rng.choice(LEVELS),
        "risk_level": rng.choice(RISKS),
        "total_assets_band": rng.choice(ASSET_BANDS),
        "holdings": rng.choice(HOLDING_OPTIONS),
        "investable_funds_band": rng.choice(FUND_BANDS),
        "last_login_at": _iso_delta(days=-rng.randint(0, 12)),
        "last_trade_at": _iso_delta(days=-rng.randint(0, 15)),
        "asset_change_30d_pct": round(rng.uniform(-12, 16), 1),
        "recent_product_interest": rng.choice(INTEREST_OPTIONS),
        "recent_consult_topic": rng.choice(CONSULT_OPTIONS),
        "last_contact_at": _iso_delta(days=-last_contact_days),
        "contact_method": rng.choice(["电话", "企业微信", "线下", "App消息"]),
        "historical_contact_count": rng.randint(1, 14),
        "stage": stage,
        "intent": default_intent,
        "last_feedback": rng.choice(["", "近期先保持关注", "有需要再沟通", "想再了解一下", "近期比较忙"]),
        "measures": [action],
        "next_step": "按当前进度继续跟进",
        "next_contact_at": next_contact,
        "manager_note": "",
        "pinned": False,
        "pinned_at": None,
        "created_at": _iso_delta(days=-rng.randint(60, 240)),
        "updated_at": now_iso,
    }


def _scenario_overrides() -> Dict[str, Dict[str, Any]]:
    return {
        "C001": {
            "customer_level": "铂金",
            "risk_level": "C3",
            "total_assets_band": "80-150万",
            "holdings": ["基金", "现金管理"],
            "investable_funds_band": "20-50万",
            "last_login_at": _iso_delta(days=-1),
            "last_trade_at": _iso_delta(days=-2),
            "asset_change_30d_pct": 12.4,
            "recent_product_interest": "固收类配置",
            "recent_consult_topic": "资产配置",
            "last_contact_at": _iso_delta(days=-4),
            "contact_method": "电话",
            "historical_contact_count": 6,
            "stage": "considering",
            "intent": "high",
            "last_feedback": "方案我再考虑几天，周末后再联系。",
            "measures": ["完成需求访谈", "发送资产配置框架"],
            "next_step": "按约定回访，确认考虑结果",
            "next_contact_at": _iso_delta(days=-1),
            "manager_note": "关注回访节奏，不提前重复触达。",
            "pinned": False,
            "pinned_at": None,
        },
        "C002": {
            "customer_level": "金卡",
            "stage": "interested",
            "intent": "high",
            "last_contact_at": _iso_delta(days=-3),
            "next_contact_at": _iso_delta(hours=8),
            "recent_consult_topic": "长期投资计划",
            "recent_product_interest": "",
            "asset_change_30d_pct": 3.2,
            "last_feedback": "希望把长期资金安排再梳理清楚。",
            "measures": ["完成长期目标梳理"],
            "next_step": "继续澄清期限与流动性需求",
            "pinned": True,
            "pinned_at": _iso_delta(days=-1),
        },
        "C003": {
            "customer_level": "铂金",
            "stage": "rejected",
            "intent": "low",
            "last_contact_at": _iso_delta(days=-1),
            "next_contact_at": _iso_delta(days=30),
            "recent_consult_topic": "",
            "recent_product_interest": "",
            "asset_change_30d_pct": 1.1,
            "last_feedback": "近期没有需求，暂时不用再联系。",
            "measures": ["记录客户明确拒绝"],
            "next_step": "进入冷静期，后续仅做必要服务维护",
            "pinned": False,
            "pinned_at": None,
        },
        "C004": {
            "customer_level": "普通",
            "stage": "contacted",
            "intent": "medium",
            "last_contact_at": _iso_delta(days=-8),
            "next_contact_at": None,
            "last_login_at": _iso_delta(hours=-10),
            "last_trade_at": _iso_delta(days=-1),
            "asset_change_30d_pct": 18.6,
            "recent_product_interest": "指数ETF",
            "recent_consult_topic": "",
            "last_feedback": "上次没有明确新需求。",
            "measures": ["完成常规服务回访"],
            "next_step": "先核实近期行为变化原因",
        },
        "C005": {
            "customer_level": "金卡",
            "stage": "considering",
            "intent": "medium",
            "last_contact_at": _iso_delta(hours=-6),
            "next_contact_at": _iso_delta(days=3),
            "asset_change_30d_pct": 0.8,
            "recent_product_interest": "",
            "recent_consult_topic": "流动性安排",
            "last_feedback": "我再考虑三天，到时候再聊。",
            "measures": ["完成流动性需求沟通"],
            "next_step": "三天后按约定回访",
        },
        "C006": {
            "customer_level": "银卡",
            "stage": "dormant",
            "intent": "low",
            "last_contact_at": _iso_delta(days=-35),
            "next_contact_at": None,
            "asset_change_30d_pct": -16.2,
            "recent_product_interest": "",
            "recent_consult_topic": "",
            "last_feedback": "",
            "measures": ["历史服务维护"],
            "next_step": "先确认近期资金变化与服务需求",
        },
    }


def _seed_timeline(customer: Dict[str, Any], db_path: Optional[PathLike]) -> None:
    repository.add_timeline_event(
        {
            "customer_id": customer["customer_id"],
            "event_type": "profile",
            "title": "建立模拟客户档案",
            "detail": "演示数据初始化；不对应任何真实券商客户。",
            "feedback": "",
            "stage_after": "new",
            "next_contact_at": None,
            "metadata": {"demo": True},
            "created_at": customer["created_at"],
        },
        db_path,
    )
    if customer.get("last_contact_at"):
        repository.add_timeline_event(
            {
                "customer_id": customer["customer_id"],
                "event_type": "contact",
                "title": customer.get("measures", ["完成客户沟通"])[-1],
                "detail": customer.get("manager_note") or "记录最近一次客户经理动作。",
                "feedback": customer.get("last_feedback") or "",
                "stage_after": customer["stage"],
                "next_contact_at": customer.get("next_contact_at"),
                "metadata": {"contact_method": customer.get("contact_method", "")},
                "created_at": customer["last_contact_at"],
            },
            db_path,
        )


def seed_demo_data(db_path: Optional[PathLike] = None) -> None:
    rng = random.Random(20260920)
    overrides = _scenario_overrides()
    for index in range(40):
        customer = _base_customer(index, rng)
        customer.update(overrides.get(customer["customer_id"], {}))
        repository.insert_customer(customer, db_path)
        _seed_timeline(customer, db_path)


def ensure_seeded(db_path: Optional[PathLike] = None) -> None:
    init_db(db_path)
    if repository.count_customers(db_path) == 0:
        seed_demo_data(db_path)


def reset_demo_data(db_path: Optional[PathLike] = None) -> None:
    init_db(db_path)
    repository.reset_all(db_path)
    seed_demo_data(db_path)
