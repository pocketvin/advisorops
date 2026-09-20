import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.ai_client import KimiResult
from app.ai_service import AIService
from app.db import connect
from app.service import WorkbenchService
from app.sync_service import SyncService


NOW = datetime(2026, 9, 20, 6, 30, tzinfo=timezone.utc)


class FakeKimiClient:
    configured = True

    def __init__(self):
        self.last_images = []

    def status(self):
        return {
            "configured": True,
            "model": "kimi-k3-test",
            "source": "test",
            "base_url": "https://example.invalid/v1",
        }

    def json_schema(self, **kwargs):
        self.last_images = list(kwargs.get("images") or [])
        schema_name = kwargs["schema_name"]
        if schema_name == "interaction_extraction":
            return KimiResult(
                data={
                    "structured_summary": "客户近期可能有资金使用需求，希望十月后再联系。",
                    "customer_feedback": "十月以后再联系。",
                    "relationship_stage": "considering",
                    "intent_level": "medium",
                    "current_need": "确认近期资金使用安排",
                    "current_obstacle": "近期可能有资金支出",
                    "next_step": "十月后重新确认资金安排",
                    "next_contact_at": "2026-10-01T09:00:00+08:00",
                    "outcome": "completed",
                    "waiting_on": "none",
                    "reasoning_summary": "客户明确要求延后联系并提到近期资金用途。",
                    "confidence": 0.93,
                },
                model="kimi-k3-test",
                usage={"total_tokens": 123},
            )
        if schema_name == "customer_brief":
            return KimiResult(
                data={
                    "summary": "客户正在考虑方案，近期关注流动性。",
                    "main_focus": "流动性与资金使用时间",
                    "current_obstacle": "仍需时间考虑",
                    "unresolved_questions": ["具体资金使用时间"],
                    "next_conversation_focus": "先确认资金使用时间是否变化",
                },
                model="kimi-k3-test",
                usage={},
            )
        raise AssertionError(schema_name)


