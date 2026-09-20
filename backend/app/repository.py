import json
import sqlite3
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple


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


def update_activity(
    conn: sqlite3.Connection,
    activity_id: int,
    updates: Mapping[str, Any],
) -> None:
    if not updates:
        return
    payload = dict(updates)
    if "metadata" in payload:
        payload["metadata_json"] = json.dumps(
            payload.pop("metadata"),
            ensure_ascii=False,
            separators=(",", ":"),
        )
    assignments = ", ".join(f"{field} = ?" for field in payload)
    conn.execute(
        f"UPDATE activity_events SET {assignments} WHERE id = ?",
        (*payload.values(), activity_id),
    )


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


def insert_change_proposal(
    conn: sqlite3.Connection,
    proposal: Mapping[str, Any],
) -> int:
    payload = dict(proposal)
    payload["proposed_changes_json"] = json.dumps(
        payload.pop("proposed_changes"),
        ensure_ascii=False,
        separators=(",", ":"),
    )
    columns = ", ".join(payload.keys())
    placeholders = ", ".join(["?"] * len(payload))
    cursor = conn.execute(
        f"INSERT INTO change_proposals ({columns}) VALUES ({placeholders})",
        tuple(payload.values()),
    )
    return int(cursor.lastrowid)


def _proposal_from_row(row: sqlite3.Row) -> Dict[str, Any]:
    item = dict(row)
    item["proposed_changes"] = json.loads(
        item.pop("proposed_changes_json") or "{}"
    )
    return item


def get_change_proposal(
    conn: sqlite3.Connection,
    proposal_id: int,
) -> Optional[Dict[str, Any]]:
    row = conn.execute(
        "SELECT * FROM change_proposals WHERE id = ?",
        (proposal_id,),
    ).fetchone()
    return _proposal_from_row(row) if row else None


