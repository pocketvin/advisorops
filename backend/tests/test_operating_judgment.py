import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from app.service import WorkbenchService


NOW = datetime(2026, 9, 20, 10, 0, tzinfo=timezone.utc)


class OperatingJudgmentTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tempdir.name) / "judgment.db"
        self.service = WorkbenchService(
            db_path=self.db_path,
            clock=lambda: NOW,
        )

    def tearDown(self):
        self.tempdir.cleanup()

    def test_customer_detail_includes_explainable_judgment(self):
        detail = self.service.customer_detail("C004")
        judgment = detail["operating_judgment"]

        self.assertEqual(judgment["mode"], "deterministic")
        self.assertIn("高意向", judgment["current_state"]["text"])
        self.assertIn(
            "明确长期资金用途和可投资期限",
            judgment["core_concern"]["text"],
        )
        self.assertIn("资金用途", judgment["next_confirmation"]["text"])
        self.assertEqual(judgment["action_brief"]["mode"], "contact")
        self.assertIn("资金", judgment["action_brief"]["objective"])
        self.assertGreaterEqual(len(judgment["action_brief"]["questions"]), 3)
        self.assertIn("流动性", judgment["action_brief"]["completion_criteria"])
        self.assertTrue(judgment["current_state"]["evidence"])
        self.assertTrue(judgment["core_concern"]["evidence"])

    def test_waiting_customer_avoids_repeated_pressure(self):
        judgment = self.service.customer_detail("C005")["operating_judgment"]

        self.assertIn("等待客户", judgment["current_state"]["text"])
        self.assertIn("先等待客户", judgment["communication_approach"]["text"])
        self.assertEqual(judgment["action_brief"]["mode"], "wait")
        self.assertEqual(judgment["action_brief"]["questions"], [])
        self.assertIn("不重复催促", judgment["action_brief"]["completion_criteria"])
        self.assertIn("避免", judgment["avoid_action"]["text"])
        self.assertIn("重复", judgment["avoid_action"]["text"])

    def test_rejected_customer_keeps_low_pressure_boundary(self):
        judgment = self.service.customer_detail("C008")["operating_judgment"]

        self.assertIn("明确拒绝", judgment["current_state"]["text"])
        self.assertIn("没有主动经营需求", judgment["core_concern"]["text"])
        self.assertIn("产品推介", judgment["avoid_action"]["text"])
        self.assertEqual(judgment["action_brief"]["mode"], "wait")
        self.assertIn("冷静期", judgment["action_brief"]["objective"])
        self.assertIn("低打扰", judgment["next_confirmation"]["text"])
        self.assertIn("不主动营销触达", judgment["communication_approach"]["text"])

    def test_hypothesis_is_labeled_as_hypothesis_evidence(self):
        judgment = self.service.customer_detail("C010")["operating_judgment"]
        hypothesis_evidence = [
            item
            for item in judgment["decision_barrier"]["evidence"]
            if item["kind"] == "hypothesis"
        ]
        self.assertTrue(hypothesis_evidence)

    def test_judgment_is_read_only(self):
        before = self.service.customer_detail("C001")["customer"]
        _ = self.service.customer_detail("C001")["operating_judgment"]
        after = self.service.customer_detail("C001")["customer"]
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
