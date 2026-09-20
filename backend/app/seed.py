from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from . import repository
from .db import PathLike, init_db, transaction
from .time_utils import to_iso, utc_now


NAMES = [
    "张明远", "陈可欣", "李卓", "王启航", "周婷", "赵然", "孙嘉宁", "林泽宇",
    "吴思涵", "徐嘉树", "黄晨曦", "许安然", "郑一鸣", "冯诗雨", "沈知行", "韩若曦",
    "唐俊杰", "曹予安", "潘书瑶", "袁景川", "程语桐", "吕承泽", "邵雨辰", "蒋沐阳",
    "蔡宁", "叶之航", "杜若", "苏景然", "魏清越", "罗伊宁", "顾泽", "梁嘉禾",
    "宋知微", "马启辰", "谢雨凡", "邓知夏", "方一诺", "江予舟", "白安琪", "高云帆",
]

LEVELS = ["普通", "银卡", "金卡", "铂金", "钻石"]
RISKS = ["C2", "C3", "C3", "C4"]
ASSET_BANDS = ["10-30万", "30-80万", "80-150万", "150-300万", "300万以上"]
FUND_BANDS = ["5万以内", "5-20万", "20-50万", "50-100万", "100万以上"]


def _customer(
    index: int,
    now: datetime,
    **overrides,
) -> Dict[str, object]:
    stage_cycle = ["contacted", "interested", "contacted", "new", "dormant"]
    intent_cycle = ["medium", "high", "medium", "unknown", "low"]
    stage = stage_cycle[index % len(stage_cycle)]
    intent = intent_cycle[index % len(intent_cycle)]
    customer_id = f"C{index + 1:03d}"

    base: Dict[str, object] = {
        "customer_id": customer_id,
        "name": NAMES[index],
        "age_band": ["25-35", "35-45", "45-55", "55+"][index % 4],
        "customer_level": LEVELS[index % len(LEVELS)],
        "risk_level": RISKS[index % len(RISKS)],
        "total_assets_band": ASSET_BANDS[index % len(ASSET_BANDS)],
        "investable_funds_band": FUND_BANDS[(index + 1) % len(FUND_BANDS)],
        "holdings_summary": [
            "现金管理 + 权益基金",
            "股票 + 现金管理",
            "固收类 + 基金",
            "ETF + 股票",
            "现金管理",
        ][index % 5],
        "recent_login_at": to_iso(now - timedelta(days=index % 9)),
        "recent_trade_at": to_iso(now - timedelta(days=(index + 2) % 12)),
        "asset_change_30d_pct": float((index % 9) - 4),
        "recent_product_interest": [
            "",
            "指数 ETF",
            "固收类配置",
            "",
            "现金管理",
        ][index % 5],
        "recent_consult_topic": [
            "资产配置",
            "",
            "市场波动",
            "流动性安排",
            "",
        ][index % 5],
        "relationship_stage": stage,
        "intent_level": intent,
        "current_need": [
            "日常资产配置梳理",
            "流动性安排",
            "长期资金规划",
            "首次需求了解",
            "服务关系维护",
        ][index % 5],
        "current_obstacle": "",
        "current_progress": "已建立客户经营档案，等待下一次有效互动",
        "next_step": "按当前经营节奏继续跟进",
        "next_contact_at": None,
        "cooldown_until": None,
        "pinned": False,
        "manager_note": "",
        "last_contact_at": to_iso(now - timedelta(days=5 + (index % 18))),
        "recent_signal": "",
        "created_at": to_iso(now - timedelta(days=120 + index)),
        "updated_at": to_iso(now),
    }
    base.update(overrides)
    return base