def list_change_proposals(
    conn: sqlite3.Connection,
    *,
    customer_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    clauses: List[str] = []
    params: List[Any] = []
    if customer_id:
        clauses.append("customer_id = ?")
        params.append(customer_id)
    if status:
        clauses.append("status = ?")
        params.append(status)
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    params.append(limit)
    rows = conn.execute(
        f"""
        SELECT * FROM change_proposals
        {where}
        ORDER BY created_at DESC, id DESC
        LIMIT ?
        """,
        params,
    ).fetchall()
    return [_proposal_from_row(row) for row in rows]


def update_change_proposal(
    conn: sqlite3.Connection,
    proposal_id: int,
    updates: Mapping[str, Any],
) -> None:
    if not updates:
        return
    payload = dict(updates)
    if "proposed_changes" in payload:
        payload["proposed_changes_json"] = json.dumps(
            payload.pop("proposed_changes"),
            ensure_ascii=False,
            separators=(",", ":"),
        )
    assignments = ", ".join(f"{field} = ?" for field in payload)
    conn.execute(
        f"UPDATE change_proposals SET {assignments} WHERE id = ?",
        (*payload.values(), proposal_id),
    )


def upsert_sync_state(
    conn: sqlite3.Connection,
    *,
    source: str,
    cursor: int,
    last_attempt_at: Optional[str],
    last_success_at: Optional[str],
    last_error: str,
    last_result_count: int,
) -> None:
    conn.execute(
        """
        INSERT INTO sync_state (
            source, cursor, last_attempt_at, last_success_at,
            last_error, last_result_count
        ) VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(source) DO UPDATE SET
            cursor = excluded.cursor,
            last_attempt_at = excluded.last_attempt_at,
            last_success_at = excluded.last_success_at,
            last_error = excluded.last_error,
            last_result_count = excluded.last_result_count
        """,
        (
            source,
            cursor,
            last_attempt_at,
            last_success_at,
            last_error,
            last_result_count,
        ),
    )


def get_sync_state(
    conn: sqlite3.Connection,
    source: str,
) -> Optional[Dict[str, Any]]:
    row = conn.execute(
        "SELECT * FROM sync_state WHERE source = ?",
        (source,),
    ).fetchone()
    return row_to_dict(row)


def list_sync_states(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM sync_state ORDER BY source"
    ).fetchall()
    return [dict(row) for row in rows]


def insert_external_event(
    conn: sqlite3.Connection,
    event: Mapping[str, Any],
) -> None:
    payload = dict(event)
    payload["payload_json"] = json.dumps(
        payload.pop("payload", {}),
        ensure_ascii=False,
        separators=(",", ":"),
    )
    columns = ", ".join(payload.keys())
    placeholders = ", ".join(["?"] * len(payload))
    conn.execute(
        f"INSERT OR IGNORE INTO external_events ({columns}) VALUES ({placeholders})",
        tuple(payload.values()),
    )


def fetch_external_events(
    conn: sqlite3.Connection,
    source: str,
    cursor: int,
    *,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT * FROM external_events
        WHERE source = ? AND sequence_number > ?
        ORDER BY sequence_number ASC
        LIMIT ?
        """,
        (source, cursor, limit),
    ).fetchall()
    items: List[Dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["payload"] = json.loads(item.pop("payload_json") or "{}")
        items.append(item)
    return items


def external_event_ingested(
    conn: sqlite3.Connection,
    source: str,
    source_event_id: str,
) -> bool:
    row = conn.execute(
        """
        SELECT 1 FROM ingested_external_events
        WHERE source = ? AND source_event_id = ?
        LIMIT 1
        """,
        (source, source_event_id),
    ).fetchone()
    return row is not None


def mark_external_event_ingested(
    conn: sqlite3.Connection,
    *,
    source: str,
    source_event_id: str,
    activity_id: int,
    ingested_at: str,
) -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO ingested_external_events (
            source, source_event_id, activity_id, ingested_at
        ) VALUES (?, ?, ?, ?)
        """,
        (source, source_event_id, activity_id, ingested_at),
    )


def set_demo_state(
    conn: sqlite3.Connection,
    key: str,
    value: str,
) -> None:
    conn.execute(
        """
        INSERT INTO demo_state(key, value) VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        (key, value),
    )


def get_demo_state(
    conn: sqlite3.Connection,
    key: str,
    default: str = "",
) -> str:
    row = conn.execute(
        "SELECT value FROM demo_state WHERE key = ?",
        (key,),
    ).fetchone()
    return str(row["value"]) if row else default


def customer_search(
    conn: sqlite3.Connection,
    *,
    search: str = "",
    stage: str = "",
    risk_level: str = "",
    intent: str = "",
    customer_level: str = "",
    total_assets_band: str = "",
) -> List[Dict[str, Any]]:
    clauses: List[str] = []
    params: List[Any] = []

    if search.strip():
        clauses.append(
            "(name LIKE ? OR customer_id LIKE ? OR current_need LIKE ? OR manager_note LIKE ?)"
        )
        value = f"%{search.strip()}%"
        params.extend([value, value, value, value])
    if stage:
        clauses.append("relationship_stage = ?")
        params.append(stage)
    if risk_level:
        clauses.append("risk_level = ?")
        params.append(risk_level)
    if intent:
        clauses.append("intent_level = ?")
        params.append(intent)
    if customer_level:
        clauses.append("customer_level = ?")
        params.append(customer_level)
    if total_assets_band:
        clauses.append("total_assets_band = ?")
        params.append(total_assets_band)

    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    rows = conn.execute(
        f"""
        SELECT * FROM customers
        {where}
        ORDER BY pinned DESC, updated_at DESC, customer_id ASC
        """,
        params,
    ).fetchall()
    result: List[Dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["pinned"] = bool(item["pinned"])
        result.append(item)
    return result


def latest_activities(
    conn: sqlite3.Connection,
    *,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT a.*, c.name
        FROM activity_events a
        JOIN customers c ON c.customer_id = a.customer_id
        WHERE a.activity_type != 'profile'
        ORDER BY a.occurred_at DESC, a.id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    items: List[Dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["metadata"] = json.loads(item.pop("metadata_json") or "{}")
        items.append(item)
    return items


def reset_all(conn: sqlite3.Connection) -> None:
    conn.execute("DELETE FROM ingested_external_events")
    conn.execute("DELETE FROM external_events")
    conn.execute("DELETE FROM sync_state")
    conn.execute("DELETE FROM change_proposals")
    conn.execute("DELETE FROM demo_state")
    conn.execute("DELETE FROM field_change_audit")
    conn.execute("DELETE FROM work_items")
    conn.execute("DELETE FROM activity_events")
    conn.execute("DELETE FROM customers")
