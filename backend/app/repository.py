import json
import sqlite3
from typing import Any, Dict, Iterable, List, Mapping, Optional


ACTIVE_WORK_STATUSES = ("action_required", "waiting")


def row_to_dict(row: Optional[sqlite3.Row]) -> Optional[Dict[str, Any]]:
    return dict(row) if row is not None else None


def get_customer(conn: sqlite3.Connection, customer_id: str) -> Optional[Dict[str, Any]]:
    row = conn.execute(
        "SELECT * FROM customers WHERE customer_id = ?",
        (customer_id,),
    ).fetchone()
    item = row_to_dict(row)
    if item is not None:
        item["pinned"] = bool(item["pinned"])
    return item


def list_customers(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    rows = conn.execute("SELECT * FROM customers ORDER BY customer_id").fetchall()
    result: List[Dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["pinned"] = bool(item["pinned"])
        result.append(item)
    return result


def insert_customer(conn: sqlite3.Connection, customer: Mapping[str, Any]) -> None:
    payload = dict(customer)
    payload["pinned"] = 1 if payload.get("pinned") else 0
    columns = ", ".join(payload.keys())
    placeholders = ", ".join(["?"] * len(payload))
    conn.execute(
        f"INSERT INTO customers ({columns}) VALUES ({placeholders})",
        tuple(payload.values()),
    )


def update_customer(
    conn: sqlite3.Connection,
    customer_id: str,
    updates: Mapping[str, Any],
) -> None:
    if not updates:
        return
    payload = dict(updates)
    if "pinned" in payload:
        payload["pinned"] = 1 if payload["pinned"] else 0
    assignments = ", ".join(f"{field} = ?" for field in payload)
    conn.execute(
        f"UPDATE customers SET {assignments} WHERE customer_id = ?",
        (*payload.values(), customer_id),
    )


def insert_activity(conn: sqlite3.Connection, activity: Mapping[str, Any]) -> int:
    payload = dict(activity)
    payload["metadata_json"] = json.dumps(
        payload.pop("metadata", {}),
        ensure_ascii=False,
        separators=(",", ":"),
    )
    columns = ", ".join(payload.keys())
    placeholders = ", ".join(["?"] * len(payload))
    cursor = conn.execute(
        f"INSERT INTO activity_events ({columns}) VALUES ({placeholders})",
        tuple(payload.values()),
    )
    return int(cursor.lastrowid)


def list_activities(
    conn: sqlite3.Connection,
    customer_id: str,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT * FROM activity_events
        WHERE customer_id = ?
        ORDER BY occurred_at DESC, id DESC
        LIMIT ?
        """,
        (customer_id, limit),
    ).fetchall()
    items: List[Dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["metadata"] = json.loads(item.pop("metadata_json") or "{}")
        items.append(item)
    return items


def create_work_item(conn: sqlite3.Connection, work_item: Mapping[str, Any]) -> int:
    payload = dict(work_item)
    columns = ", ".join(payload.keys())
    placeholders = ", ".join(["?"] * len(payload))
    cursor = conn.execute(
        f"INSERT INTO work_items ({columns}) VALUES ({placeholders})",
        tuple(payload.values()),
    )
    return int(cursor.lastrowid)


def get_work_item(conn: sqlite3.Connection, work_item_id: int) -> Optional[Dict[str, Any]]:
    row = conn.execute(
        "SELECT * FROM work_items WHERE id = ?",
        (work_item_id,),
    ).fetchone()
    return row_to_dict(row)


def get_active_work_for_customer(
    conn: sqlite3.Connection,
    customer_id: str,
) -> Optional[Dict[str, Any]]:
    placeholders = ",".join("?" for _ in ACTIVE_WORK_STATUSES)
    row = conn.execute(
        f"""
        SELECT * FROM work_items
        WHERE customer_id = ?
          AND status IN ({placeholders})
        ORDER BY id DESC
        LIMIT 1
        """,
        (customer_id, *ACTIVE_WORK_STATUSES),
    ).fetchone()
    return row_to_dict(row)


def list_active_work(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    placeholders = ",".join("?" for _ in ACTIVE_WORK_STATUSES)
    rows = conn.execute(
        f"""
        SELECT w.*, c.name, c.customer_level, c.relationship_stage, c.intent_level,
               c.last_contact_at, c.current_progress AS customer_progress,
               c.next_step AS customer_next_step
        FROM work_items w
        JOIN customers c ON c.customer_id = w.customer_id
        WHERE w.status IN ({placeholders})
        ORDER BY
          CASE w.status WHEN 'action_required' THEN 0 ELSE 1 END,
          COALESCE(w.due_at, '9999') ASC,
          w.started_at ASC
        """,
        ACTIVE_WORK_STATUSES,
    ).fetchall()
    return [dict(row) for row in rows]


def list_completed_today(
    conn: sqlite3.Connection,
    start_utc: str,
    end_utc: str,
) -> List[Dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT w.*, c.name, c.customer_level, c.relationship_stage, c.intent_level,
               c.last_contact_at
        FROM work_items w
        JOIN customers c ON c.customer_id = w.customer_id
        WHERE w.status = 'completed_today'
          AND w.completed_at >= ?
          AND w.completed_at < ?
        ORDER BY w.completed_at DESC
        """,
        (start_utc, end_utc),
    ).fetchall()
    return [dict(row) for row in rows]


def customer_completed_in_window(
    conn: sqlite3.Connection,
    customer_id: str,
    start_utc: str,
    end_utc: str,
) -> bool:
    row = conn.execute(
        """
        SELECT 1 FROM work_items
        WHERE customer_id = ?
          AND status = 'completed_today'
          AND completed_at >= ?
          AND completed_at < ?
        LIMIT 1
        """,
        (customer_id, start_utc, end_utc),
    ).fetchone()
    return row is not None


def update_work_item(
    conn: sqlite3.Connection,
    work_item_id: int,
    updates: Mapping[str, Any],
) -> None:
    if not updates:
        return
    assignments = ", ".join(f"{field} = ?" for field in updates)
    conn.execute(
        f"UPDATE work_items SET {assignments} WHERE id = ?",
        (*updates.values(), work_item_id),
    )


def insert_audits(
    conn: sqlite3.Connection,
    audits: Iterable[Mapping[str, Any]],
) -> None:
    for audit in audits:
        conn.execute(
            """
            INSERT INTO field_change_audit (
                customer_id,
                source_activity_id,
                field_name,
                old_value,
                new_value,
                changed_by,
                changed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                audit["customer_id"],
                audit.get("source_activity_id"),
                audit["field_name"],
                audit.get("old_value"),
                audit.get("new_value"),
                audit["changed_by"],
                audit["changed_at"],
            ),
        )


def list_audits(
    conn: sqlite3.Connection,
    customer_id: str,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT * FROM field_change_audit
        WHERE customer_id = ?
        ORDER BY changed_at DESC, id DESC
        LIMIT ?
        """,
        (customer_id, limit),
    ).fetchall()
    return [dict(row) for row in rows]


def reset_all(conn: sqlite3.Connection) -> None:
    conn.execute("DELETE FROM field_change_audit")
    conn.execute("DELETE FROM work_items")
    conn.execute("DELETE FROM activity_events")
    conn.execute("DELETE FROM customers")
