import os
import sqlite3
from pathlib import Path
from typing import Optional, Union

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
    return connection


def init_db(db_path: Optional[PathLike] = None) -> None:
    with connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS customers (
                customer_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                age_band TEXT NOT NULL,
                customer_level TEXT NOT NULL,
                risk_level TEXT NOT NULL,
                total_assets_band TEXT NOT NULL,
                holdings_json TEXT NOT NULL DEFAULT '[]',
                investable_funds_band TEXT NOT NULL,
                last_login_at TEXT,
                last_trade_at TEXT,
                asset_change_30d_pct REAL NOT NULL DEFAULT 0,
                recent_product_interest TEXT NOT NULL DEFAULT '',
                recent_consult_topic TEXT NOT NULL DEFAULT '',
                last_contact_at TEXT,
                contact_method TEXT NOT NULL DEFAULT '',
                historical_contact_count INTEGER NOT NULL DEFAULT 0,
                stage TEXT NOT NULL,
                intent TEXT NOT NULL,
                last_feedback TEXT NOT NULL DEFAULT '',
                measures_json TEXT NOT NULL DEFAULT '[]',
                next_step TEXT NOT NULL DEFAULT '',
                next_contact_at TEXT,
                manager_note TEXT NOT NULL DEFAULT '',
                pinned INTEGER NOT NULL DEFAULT 0,
                pinned_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS timeline_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                title TEXT NOT NULL,
                detail TEXT NOT NULL DEFAULT '',
                feedback TEXT NOT NULL DEFAULT '',
                stage_after TEXT,
                next_contact_at TEXT,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                FOREIGN KEY(customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_customers_stage ON customers(stage);
            CREATE INDEX IF NOT EXISTS idx_customers_next_contact ON customers(next_contact_at);
            CREATE INDEX IF NOT EXISTS idx_timeline_customer ON timeline_events(customer_id, created_at DESC);
            """
        )
