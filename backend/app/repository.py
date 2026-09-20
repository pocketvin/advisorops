import json
from typing import Any, Dict, Iterable, List, Mapping, Optional

from .db import PathLike, connect


CUSTOMER_FIELDS = {
    "name",
    "age_band",
    "customer_level",
    "risk_level",
    "total_assets_band",
    "holdings_json",
    "investable_funds_band",
    "last_login_at",
    "last_trade_at",
    "asset_change_30d_pct",
    "recent_product_interest",
    "recent_consult_topic",
    "last_contact_at",
    "contact_method",
    "historical_contact_count",
    "stage",
    "intent",
    "last_feedback",
    "measures_json",
    "next_step",
    "next_contact_at",
    "manager_note",
    "pinned",
    "pinned_at",
    "updated_at",
}


def _customer_from_row(row: Any) -> Dict[str, Any]:
    item = dict(row)
    item["holdings"] = json.loads(item.pop("holdings_json") or "[]")
    item["measures"] = json.loads(item.pop("measures_json") or "[]")
    item["pinned"] = bool(item["pinned"])
    return item


def _event_from_row(row: Any) -> Dict[str, Any]:
    item = dict(row)
    item["metadata"] = json.loads(item.pop("metadata_json") or "{}")
    return item


def count_customers(db_path: Optional[PathLike] = None) -> int:
    with connect(db_path) as conn:
        row = conn.execute("SELECT COUNT(*) AS count FROM customers").fetchone()
        return int(row["count"])


def list_customers(db_path: Optional[PathLike] = None) -> List[Dict[str, Any]]:
    with connect(db_path) as conn:
        rows = conn.execute("SELECT * FROM customers ORDER BY customer_id").fetchall()
    return [_customer_from_row(row) for row in rows]


def get_customer(customer_id: str, db_path: Optional[PathLike] = None) -> Optional[Dict[str, Any]]:
    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM customers WHERE customer_id = ?",
            (customer_id,),
        ).fetchone()
    return _customer_from_row(row) if row else None


def insert_customer(customer: Mapping[str, Any], db_path: Optional[PathLike] = None) -> None:
    payload = dict(customer)
    payload["holdings_json"] = json.dumps(payload.pop("holdings", []), ensure_ascii=False)
    payload["measures_json"] = json.dumps(payload.pop("measures", []), ensure_ascii=False)
    payload["pinned"] = 1 if payload.get("pinned") else 0
    columns = ", ".join(payload.keys())
    placeholders = ", ".join(["?"] * len(payload))
    with connect(db_path) as conn:
        conn.execute(
            f"INSERT INTO customers ({columns}) VALUES ({placeholders})",
            tuple(payload.values()),
        )


def update_customer(
    customer_id: str,
    updates: Mapping[str, Any],
    db_path: Optional[PathLike] = None,
) -> None:
    clean: Dict[str, Any] = {}
    for key, value in updates.items():
        storage_key = key
        storage_value = value
        if key == "holdings":
            storage_key = "holdings_json"
            storage_value = json.dumps(value or [], ensure_ascii=False)
        elif key == "measures":
            storage_key = "measures_json"
            storage_value = json.dumps(value or [], ensure_ascii=False)
        elif key == "pinned":
            storage_value = 1 if value else 0
        if storage_key in CUSTOMER_FIELDS:
            clean[storage_key] = storage_value
    if not clean:
        return
    assignments = ", ".join(f"{key} = ?" for key in clean)
    values = list(clean.values()) + [customer_id]
    with connect(db_path) as conn:
        conn.execute(
            f"UPDATE customers SET {assignments} WHERE customer_id = ?",
            values,
        )


def add_timeline_event(
    event: Mapping[str, Any],
    db_path: Optional[PathLike] = None,
) -> int:
    payload = dict(event)
    payload["metadata_json"] = json.dumps(payload.pop("metadata", {}), ensure_ascii=False)
    columns = ", ".join(payload.keys())
    placeholders = ", ".join(["?"] * len(payload))
    with connect(db_path) as conn:
        cursor = conn.execute(
            f"INSERT INTO timeline_events ({columns}) VALUES ({placeholders})",
            tuple(payload.values()),
        )
        return int(cursor.lastrowid)


def list_timeline(
    customer_id: str,
    db_path: Optional[PathLike] = None,
) -> List[Dict[str, Any]]:
    with connect(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM timeline_events WHERE customer_id = ? ORDER BY created_at DESC, id DESC",
            (customer_id,),
        ).fetchall()
    return [_event_from_row(row) for row in rows]


def reset_all(db_path: Optional[PathLike] = None) -> None:
    with connect(db_path) as conn:
        conn.execute("DELETE FROM timeline_events")
        conn.execute("DELETE FROM customers")