class V1FeatureTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tempdir.name) / "v1.db"
        self.previous_attachments_dir = os.environ.get("WORKBENCH_ATTACHMENTS_DIR")
        os.environ["WORKBENCH_ATTACHMENTS_DIR"] = str(
            Path(self.tempdir.name) / "attachments"
        )
        self.service = WorkbenchService(
            db_path=self.db_path,
            clock=lambda: NOW,
        )
        self.fake_ai = AIService(
            db_path=self.db_path,
            client=FakeKimiClient(),
        )
        self.service.ai = self.fake_ai
        self.service.sync = SyncService(
            db_path=self.db_path,
            ai_service=self.fake_ai,
        )

    def tearDown(self):
        if self.previous_attachments_dir is None:
            os.environ.pop("WORKBENCH_ATTACHMENTS_DIR", None)
        else:
            os.environ["WORKBENCH_ATTACHMENTS_DIR"] = self.previous_attachments_dir
        self.tempdir.cleanup()

    def test_seed_has_40_fixed_customers(self):
        customers = self.service.customers()
        self.assertEqual(len(customers), 40)
        self.assertEqual(customers[0]["customer"]["customer_id"][:1], "C")

    def test_seed_profiles_are_rich_and_separate_hypotheses(self):
        customer = self.service.customer_detail("C001")["customer"]
        profile = customer["profile"]
        self.assertIn("demographics", profile)
        self.assertIn("family_and_life", profile)
        self.assertIn("financial_context", profile)
        self.assertIn("investment_context", profile)
        self.assertIn("service_preferences", profile)
        self.assertIn("relationship_context", profile)
        self.assertTrue(customer["profile_hypotheses"])
        self.assertEqual(
            customer["profile_hypotheses"][0]["status"],
            "needs_validation",
        )

    def test_customer_search_includes_rich_profile_text(self):
        results = self.service.customers(search="软件工程师")
        self.assertTrue(results)
        self.assertTrue(
            any(
                item["customer"]["profile"]["demographics"]["occupation"]
                == "软件工程师"
                for item in results
            )
        )

    def test_context_pack_uses_rich_profile_but_redacts_precise_address(self):
        pack = self.service.ai_context("C001")
        self.assertIn("【财务与投资背景】", pack["text"])
        self.assertIn("【沟通与关系画像】", pack["text"])
        self.assertIn("【待验证经营假设】", pack["text"])
        self.assertIn("precise_address", pack["redacted_fields"])

    def test_public_service_tier_names_replace_unfounded_card_labels(self):
        customers = self.service.customers()
        tiers = {item["customer"]["customer_level"] for item in customers}
        self.assertTrue(tiers)
        self.assertTrue(
            tiers.issubset(
                {"Gold", "Platinum", "Black Gold", "Diamond", "Black Diamond"}
            )
        )

    def test_global_quick_record_resolves_customer_name_before_ai(self):
        prepared = self.service.quick_record_prepare(
            raw_content="周婷刚刚说资料已经看过了，明天下午回复我。",
            channel="phone",
        )
        self.assertEqual(prepared["customer"]["customer_id"], "C005")
        self.assertTrue(prepared["ai_ready"])
        self.assertIn("suggested_interaction", prepared)

    def test_global_quick_record_requires_one_explicit_customer(self):
        with self.assertRaises(ValueError):
            self.service.quick_record_prepare(
                raw_content="刚刚客户说资料看过了，明天回复。",
                channel="phone",
            )
        with self.assertRaises(ValueError):
            self.service.quick_record_prepare(
                raw_content="张明远和周婷今天都联系过了。",
                channel="phone",
            )

    def test_quick_record_passes_image_to_vision_model(self):
        tiny_png = (
            "data:image/png;base64,"
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl7fHIAAAAASUVORK5CYII="
        )
        prepared = self.service.quick_record_prepare(
            raw_content="周婷刚刚发来聊天截图。",
            channel="wecom",
            attachments=[
                {
                    "name": "chat.png",
                    "mime_type": "image/png",
                    "data_url": tiny_png,
                }
            ],
        )
        self.assertTrue(prepared["ai_ready"])
        self.assertEqual(len(self.fake_ai.client.last_images), 1)

    def test_record_interaction_persists_attachment_metadata_and_file(self):
        tiny_png = (
            "data:image/png;base64,"
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl7fHIAAAAASUVORK5CYII="
        )
        work = self.service.start_work("C001")
        self.service.record_interaction(
            work["id"],
            {
                "raw_content": "客户发来截图并补充说明。",
                "structured_summary": "客户通过截图补充了本次沟通信息。",
                "customer_feedback": "",
                "action_taken": "记录图片沟通",
                "relationship_stage": "considering",
                "intent_level": "medium",
                "current_need": "继续确认后续安排",
                "current_obstacle": "",
                "next_step": "按约定继续沟通",
                "next_contact_at": None,
                "channel": "wecom",
                "outcome": "completed",
                "waiting_on": "none",
                "attachments": [
                    {
                        "name": "chat.png",
                        "mime_type": "image/png",
                        "data_url": tiny_png,
                    }
                ],
            },
        )
        detail = self.service.customer_detail("C001")
        interaction = next(
            item for item in detail["activities"] if item["activity_type"] == "interaction"
        )
        saved = interaction["metadata"]["attachments"]
        self.assertEqual(len(saved), 1)
        self.assertTrue(saved[0]["url"].startswith("/attachments/"))
        self.assertEqual(
            len(list((Path(self.tempdir.name) / "attachments").glob("*.png"))),
            1,
        )

    def test_defer_supports_specific_follow_up_time(self):
        target = NOW + timedelta(days=2, hours=3)
        updated = self.service.defer_customer(
            "C002",
            days=None,
            next_contact_at=target.isoformat(),
        )
        self.assertEqual(updated["next_contact_at"], target.isoformat().replace("+00:00", "Z"))
        self.assertIn("重新跟进", updated["next_step"])

    def test_demo_time_advance_releases_scheduled_customer(self):
        before = {
            item["customer"]["customer_id"]
            for item in self.service.workbench()["discovery"]
        }
        self.assertNotIn("C003", before)

        result = self.service.advance_demo_time(days=3)
        after = {
            item["customer"]["customer_id"]
            for item in result["workbench"]["discovery"]
        }
        self.assertIn("C003", after)

    def test_ai_proposal_does_not_change_snapshot_until_applied(self):
        before = self.service.customer_detail("C012")["customer"]
        extracted = self.service.ai_extract_interaction(
            "C012",
            raw_content="最近公司要用钱，十月以后再聊。",
            channel="wecom",
        )
        proposal = extracted["proposal"]

        middle = self.service.customer_detail("C012")["customer"]
        self.assertEqual(
            before["relationship_stage"],
            middle["relationship_stage"],
        )
        self.assertEqual(proposal["status"], "pending")

        applied = self.service.apply_change_proposal(proposal["id"])
        self.assertEqual(applied["status"], "applied")
        self.assertEqual(
            applied["customer"]["relationship_stage"],
            "considering",
        )
        self.assertEqual(applied["customer"]["intent_level"], "medium")

    def test_context_pack_redacts_direct_name(self):
        pack = self.service.ai_context("C001", question="下次怎么自然展开沟通？")
        self.assertNotIn("张明远", pack["text"])
        self.assertIn("客户代号：C001", pack["text"])
        self.assertIn("name", pack["redacted_fields"])

    def test_customer_brief_uses_ai_without_mutating_customer(self):
        before = self.service.customer_detail("C001")["customer"]
        brief = self.service.ai_customer_brief("C001")
        after = self.service.customer_detail("C001")["customer"]
        self.assertIn("summary", brief)
        self.assertEqual(before, after)

    def test_sync_refresh_is_incremental_and_behavior_signal_is_discoverable(self):
        first = self.service.refresh_sources()
        self.assertEqual(first["new_count"], 3)
        self.assertEqual(first["pending_proposals_created"], 1)

        c013 = self.service.customer_detail("C013")["customer"]
        self.assertIn("资产增加", c013["recent_signal"])

        discovery_ids = {
            item["customer"]["customer_id"]
            for item in self.service.workbench()["discovery"]
        }
        self.assertIn("C013", discovery_ids)

        second = self.service.refresh_sources()
        self.assertEqual(second["new_count"], 2)

        third = self.service.refresh_sources()
        self.assertEqual(third["new_count"], 0)

        with connect(self.db_path) as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM ingested_external_events"
            ).fetchone()[0]
        self.assertEqual(count, 5)

        feed = self.service.activity_feed()
        self.assertTrue(all(item["activity_type"] != "profile" for item in feed["activities"]))

    def test_manual_work_can_be_created_for_non_discovery_customer(self):
        before = {
            item["customer"]["customer_id"]
            for item in self.service.workbench()["discovery"]
        }
        self.assertNotIn("C003", before)

        work = self.service.ensure_manual_work("C003")
        self.assertEqual(work["status"], "action_required")
        self.assertEqual(work["customer_id"], "C003")

    def test_defer_removes_current_signal_and_hides_customer(self):
        before = {
            item["customer"]["customer_id"]
            for item in self.service.workbench()["discovery"]
        }
        self.assertIn("C002", before)

        updated = self.service.defer_customer("C002", 3)
        self.assertEqual(updated["recent_signal"], "")

        after = {
            item["customer"]["customer_id"]
            for item in self.service.workbench()["discovery"]
        }
        self.assertNotIn("C002", after)

    def test_rejected_interaction_enters_30_day_cooldown(self):
        work = self.service.start_work("C001")
        result = self.service.record_interaction(
            work["id"],
            {
                "raw_content": "客户明确表示近期没有需求，先不要联系。",
                "structured_summary": "客户明确拒绝近期主动跟进。",
                "customer_feedback": "近期没有需求，先不要联系。",
                "action_taken": "电话回访",
                "relationship_stage": "rejected",
                "intent_level": "low",
                "current_need": "暂无主动经营需求",
                "current_obstacle": "客户明确拒绝",
                "next_step": "",
                "next_contact_at": None,
                "channel": "phone",
                "outcome": "completed",
                "waiting_on": "none",
            },
        )
        customer = result["customer"]
        self.assertEqual(customer["relationship_stage"], "rejected")
        self.assertIsNotNone(customer["cooldown_until"])
        self.assertFalse(customer["pinned"])
        self.assertIn("冷静期", customer["next_step"])

        discovery = {
            item["customer"]["customer_id"]
            for item in self.service.workbench()["discovery"]
        }
        self.assertNotIn("C001", discovery)

        self.service.advance_demo_time(days=31)
        recovered = next(
            item
            for item in self.service.workbench()["discovery"]
            if item["customer"]["customer_id"] == "C001"
        )
        self.assertIn("冷静期", recovered["discovery"]["actionable_reason"])
        self.assertIn("低打扰服务回访", recovered["discovery"]["suggested_action"])

    def test_pin_changes_sorting_metadata_without_changing_score(self):
        self.service.set_pin("C012", True)
        workbench = self.service.workbench()
        item = next(
            item
            for item in workbench["discovery"]
            if item["customer"]["customer_id"] == "C012"
        )
        self.assertTrue(item["customer"]["pinned"])
        self.assertTrue(item["discovery"]["pinned"])
        self.assertLess(item["discovery"]["score"], 100)

    def test_customer_list_filters_assets_and_sorts_priority(self):
        filtered = self.service.customers(
            total_assets_band="300万以上",
            sort_by="priority",
        )
        self.assertTrue(filtered)
        self.assertTrue(
            all(
                item["customer"]["total_assets_band"] == "300万以上"
                for item in filtered
            )
        )
        unpinned_scores = [
            item["discovery"]["score"] if item["discovery"] else -1
            for item in filtered
            if not item["customer"]["pinned"]
        ]
        self.assertEqual(unpinned_scores, sorted(unpinned_scores, reverse=True))


if __name__ == "__main__":
    unittest.main()
