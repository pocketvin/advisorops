import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.service import InvalidWorkStateError, WorkbenchService
from app.time_utils import to_iso


FIXED_NOW = datetime(2026, 9, 20, 5, 0, tzinfo=timezone.utc)


class Phase1WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tempdir.name) / "phase1.db"
        self.service = WorkbenchService(
            db_path=self.db_path,
            clock=lambda: FIXED_NOW,
        )

    def tearDown(self):
        self.tempdir.cleanup()

    def _discovery_ids(self):
        return [
            item["customer"]["customer_id"]
            for item in self.service.workbench()["discovery"]
        ]

    def test_initial_workbench_has_discovery_but_no_active_work(self):
        workbench = self.service.workbench()

        self.assertEqual(workbench["summary"]["action_required"], 1)
        self.assertEqual(workbench["summary"]["waiting"], 2)
        self.assertEqual(workbench["summary"]["completed_today"], 1)
        self.assertIn("C001", self._discovery_ids())
        self.assertIn("C002", self._discovery_ids())
        self.assertNotIn("C003", self._discovery_ids())

    def test_starting_discovery_moves_customer_into_work_area(self):
        work_item = self.service.start_work("C001")
        workbench = self.service.workbench()

        self.assertEqual(work_item["status"], "action_required")
        self.assertNotIn("C001", self._discovery_ids())
        action_ids = [
            item["customer_id"]
            for item in workbench["work_area"]["action_required"]
        ]
        self.assertIn("C001", action_ids)
        self.assertEqual(action_ids.count("C001"), 1)

    def test_completed_interaction_keeps_raw_record_and_updates_snapshot(self):
        work_item = self.service.start_work("C001")
        future_contact = to_iso(FIXED_NOW + timedelta(days=3))

        result = self.service.record_interaction(
            work_item["id"],
            {
                "raw_content": "刚刚跟张总电话沟通，他说方案看过了，但这几天先考虑，三天后再联系。",
                "structured_summary": "客户已查看方案，仍需三天考虑，约定三天后电话回访。",
                "customer_feedback": "再考虑三天。",
                "action_taken": "电话回访",
                "relationship_stage": "considering",
                "intent_level": "medium",
                "current_need": "继续确认资金使用期限与流动性需求",
                "current_obstacle": "客户仍需时间考虑",
                "next_step": "三天后按约定回访",
                "next_contact_at": future_contact,
                "channel": "phone",
                "outcome": "completed",
                "waiting_on": "none",
            },
        )

        self.assertEqual(result["work_item"]["status"], "completed_today")
        self.assertEqual(result["customer"]["intent_level"], "medium")
        self.assertEqual(result["customer"]["next_contact_at"], future_contact)

        workbench = self.service.workbench()
        self.assertNotIn("C001", self._discovery_ids())
        completed_ids = [
            item["customer_id"]
            for item in workbench["work_area"]["completed_today"]
        ]
        self.assertIn("C001", completed_ids)
        self.assertEqual(completed_ids.count("C001"), 1)

        detail = self.service.customer_detail("C001")
        interaction = next(
            item for item in detail["activities"] if item["activity_type"] == "interaction"
        )
        self.assertIn("刚刚跟张总电话沟通", interaction["raw_content"])
        self.assertEqual(
            interaction["structured_summary"],
            "客户已查看方案，仍需三天考虑，约定三天后电话回访。",
        )
        changed_fields = {item["field_name"] for item in detail["field_changes"]}
        self.assertIn("intent_level", changed_fields)
        self.assertIn("next_contact_at", changed_fields)

    def test_waiting_outcome_stays_in_work_area_and_not_discovery(self):
        work_item = self.service.start_work("C002")
        check_time = to_iso(FIXED_NOW + timedelta(days=1))

        result = self.service.record_interaction(
            work_item["id"],
            {
                "raw_content": "给陈女士发了资料，她说晚上看一下，明天回复。",
                "structured_summary": "已发送资料，等待客户明天反馈。",
                "customer_feedback": "晚上看一下，明天回复。",
                "action_taken": "发送资料",
                "relationship_stage": "contacted",
                "intent_level": "medium",
                "current_need": "确认近期资金安排变化",
                "current_obstacle": "",
                "next_step": "明天检查客户反馈",
                "next_contact_at": check_time,
                "channel": "wecom",
                "outcome": "waiting",
                "waiting_on": "customer",
            },
        )

        self.assertEqual(result["work_item"]["status"], "waiting")
        self.assertEqual(result["work_item"]["waiting_on"], "customer")

        workbench = self.service.workbench()
        self.assertNotIn("C002", self._discovery_ids())
        waiting_ids = [
            item["customer_id"]
            for item in workbench["work_area"]["waiting"]
        ]
        self.assertIn("C002", waiting_ids)
        self.assertEqual(waiting_ids.count("C002"), 1)

    def test_customer_without_actionable_reason_cannot_be_started(self):
        with self.assertRaises(InvalidWorkStateError):
            self.service.start_work("C003")

    def test_invalid_interaction_does_not_partially_update_customer(self):
        work_item = self.service.start_work("C001")
        before = self.service.customer_detail("C001")["customer"]

        with self.assertRaises(ValueError):
            self.service.record_interaction(
                work_item["id"],
                {
                    "raw_content": "",
                    "structured_summary": "不应该保存",
                    "relationship_stage": "rejected",
                    "intent_level": "low",
                    "outcome": "completed",
                },
            )

        after = self.service.customer_detail("C001")["customer"]
        self.assertEqual(before["relationship_stage"], after["relationship_stage"])
        self.assertEqual(before["intent_level"], after["intent_level"])


if __name__ == "__main__":
    unittest.main()
