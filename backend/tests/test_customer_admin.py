import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from app.db import connect
from app.service import CustomerNotFoundError, WorkbenchService


NOW = datetime(2026, 9, 20, 9, 30, tzinfo=timezone.utc)


class CustomerAdminTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tempdir.name) / "admin.db"
        self.service = WorkbenchService(
            db_path=self.db_path,
            clock=lambda: NOW,
        )

    def tearDown(self):
        self.tempdir.cleanup()

    def test_import_preview_normalizes_chinese_headers_and_values(self):
        csv_text = """客户编号,姓名,年龄段,客户等级,风险等级,关系阶段,当前意向,居住区域,职业,兴趣
NEW-001,林示例,35-45,金卡,c3,考虑中,高意向,杭州·西湖,产品经理,旅行|阅读
"""
        preview = self.service.preview_customer_import(csv_text)
        self.assertEqual(preview["summary"]["valid"], 1)
        row = preview["rows"][0]
        self.assertEqual(row["normalized"]["customer_level"], "Gold")
        self.assertEqual(row["normalized"]["risk_level"], "C3")
        self.assertEqual(row["normalized"]["relationship_stage"], "considering")
        self.assertEqual(row["normalized"]["intent_level"], "high")
        self.assertEqual(
            row["normalized"]["profile"]["demographics"]["occupation"],
            "产品经理",
        )
        self.assertEqual(
            row["normalized"]["profile"]["relationship_context"]["interests"],
            ["旅行", "阅读"],
        )

    def test_import_generates_id_and_records_import_activity(self):
        csv_text = """姓名,服务层级,风险等级,当前需求
导入客户,Platinum,C4,确认长期资金安排
"""
        result = self.service.commit_customer_import(csv_text)
        self.assertEqual(result["imported_count"], 1)
        customer_id = result["imported_customer_ids"][0]
        self.assertTrue(customer_id.startswith("IMP-"))

        detail = self.service.customer_detail(customer_id)
        self.assertEqual(detail["customer"]["name"], "导入客户")
        self.assertTrue(
            any(
                event["source"] == "import"
                and event["action_taken"] == "批量导入"
                for event in detail["activities"]
            )
        )

    def test_existing_customer_id_is_preview_error_and_not_imported(self):
        csv_text = """customer_id,name
C001,重复客户
"""
        preview = self.service.preview_customer_import(csv_text)
        self.assertEqual(preview["summary"]["invalid"], 1)
        self.assertIn("客户编号已存在", preview["rows"][0]["errors"][0])
        with self.assertRaises(ValueError):
            self.service.commit_customer_import(csv_text)

    def test_bulk_delete_removes_customer_and_cascades_related_records(self):
        csv_text = """customer_id,name
DELETE-001,待删除客户
"""
        self.service.commit_customer_import(csv_text)
        work = self.service.ensure_manual_work("DELETE-001")
        self.assertEqual(work["customer_id"], "DELETE-001")

        result = self.service.bulk_delete_customers(
            ["DELETE-001"],
            confirm=True,
        )
        self.assertEqual(result["deleted_count"], 1)

        with self.assertRaises(CustomerNotFoundError):
            self.service.customer_detail("DELETE-001")

        with connect(self.db_path) as conn:
            work_count = conn.execute(
                "SELECT COUNT(*) FROM work_items WHERE customer_id = ?",
                ("DELETE-001",),
            ).fetchone()[0]
            activity_count = conn.execute(
                "SELECT COUNT(*) FROM activity_events WHERE customer_id = ?",
                ("DELETE-001",),
            ).fetchone()[0]
        self.assertEqual(work_count, 0)
        self.assertEqual(activity_count, 0)

    def test_bulk_delete_requires_explicit_confirmation(self):
        with self.assertRaises(ValueError):
            self.service.bulk_delete_customers(
                ["C001"],
                confirm=False,
            )


if __name__ == "__main__":
    unittest.main()
