import unittest
from datetime import datetime, timedelta, timezone

from app.priority import evaluate_discovery
from app.time_utils import to_iso


NOW = datetime(2026, 9, 20, 5, 0, tzinfo=timezone.utc)


def customer(**overrides):
    value = {
        "customer_id": "T001",
        "customer_level": "Gold",
        "relationship_stage": "interested",
        "intent_level": "high",
        "last_contact_at": to_iso(NOW - timedelta(days=5)),
        "next_contact_at": None,
        "cooldown_until": None,
        "recent_signal": "",
        "pinned": False,
        "next_step": "",
    }
    value.update(overrides)
    return value


class DiscoveryRuleTests(unittest.TestCase):
    def test_recent_contact_without_new_reason_is_suppressed(self):
        result = evaluate_discovery(
            customer(last_contact_at=to_iso(NOW - timedelta(hours=6))),
            now=NOW,
        )
        self.assertIsNone(result)

    def test_recent_contact_with_new_signal_can_return(self):
        result = evaluate_discovery(
            customer(
                last_contact_at=to_iso(NOW - timedelta(hours=6)),
                recent_signal="新增明显资产变化",
            ),
            now=NOW,
        )
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.actionable_reason, "出现新的客户经营信号")

    def test_future_follow_up_is_not_discovered_early(self):
        result = evaluate_discovery(
            customer(
                relationship_stage="considering",
                intent_level="medium",
                next_contact_at=to_iso(NOW + timedelta(days=3)),
            ),
            now=NOW,
        )
        self.assertIsNone(result)

    def test_overdue_follow_up_has_explicit_reason(self):
        result = evaluate_discovery(
            customer(
                relationship_stage="considering",
                intent_level="medium",
                next_contact_at=to_iso(NOW - timedelta(days=2)),
            ),
            now=NOW,
        )
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.follow_up_state, "overdue")
        self.assertIn("逾期", result.actionable_reason)

    def test_pin_is_sorting_metadata_not_score_points(self):
        result = evaluate_discovery(
            customer(
                pinned=True,
                relationship_stage="contacted",
                intent_level="low",
                next_step="确认当前进度",
            ),
            now=NOW,
        )
        self.assertIsNotNone(result)
        assert result is not None
        self.assertTrue(result.pinned)
        self.assertNotIn("manual_pin", {factor.code for factor in result.factors})
        self.assertLess(result.score, 70)

    def test_malformed_legacy_follow_up_time_does_not_crash_discovery(self):
        result = evaluate_discovery(
            customer(next_contact_at="not-a-date"),
            now=NOW,
        )
        self.assertIsNotNone(result)


if __name__ == "__main__":
    unittest.main()
