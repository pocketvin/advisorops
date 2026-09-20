import sqlite3
import tempfile
import unittest
from pathlib import Path

from app.db import connect, init_db


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tempdir.name) / "db-test.sqlite"

    def tearDown(self):
        self.tempdir.cleanup()

    def test_sqlite_uses_wal_and_foreign_keys(self):
        init_db(self.db_path)
        with connect(self.db_path) as conn:
            journal_mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
            foreign_keys = conn.execute("PRAGMA foreign_keys").fetchone()[0]

        self.assertEqual(journal_mode.lower(), "wal")
        self.assertEqual(foreign_keys, 1)

    def test_legacy_demo_schema_is_rebuilt(self):
        raw = sqlite3.connect(self.db_path)
        raw.execute(
            """
            CREATE TABLE customers (
                customer_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                stage TEXT NOT NULL
            )
            """
        )
        raw.execute(
            "INSERT INTO customers(customer_id, name, stage) VALUES ('OLD', '旧数据', 'contacted')"
        )
        raw.commit()
        raw.close()

        init_db(self.db_path)

        with connect(self.db_path) as conn:
            columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(customers)").fetchall()
            }
            count = conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]

        self.assertIn("relationship_stage", columns)
        self.assertNotIn("stage", columns)
        self.assertEqual(count, 0)


if __name__ == "__main__":
    unittest.main()