def _customers(now: datetime) -> List[Dict[str, object]]:
    customers = [_customer(index, now) for index in range(40)]
    scenarios: Dict[str, Dict[str, object]] = {
        "C001": {
            "customer_level": "铂金",
            "relationship_stage": "considering",
            "intent_level": "high",
            "current_need": "在保持流动性的前提下重新梳理资产配置",
            "current_obstacle": "仍在考虑此前方案",
            "current_progress": "已发送资产配置框架，等待按约定回访",
            "next_step": "按约定回访，确认考虑结果",
            "next_contact_at": to_iso(now - timedelta(days=1)),
            "last_contact_at": to_iso(now - timedelta(days=4)),
        },
        "C002": {
            "customer_level": "金卡",
            "relationship_stage": "contacted",
            "intent_level": "medium",
            "current_need": "确认近期资金安排是否发生变化",
            "current_progress": "上次为常规服务回访",
            "next_step": "先核实近期变化背后的真实需求",
            "last_contact_at": to_iso(now - timedelta(days=8)),
            "asset_change_30d_pct": 12.4,
            "recent_product_interest": "指数 ETF",
            "recent_signal": "近 30 日资产明显增加，并新增指数 ETF 关注",
        },
        "C003": {
            "relationship_stage": "considering",
            "intent_level": "medium",
            "current_need": "近期流动性安排",
            "current_obstacle": "客户希望先观察几天",
            "current_progress": "刚完成沟通，客户明确要求三天后再联系",
            "next_step": "三天后按约定回访",
            "next_contact_at": to_iso(now + timedelta(days=3)),
            "last_contact_at": to_iso(now - timedelta(hours=6)),
        },
        "C004": {
            "customer_level": "铂金",
            "relationship_stage": "interested",
            "intent_level": "high",
            "current_need": "明确长期资金用途和可投资期限",
            "current_progress": "已进入重点沟通，今天需要补齐需求信息",
            "next_step": "今天确认资金期限与流动性边界",
            "last_contact_at": to_iso(now - timedelta(days=2)),
        },
        "C005": {
            "relationship_stage": "contacted",
            "intent_level": "medium",
            "current_need": "确认资料后的反馈",
            "current_progress": "已发送资料，正在等待客户回复",
            "next_step": "明天下午检查客户反馈",
            "next_contact_at": to_iso(now + timedelta(days=1)),
            "last_contact_at": to_iso(now - timedelta(hours=4)),
        },
        "C006": {
            "relationship_stage": "interested",
            "intent_level": "medium",
            "current_need": "补充内部可提供的服务资料",
            "current_progress": "客户问题已确认，等待内部资料",
            "next_step": "资料齐全后回传客户",
            "last_contact_at": to_iso(now - timedelta(days=1)),
        },
        "C007": {
            "relationship_stage": "contacted",
            "intent_level": "medium",
            "current_progress": "今天已经完成一次服务回访",
            "next_step": "两周后再做服务维护",
            "next_contact_at": to_iso(now + timedelta(days=14)),
            "last_contact_at": to_iso(now - timedelta(hours=2)),
        },
        "C008": {
            "relationship_stage": "rejected",
            "intent_level": "low",
            "current_need": "暂无主动经营需求",
            "current_obstacle": "客户明确表示近期不希望被主动营销触达",
            "current_progress": "已记录明确拒绝",
            "next_step": "冷静期结束后仅做低打扰服务复核",
            "cooldown_until": to_iso(now + timedelta(days=25)),
            "next_contact_at": to_iso(now + timedelta(days=25)),
            "last_contact_at": to_iso(now - timedelta(days=2)),
        },
        "C009": {
            "relationship_stage": "considering",
            "intent_level": "high",
            "current_need": "继续确认近期配置计划",
            "current_progress": "上次约定两天后回访，但尚未完成",
            "next_step": "尽快补做约定回访",
            "next_contact_at": to_iso(now - timedelta(days=3)),
            "last_contact_at": to_iso(now - timedelta(days=7)),
        },
        "C010": {
            "relationship_stage": "dormant",
            "intent_level": "low",
            "current_need": "重新确认服务需求",
            "current_progress": "较长时间没有有效互动",
            "next_step": "低打扰服务回访",
            "last_contact_at": to_iso(now - timedelta(days=46)),
        },
        "C011": {
            "relationship_stage": "interested",
            "intent_level": "medium",
            "current_need": "持续跟踪家庭长期资金安排",
            "current_progress": "客户经理主动标记为当前重点关注",
            "next_step": "确认当前进度和下一步",
            "pinned": True,
            "last_contact_at": to_iso(now - timedelta(days=5)),
        },
        "C012": {
            "relationship_stage": "interested",
            "intent_level": "high",
            "current_need": "长期配置",
            "current_progress": "上一轮沟通仍保持兴趣",
            "next_step": "继续明确资金使用时间",
            "last_contact_at": to_iso(now - timedelta(days=6)),
        },
        "C013": {
            "relationship_stage": "contacted",
            "intent_level": "medium",
            "current_need": "确认账户近期变化",
            "current_progress": "暂未发现明确需求",
            "next_step": "有新信号时再联系",
            "last_contact_at": to_iso(now - timedelta(days=10)),
        },
        "C014": {
            "relationship_stage": "contacted",
            "intent_level": "medium",
            "current_need": "常规服务维护",
            "current_progress": "外部 CRM 档案正常",
            "next_step": "按计划维护",
            "last_contact_at": to_iso(now - timedelta(days=12)),
        },
        "C015": {
            "relationship_stage": "contacted",
            "intent_level": "medium",
            "current_need": "待确认",
            "current_progress": "暂无新增反馈",
            "next_step": "等待新的客户回复",
            "last_contact_at": to_iso(now - timedelta(days=9)),
        },
    }
    for customer in customers:
        customer.update(scenarios.get(str(customer["customer_id"]), {}))
    return customers


