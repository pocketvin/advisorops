from datetime import datetime, timedelta
from typing import Optional

from . import repository
from .db import PathLike, init_db, transaction
from .time_utils import to_iso, utc_now


def _customer(
    customer_id: str,
    name: str,
    now: datetime,
    **overrides,
):
    base = {
        "customer_id": customer_id,
        "name": name,
        "age_band": "35-45",
        "customer_level": "金卡",
        "risk_level": "C3",
        "total_assets_band": "80-150万",
        "investable_funds_band": "20-50万",
        "relationship_stage": "contacted",
        "intent_level": "medium",
        "current_need": "资产配置",
        "current_obstacle": "",
        "current_progress": "已完成基础需求了解",
        "next_step": "",
        "next_contact_at": None,
        "cooldown_until": None,
        "pinned": False,
        "last_contact_at": to_iso(now - timedelta(days=7)),
        "recent_signal": "",
        "created_at": to_iso(now - timedelta(days=90)),
        "updated_at": to_iso(now),
    }
    base.update(overrides)
    return base


def seed_demo_data(
    db_path: Optional[PathLike] = None,
    now: Optional[datetime] = None,
) -> None:
    current = now or utc_now()
    customers = [
        _customer(
            "C001",
            "张明远",
            current,
            customer_level="铂金",
            relationship_stage="considering",
            intent_level="high",
            current_need="在保持流动性的前提下重新梳理资产配置",
            current_obstacle="仍在考虑此前方案",
            current_progress="已发送资产配置框架，等待按约定回访",
            next_step="按约定回访，确认考虑结果",
            next_contact_at=to_iso(current - timedelta(days=1)),
            last_contact_at=to_iso(current - timedelta(days=4)),
        ),
        _customer(
            "C002",
            "陈可欣",
            current,
            customer_level="金卡",
            relationship_stage="contacted",
            intent_level="medium",
            current_need="确认近期资金安排是否发生变化",
            current_progress="上次为常规服务回访",
            next_step="先核实近期变化背后的真实需求",
            last_contact_at=to_iso(current - timedelta(days=8)),
            recent_signal="近 30 日资产明显增加，并新增指数 ETF 关注",
        ),
        _customer(
            "C003",
            "李卓",
            current,
            customer_level="银卡",
            relationship_stage="considering",
            intent_level="medium",
            current_need="近期流动性安排",
            current_obstacle="客户希望先观察几天",
            current_progress="刚完成沟通，客户明确要求三天后再联系",
            next_step="三天后按约定回访",
            next_contact_at=to_iso(current + timedelta(days=3)),
            last_contact_at=to_iso(current - timedelta(hours=6)),
        ),
    ]

    with transaction(db_path) as conn:
        for customer in customers:
            repository.insert_customer(conn, customer)
            repository.insert_activity(
                conn,
                {
                    "customer_id": customer["customer_id"],
                    "source": "manual",
                    "channel": "system",
                    "activity_type": "profile",
                    "occurred_at": customer["created_at"],
                    "raw_content": "",
                    "structured_summary": "建立模拟客户档案。",
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
