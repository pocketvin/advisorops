import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional, Union

PathLike = Union[str, Path]

_DEFAULT_DB = Path(__file__).resolve().parent.parent / "data" / "customer_workbench.db"


def resolve_db_path(db_path: Optional[PathLike] = None) -> Path:
    raw = db_path or os.getenv("WORKBENCH_DB_PATH") or _DEFAULT_DB
    path = Path(raw).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def connect(db_path: Optional[PathLike] = None) -> sqlite3.Connection:
    connection = sqlite3.connect(str(resolve_db_path(db_path)))
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA busy_timeout = 5000")
    return connection


@contextmanager
def transaction(db_path: Optional[PathLike] = None) -> Iterator[sqlite3.Connection]:
    conn = connect(db_path)
    try:
        conn.execute("BEGIN")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: Optional[PathLike] = None) -> None:
    with connect(db_path) as conn:
        existing_columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(customers)").fetchall()
        }
        if existing_columns and "relationship_stage" not in existing_columns:
            # V1 仍是可重建的纯 Demo 数据；早期 scaffold schema 直接清掉，
            # 避免旧本地数据库让新业务模型启动失败。
            conn.executescript(
                "DROP TABLE IF EXISTS timeline_events; DROP TABLE IF EXISTS customers;"
            )

        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS customers (
                customer_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                age_band TEXT NOT NULL,
                customer_level TEXT NOT NULL,
                risk_level TEXT NOT NULL,
                total_assets_band TEXT NOT NULL,
                investable_funds_band TEXT NOT NULL,
                profile_json TEXT NOT NULL DEFAULT '{}',
                profile_hypotheses_json TEXT NOT NULL DEFAULT '[]',
                holdings_summary TEXT NOT NULL DEFAULT '',
                recent_login_at TEXT,
                recent_trade_at TEXT,
                asset_change_30d_pct REAL NOT NULL DEFAULT 0,
                recent_product_interest TEXT NOT NULL DEFAULT '',
                recent_consult_topic TEXT NOT NULL DEFAULT '',
                relationship_stage TEXT NOT NULL,
                intent_level TEXT NOT NULL,
                current_need TEXT NOT NULL DEFAULT '',
                current_obstacle TEXT NOT NULL DEFAULT '',
                current_progress TEXT NOT NULL DEFAULT '',
                next_step TEXT NOT NULL DEFAULT '',
                next_contact_at TEXT,
                cooldown_until TEXT,
                pinned INTEGER NOT NULL DEFAULT 0,
                manager_note TEXT NOT NULL DEFAULT '',
                last_contact_at TEXT,
                recent_signal TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS activity_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id TEXT NOT NULL,
                source TEXT NOT NULL,
                channel TEXT NOT NULL,
                activity_type TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                raw_content TEXT NOT NULL DEFAULT '',
                structured_summary TEXT NOT NULL DEFAULT '',
                customer_feedback TEXT NOT NULL DEFAULT '',
                action_taken TEXT NOT NULL DEFAULT '',
                next_step TEXT NOT NULL DEFAULT '',
                next_contact_at TEXT,
                stage_after TEXT,
                intent_after TEXT,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                FOREIGN KEY(customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS work_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id TEXT NOT NULL,
                title TEXT NOT NULL,
                status TEXT NOT NULL,
                waiting_on TEXT NOT NULL DEFAULT 'none',
                current_progress TEXT NOT NULL DEFAULT '',
                next_action TEXT NOT NULL DEFAULT '',
                due_at TEXT,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                completion_activity_id INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE,
                FOREIGN KEY(completion_activity_id) REFERENCES activity_events(id)
            );

            CREATE TABLE IF NOT EXISTS field_change_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id TEXT NOT NULL,
                source_activity_id INTEGER,
                field_name TEXT NOT NULL,
                old_value TEXT,
                new_value TEXT,
                changed_by TEXT NOT NULL,
                changed_at TEXT NOT NULL,
                FOREIGN KEY(customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE,
                FOREIGN KEY(source_activity_id) REFERENCES activity_events(id)
            );

            CREATE TABLE IF NOT EXISTS change_proposals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id TEXT NOT NULL,
                activity_id INTEGER,
                status TEXT NOT NULL DEFAULT 'pending',
                source TEXT NOT NULL,
                raw_content TEXT NOT NULL DEFAULT '',
                proposed_changes_json TEXT NOT NULL,
                extraction_summary TEXT NOT NULL DEFAULT '',
                confidence REAL,
                model TEXT,
                created_at TEXT NOT NULL,
                reviewed_at TEXT,
                applied_at TEXT,
                reviewer_note TEXT NOT NULL DEFAULT '',
                FOREIGN KEY(customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE,
                FOREIGN KEY(activity_id) REFERENCES activity_events(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS sync_state (
                source TEXT PRIMARY KEY,
                cursor INTEGER NOT NULL DEFAULT 0,
                last_attempt_at TEXT,
                last_success_at TEXT,
                last_error TEXT NOT NULL DEFAULT '',
                last_result_count INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS external_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                source_event_id TEXT NOT NULL,
                sequence_number INTEGER NOT NULL,
                customer_id TEXT NOT NULL,
                channel TEXT NOT NULL,
                event_kind TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                raw_content TEXT NOT NULL,
                payload_json TEXT NOT NULL DEFAULT '{}',
                UNIQUE(source, source_event_id),
                FOREIGN KEY(customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS ingested_external_events (
                source TEXT NOT NULL,
                source_event_id TEXT NOT NULL,
                activity_id INTEGER NOT NULL,
                ingested_at TEXT NOT NULL,
                PRIMARY KEY(source, source_event_id),
                FOREIGN KEY(activity_id) REFERENCES activity_events(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS demo_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_customers_next_contact
              ON customers(next_contact_at);
            CREATE INDEX IF NOT EXISTS idx_activity_customer_time
              ON activity_events(customer_id, occurred_at DESC);
            CREATE INDEX IF NOT EXISTS idx_work_customer_status
              ON work_items(customer_id, status);
            CREATE INDEX IF NOT EXISTS idx_work_status
              ON work_items(status);
            CREATE INDEX IF NOT EXISTS idx_proposals_customer_status
              ON change_proposals(customer_id, status);
            CREATE INDEX IF NOT EXISTS idx_external_source_sequence
              ON external_events(source, sequence_number);
            """
        )

        # Forward-compatible additive migration for the rebuildable V1 demo DB.
        current_columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(customers)").fetchall()
        }
        additions = {
            "holdings_summary": "TEXT NOT NULL DEFAULT ''",
            "recent_login_at": "TEXT",
            "recent_trade_at": "TEXT",
            "asset_change_30d_pct": "REAL NOT NULL DEFAULT 0",
            "recent_product_interest": "TEXT NOT NULL DEFAULT ''",
            "recent_consult_topic": "TEXT NOT NULL DEFAULT ''",
            "manager_note": "TEXT NOT NULL DEFAULT ''",
            "profile_json": "TEXT NOT NULL DEFAULT '{}'",
            "profile_hypotheses_json": "TEXT NOT NULL DEFAULT '[]'",
        }
        for name, definition in additions.items():
            if name not in current_columns:
                conn.execute(
                    f"ALTER TABLE customers ADD COLUMN {name} {definition}"
                )