def _seed_initial_activities(conn, customers: List[Dict[str, object]], now: datetime) -> None:
    for customer in customers:
        repository.insert_activity(
            conn,
            {
                "customer_id": customer["customer_id"],
                "source": "manual",
                "channel": "system",
                "activity_type": "profile",
                "occurred_at": customer["created_at"],
                "raw_content": "",
                "structured_summary": "建立固定模拟客户档案；不对应任何真实客户。",
                "customer_feedback": "",
                "action_taken": "初始化演示数据",
                "next_step": customer["next_step"],
                "next_contact_at": customer["next_contact_at"],
                "stage_after": customer["relationship_stage"],
                "intent_after": customer["intent_level"],
                "metadata": {"demo": True},
                "created_at": customer["created_at"],
            },
        )

    # A few richer historical events make the detail timeline useful immediately.
    rich_history = {
        "C001": [
            ("完成需求访谈", "客户关注流动性和长期配置的平衡。", now - timedelta(days=9)),
            ("发送资产配置框架", "客户表示需要几天时间考虑。", now - timedelta(days=4)),
        ],
        "C004": [
            ("电话沟通", "客户已进入具体需求讨论，需要补齐资金期限。", now - timedelta(days=2)),
        ],
        "C005": [
            ("发送服务资料", "客户表示晚些时候查看并反馈。", now - timedelta(hours=4)),
        ],
    }
    for customer_id, events in rich_history.items():
        customer = next(c for c in customers if c["customer_id"] == customer_id)
        for title, summary, occurred in events:
            repository.insert_activity(
                conn,
                {
                    "customer_id": customer_id,
                    "source": "manual",
                    "channel": "phone" if title == "电话沟通" else "wecom",
                    "activity_type": "interaction",
                    "occurred_at": to_iso(occurred),
                    "raw_content": summary,
                    "structured_summary": summary,
                    "customer_feedback": summary,
                    "action_taken": title,
                    "next_step": customer["next_step"],
                    "next_contact_at": customer["next_contact_at"],
                    "stage_after": customer["relationship_stage"],
                    "intent_after": customer["intent_level"],
                    "metadata": {"demo": True, "seed_history": True},
                    "created_at": to_iso(occurred),
                },
            )


def _seed_work_items(conn, now: datetime) -> None:
    active = [
        (
            "C004",
            "今天确认资金期限与流动性边界",
            "action_required",
            "manager",
            "已进入重点沟通，今天需要补齐需求信息",
            "今天确认资金期限与流动性边界",
            now - timedelta(hours=1),
            now + timedelta(hours=2),
        ),
        (
            "C005",
            "明天下午检查客户反馈",
            "waiting",
            "customer",
            "已发送资料，正在等待客户回复",
            "明天下午检查客户反馈",
            now - timedelta(hours=4),
            now + timedelta(days=1),
        ),
        (
            "C006",
            "资料齐全后回传客户",
            "waiting",
            "internal",
            "客户问题已确认，等待内部资料",
            "资料齐全后回传客户",
            now - timedelta(hours=3),
            None,
        ),
    ]
    for customer_id, title, status, waiting_on, progress, action, started, due in active:
        repository.create_work_item(
            conn,
            {
                "customer_id": customer_id,
                "title": title,
                "status": status,
                "waiting_on": waiting_on,
                "current_progress": progress,
                "next_action": action,
                "due_at": to_iso(due),
                "started_at": to_iso(started),
                "completed_at": None,
                "completion_activity_id": None,
                "created_at": to_iso(started),
                "updated_at": to_iso(now),
            },
        )

    completed_activity = repository.insert_activity(
        conn,
        {
            "customer_id": "C007",
            "source": "manual",
            "channel": "phone",
            "activity_type": "interaction",
            "occurred_at": to_iso(now - timedelta(hours=2)),
            "raw_content": "完成今天的常规服务回访，客户暂无新增需求，两周后再联系。",
            "structured_summary": "已完成常规服务回访，暂无新增需求。",
            "customer_feedback": "近期暂无新增需求。",
            "action_taken": "服务回访",
            "next_step": "两周后再做服务维护",
            "next_contact_at": to_iso(now + timedelta(days=14)),
            "stage_after": "contacted",
            "intent_after": "medium",
            "metadata": {"demo": True},
            "created_at": to_iso(now - timedelta(hours=2)),
        },
    )
    repository.create_work_item(
        conn,
        {
            "customer_id": "C007",
            "title": "完成今日服务回访",
            "status": "completed_today",
            "waiting_on": "none",
            "current_progress": "已完成常规服务回访，暂无新增需求",
            "next_action": "两周后再做服务维护",
            "due_at": to_iso(now + timedelta(days=14)),
            "started_at": to_iso(now - timedelta(hours=3)),
            "completed_at": to_iso(now - timedelta(hours=2)),
            "completion_activity_id": completed_activity,
            "created_at": to_iso(now - timedelta(hours=3)),
            "updated_at": to_iso(now - timedelta(hours=2)),
        },
    )


