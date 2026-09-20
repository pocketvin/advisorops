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

LEVELS = ["Gold", "Platinum", "Black Gold", "Diamond", "Black Diamond"]
RISKS = ["C2", "C3", "C3", "C4"]
ASSET_BANDS = ["10-30万", "30-80万", "80-150万", "150-300万", "300万以上"]
FUND_BANDS = ["5万以内", "5-20万", "20-50万", "50-100万", "100万以上"]


RESIDENCE_REGIONS = [
    "杭州·临平", "杭州·余杭", "杭州·西湖", "杭州·滨江", "杭州·上城",
    "上海·浦东", "上海·徐汇", "宁波·鄞州", "绍兴·越城", "嘉兴·南湖",
]
OCCUPATIONS = [
    ("软件工程师", "互联网/软件", "民营企业"),
    ("企业中层管理", "先进制造", "民营企业"),
    ("小微企业主", "商贸零售", "自营企业"),
    ("医生", "医疗健康", "事业单位"),
    ("教师", "教育", "事业单位"),
    ("财务负责人", "专业服务", "民营企业"),
    ("销售负责人", "消费品", "民营企业"),
    ("产品经理", "互联网/软件", "民营企业"),
    ("退休人员", "退休", "退休"),
    ("自由职业者", "创意/设计", "自由职业"),
]
FAMILY_STAGES = [
    "单身独居", "新婚家庭", "育有学龄前子女", "育有学龄子女", "子女升学阶段",
    "家庭责任较重", "空巢阶段", "临近退休", "已退休", "三代同堂",
]
INCOME_BANDS = ["20-30万", "30-50万", "50-80万", "80-150万", "150万以上"]
LIABILITY_BANDS = ["无明显负债", "20万以内", "20-80万", "80-200万", "200万以上"]
CASH_FLOW_PATTERNS = ["月度稳定", "奖金占比较高", "经营性现金流波动", "季节性明显", "退休现金流稳定"]
INVESTMENT_EXPERIENCE = ["1-3年", "3-5年", "5-10年", "10年以上", "经验较少"]
INVESTMENT_GOALS = ["稳健增值", "长期成长", "退休准备", "子女教育", "流动性管理", "分散配置"]
INVESTMENT_HORIZONS = ["1年以内", "1-3年", "3-5年", "5年以上"]
CONTACT_CHANNELS = ["电话", "企业微信", "线下", "企业微信+电话", "App消息"]
CONTACT_TIMES = ["工作日上午", "工作日下午", "午休前后", "工作日晚间", "周末上午"]
COMMUNICATION_STYLES = [
    "偏好简洁结论，再看细节",
    "偏好数据和研究依据",
    "需要较充分解释风险和机制",
    "更接受电话沟通，不喜欢长文字",
    "偏好先文字说明，再预约电话",
]
DECISION_STYLES = [
    "独立决策，节奏较快",
    "习惯比较多种方案后决定",
    "重大事项会与家人共同商量",
    "决策偏慢，需要多次确认",
    "对外部事件敏感，容易阶段性改变计划",
]
INTERESTS = [
    ["跑步", "科技产品"],
    ["亲子教育", "旅行"],
    ["汽车", "摄影"],
    ["阅读", "健康管理"],
    ["球类运动", "商业资讯"],
]
KEY_CONCERNS = [
    ["流动性", "最大回撤"],
    ["资金安全", "信息透明"],
    ["费用", "操作复杂度"],
    ["政策变化", "市场波动"],
    ["家庭资金安排", "长期可持续性"],
]
TRUST_FACTORS = [
    ["研究依据充分", "不频繁打扰"],
    ["风险讲清楚", "按约定时间跟进"],
    ["信息简洁", "响应及时"],
    ["长期服务一致性", "先理解需求再谈方案"],
    ["数据透明", "不做收益承诺"],
]
MAJOR_PLANS = [
    "未来两年可能购置改善型住房",
    "子女教育支出将逐步增加",
    "未来三年计划扩大经营投入",
    "开始考虑退休现金流安排",
    "暂无明确大额支出计划",
]


def _rich_profile(index: int) -> Dict[str, object]:
    occupation, industry, employer_type = OCCUPATIONS[index % len(OCCUPATIONS)]
    return {
        "demographics": {
            "residence_region": RESIDENCE_REGIONS[index % len(RESIDENCE_REGIONS)],
            "occupation": occupation,
            "industry": industry,
            "employer_type": employer_type,
        },
        "family_and_life": {
            "family_stage": FAMILY_STAGES[index % len(FAMILY_STAGES)],
            "dependents_summary": ["无明确赡养压力", "需承担子女教育", "需兼顾父母养老"][index % 3],
            "major_plan": MAJOR_PLANS[index % len(MAJOR_PLANS)],
        },
        "financial_context": {
            "annual_income_band": INCOME_BANDS[index % len(INCOME_BANDS)],
            "liabilities_band": LIABILITY_BANDS[index % len(LIABILITY_BANDS)],
            "cash_flow_pattern": CASH_FLOW_PATTERNS[index % len(CASH_FLOW_PATTERNS)],
            "liquidity_preference": ["高", "中高", "中", "中低"][index % 4],
        },
        "investment_context": {
            "experience": INVESTMENT_EXPERIENCE[index % len(INVESTMENT_EXPERIENCE)],
            "primary_goal": INVESTMENT_GOALS[index % len(INVESTMENT_GOALS)],
            "investment_horizon": INVESTMENT_HORIZONS[index % len(INVESTMENT_HORIZONS)],
            "information_preference": ["研究报告", "图表摘要", "简短要点", "电话讲解"][index % 4],
        },
        "service_preferences": {
            "preferred_channel": CONTACT_CHANNELS[index % len(CONTACT_CHANNELS)],
            "preferred_contact_time": CONTACT_TIMES[index % len(CONTACT_TIMES)],
            "communication_style": COMMUNICATION_STYLES[index % len(COMMUNICATION_STYLES)],
        },
        "relationship_context": {
            "interests": INTERESTS[index % len(INTERESTS)],
            "key_concerns": KEY_CONCERNS[index % len(KEY_CONCERNS)],
            "trust_factors": TRUST_FACTORS[index % len(TRUST_FACTORS)],
        },
    }


def _profile_hypotheses(index: int) -> List[Dict[str, object]]:
    return [
        {
            "key": "decision_style",
            "value": DECISION_STYLES[index % len(DECISION_STYLES)],
            "confidence": round(0.58 + (index % 4) * 0.08, 2),
            "status": "needs_validation",
            "basis": "基于历史沟通节奏形成的经营假设，下一次沟通应继续验证。",
        }
    ]


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
        "profile": _rich_profile(index),
        "profile_hypotheses": _profile_hypotheses(index),
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
            "customer_level": "Platinum",
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
            "customer_level": "Gold",
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
            "customer_level": "Platinum",
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
