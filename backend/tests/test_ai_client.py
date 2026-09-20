import unittest

from app.ai_client import KimiError, _parse_json_object
from app.ai_service import _validate_interaction_suggestion


class AIClientParsingTests(unittest.TestCase):
    def test_parses_plain_json_object(self):
        self.assertEqual(_parse_json_object('{"a":1}'), {"a": 1})

    def test_parses_json_code_fence(self):
        fence = chr(96) * 3
        value = _parse_json_object(fence + 'json\n{"stage":"considering"}\n' + fence)
        self.assertEqual(value["stage"], "considering")

    def test_parses_json_after_small_text_prefix(self):
        value = _parse_json_object('结果如下：\n{"intent":"medium"}')
        self.assertEqual(value["intent"], "medium")


class AIServiceValidationTests(unittest.TestCase):
    def _valid(self):
        return {
            "structured_summary": "客户希望三天后再联系。",
            "customer_feedback": "三天后再聊",
            "relationship_stage": "considering",
            "intent_level": "medium",
            "current_need": "确认流动性安排",
            "current_obstacle": "仍需考虑",
            "next_step": "三天后回访",
            "next_contact_at": "2026-09-23T09:00:00+08:00",
            "outcome": "completed",
            "waiting_on": "customer",
            "reasoning_summary": "客户给出明确后续时间。",
            "confidence": 0.9,
        }

    def test_validates_and_normalizes_completed_waiting_on(self):
        value = _validate_interaction_suggestion(self._valid())
        self.assertEqual(value["waiting_on"], "none")
        self.assertEqual(value["confidence"], 0.9)

    def test_rejects_malformed_ai_datetime(self):
        value = self._valid()
        value["next_contact_at"] = "三天后"
        with self.assertRaises(KimiError):
            _validate_interaction_suggestion(value)

    def test_rejects_unknown_stage(self):
        value = self._valid()
        value["relationship_stage"] = "hot_lead"
        with self.assertRaises(KimiError):
            _validate_interaction_suggestion(value)


if __name__ == "__main__":
    unittest.main()