def _seed_external_events(conn, now: datetime) -> None:
    events = [
        {
            "source": "mock_wecom",
            "source_event_id": "wx-001",
            "sequence_number": 1,
            "customer_id": "C012",
            "channel": "wecom",
            "event_kind": "message",
            "occurred_at": to_iso(now - timedelta(minutes=18)),
            "raw_content": "最近公司这边可能要用一笔钱，之前的方案先放一放，十月以后你再找我吧。",
            "payload": {},
        },
        {
            "source": "mock_behavior",
            "source_event_id": "behavior-001",
            "sequence_number": 1,
            "customer_id": "C013",
            "channel": "app",
            "event_kind": "behavior_signal",
            "occurred_at": to_iso(now - timedelta(minutes=31)),
            "raw_content": "近 30 日资产增加约 15%，最近新增关注指数 ETF。",
            "payload": {
                "signal": "近 30 日资产增加约 15%，最近新增关注指数 ETF",
                "asset_change_30d_pct": 15.0,
                "recent_product_interest": "指数 ETF",
            },
        },
        {
            "source": "mock_crm",
            "source_event_id": "crm-001",
            "sequence_number": 1,
            "customer_id": "C014",
            "channel": "system",
            "event_kind": "fact",
            "occurred_at": to_iso(now - timedelta(minutes=45)),
            "raw_content": "外部 CRM 返回：客户最近一次服务标签已同步。",
            "payload": {"fact": "客户服务标签已同步"},
        },
        {
            "source": "mock_wecom",
            "source_event_id": "wx-002",
            "sequence_number": 2,
            "customer_id": "C015",
            "channel": "wecom",
            "event_kind": "message",
            "occurred_at": to_iso(now - timedelta(minutes=5)),
            "raw_content": "我今天比较忙，周一下午再聊吧，到时候你提醒我一下。",
            "payload": {},
        },
        {
            "source": "mock_behavior",
            "source_event_id": "behavior-002",
            "sequence_number": 2,
            "customer_id": "C016",
            "channel": "app",
            "event_kind": "behavior_signal",
            "occurred_at": to_iso(now - timedelta(minutes=4)),
            "raw_content": "客户近两日重新活跃，并连续查看现金管理相关内容。",
            "payload": {
                "signal": "近两日重新活跃，并连续查看现金管理相关内容",
                "recent_product_interest": "现金管理",
                "recent_login_at": to_iso(now - timedelta(hours=5)),
            },
        },
    ]
    for event in events:
        repository.insert_external_event(conn, event)

    for source in ("mock_wecom", "mock_behavior", "mock_crm"):
        repository.upsert_sync_state(
            conn,
            source=source,
            cursor=0,
            last_attempt_at=None,
            last_success_at=None,
            last_error="",
            last_result_count=0,
        )


def seed_demo_data(
    db_path: Optional[PathLike] = None,
    now: Optional[datetime] = None,
) -> None:
    current = now or utc_now()
    customers = _customers(current)
    with transaction(db_path) as conn:
        for customer in customers:
            repository.insert_customer(conn, customer)
        _seed_initial_activities(conn, customers, current)
        _seed_work_items(conn, current)
        _seed_external_events(conn, current)
        repository.set_demo_state(conn, "time_offset_seconds", "0")


def ensure_seeded(
    db_path: Optional[PathLike] = None,
    now: Optional[datetime] = None,
) -> None:
    init_db(db_path)
    from .db import connect

    with connect(db_path) as conn:
        count = conn.execute("SELECT COUNT(*) AS count FROM customers").fetchone()["count"]
    if int(count) == 0:
        seed_demo_data(db_path, now=now)


def reset_demo_data(
    db_path: Optional[PathLike] = None,
    now: Optional[datetime] = None,
) -> None:
    init_db(db_path)
    with transaction(db_path) as conn:
        repository.reset_all(conn)
    seed_demo_data(db_path, now=now)
