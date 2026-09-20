from __future__ import annotations

import json
import re
import socket
import ssl
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Mapping, Optional

from .config import KimiSettings, load_kimi_settings
from .time_utils import BUSINESS_TZ


class KimiError(RuntimeError):
    pass


class KimiUnavailableError(KimiError):
    pass


@dataclass(frozen=True)
class KimiResult:
    data: Dict[str, Any]
    model: str
    usage: Dict[str, Any]


def _redact(text: str, api_key: str) -> str:
    result = text.replace(api_key, "[redacted-key]") if api_key else text
    result = re.sub(
        r"(?i)(?:sk|ak|ms|moonshot)[-_][A-Za-z0-9._~-]{8,}",
        "[redacted-key]",
        result,
    )
    return result[:1600]


def _parse_json_object(content: str) -> Dict[str, Any]:
    text = content.strip()
    fence = chr(96) * 3
    if text.startswith(fence):
        text = re.sub(
            r"^" + re.escape(fence) + r"(?:json)?\s*",
            "",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(r"\s*" + re.escape(fence) + r"$", "", text)

    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        if start < 0:
            raise
        decoder = json.JSONDecoder()
        value, _ = decoder.raw_decode(text[start:])

    if not isinstance(value, dict):
        raise ValueError("root is not object")
    return value


class KimiClient:
    def __init__(
        self,
        settings: Optional[KimiSettings] = None,
        timeout_seconds: float = 90.0,
    ) -> None:
        self.settings = settings or load_kimi_settings()
        self.timeout_seconds = timeout_seconds

    @property
    def configured(self) -> bool:
        return self.settings.configured

    def status(self) -> Dict[str, Any]:
        return {
            "configured": self.configured,
            "model": self.settings.model if self.configured else None,
            "source": self.settings.source,
            "base_url": self.settings.base_url if self.configured else None,
        }

    def _url(self) -> str:
        base = self.settings.base_url.rstrip("/")
        if base.endswith("/v1"):
            return base + "/chat/completions"
        return base + "/v1/chat/completions"

    def json_schema(
        self,
        *,
        system: str,
        user: str,
        schema_name: str,
        schema: Mapping[str, Any],
        images: Optional[list[str]] = None,
        reasoning_effort: str = "low",
        max_completion_tokens: Optional[int] = None,
    ) -> KimiResult:
        if not self.configured:
            raise KimiUnavailableError("Kimi K3 尚未配置")

        user_content: Any = user
        if images:
            user_content = [{"type": "text", "text": user}]
            user_content.extend(
                {
                    "type": "image_url",
                    "image_url": {"url": image_url},
                }
                for image_url in images
            )

        payload = {
            "model": self.settings.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": schema_name,
                    "strict": True,
                    "schema": dict(schema),
                },
            },
            "reasoning_effort": reasoning_effort,
            "max_completion_tokens": max_completion_tokens
            or self.settings.max_completion_tokens,
            "temperature": 1.0,
        }

        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            self._url(),
            data=raw,
            method="POST",
            headers={
                "Authorization": "Bearer " + self.settings.api_key,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )

        envelope = None
        for attempt in range(2):
            try:
                with urllib.request.urlopen(
                    request,
                    timeout=self.timeout_seconds,
                ) as response:
                    envelope = json.loads(response.read().decode("utf-8"))
                break
            except urllib.error.HTTPError as exc:
                body = exc.read(4096).decode("utf-8", errors="replace")
                retryable = exc.code == 429 or 500 <= exc.code <= 504
                if retryable and attempt == 0:
                    time.sleep(0.5)
                    continue
                raise KimiError(
                    f"Kimi HTTP {exc.code}: {_redact(body, self.settings.api_key)}"
                ) from exc
            except urllib.error.URLError as exc:
                retryable = isinstance(
                    exc.reason,
                    (TimeoutError, socket.timeout, ConnectionError),
                ) and not isinstance(exc.reason, ssl.SSLError)
                if retryable and attempt == 0:
                    time.sleep(0.5)
                    continue
                reason = _redact(str(exc.reason), self.settings.api_key)
                raise KimiError(f"Kimi network error: {reason}") from exc
            except (TimeoutError, socket.timeout, ConnectionError) as exc:
                if attempt == 0:
                    time.sleep(0.5)
                    continue
                raise KimiError("Kimi request timed out after bounded retry") from exc
            except (ssl.SSLError, json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise KimiError("Kimi returned an unreadable response") from exc

        if envelope is None:
            raise KimiError("Kimi request did not return a response")

        try:
            choices = envelope["choices"]
            message = choices[0]["message"]
            content = message["content"]
            if isinstance(content, list):
                content = "".join(
                    item.get("text", "")
                    for item in content
                    if isinstance(item, dict)
                )
            if not isinstance(content, str) or not content.strip():
                raise ValueError("empty content")
            data = _parse_json_object(content)
        except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
            finish_reason = None
            try:
                finish_reason = envelope["choices"][0].get("finish_reason")
            except (KeyError, IndexError, TypeError):
                pass
            suffix = (
                f"; finish_reason={finish_reason}"
                if finish_reason
                else ""
            )
            raise KimiError(
                "Kimi structured response was invalid" + suffix
            ) from exc

        usage = envelope.get("usage")
        return KimiResult(
            data=data,
            model=self.settings.model,
            usage=usage if isinstance(usage, dict) else {},
        )


INTERACTION_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "structured_summary": {"type": "string"},
        "customer_feedback": {"type": "string"},
        "relationship_stage": {
            "type": "string",
            "enum": [
                "new",
                "contacted",
                "interested",
                "considering",
                "rejected",
                "dormant",
            ],
        },
        "intent_level": {
            "type": "string",
            "enum": ["unknown", "low", "medium", "high"],
        },
        "current_need": {"type": "string"},
        "current_obstacle": {"type": "string"},
        "next_step": {"type": "string"},
        "next_contact_at": {
            "anyOf": [{"type": "string"}, {"type": "null"}],
        },
        "outcome": {
            "type": "string",
            "enum": ["completed", "waiting"],
        },
        "waiting_on": {
            "type": "string",
            "enum": [
                "none",
                "customer",
                "manager",
                "internal",
                "scheduled_time",
            ],
        },
        "reasoning_summary": {"type": "string"},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
    },
    "required": [
        "structured_summary",
        "customer_feedback",
        "relationship_stage",
        "intent_level",
        "current_need",
        "current_obstacle",
        "next_step",
        "next_contact_at",
        "outcome",
        "waiting_on",
        "reasoning_summary",
        "confidence",
    ],
}


BRIEF_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "summary": {"type": "string"},
        "main_focus": {"type": "string"},
        "current_obstacle": {"type": "string"},
        "unresolved_questions": {
            "type": "array",
            "items": {"type": "string"},
            "maxItems": 5,
        },
        "next_conversation_focus": {"type": "string"},
    },
    "required": [
        "summary",
        "main_focus",
        "current_obstacle",
        "unresolved_questions",
        "next_conversation_focus",
    ],
}


def interaction_system_prompt() -> str:
    return """你是证券客户经理的经营记录整理助手。你的任务是把客户经理的自然语言记录整理成结构化的客户经营信息。

边界：
1. 只总结已经发生的沟通和明确可推导的经营状态；如果附带图片/聊天截图，应把图片中可见文字、表格和对话内容一起作为证据。
2. 不推荐具体股票、基金或任何投资产品。
3. 不替客户经理做适当性结论。
4. 不把“客户随口提到”夸大成确定需求；图片中无法确认身份或上下文的内容不要强行归因。
5. 时间处理：
   - 如果客户给出可根据当前时间解析的相对/日历边界，如“三天后”“下周一”“十月以后”，应生成最早建议联系时间 next_contact_at；“十月以后”可取该月 1 日 09:00（客户所在业务时区）作为最早建议时间。
   - 如果只有“以后再说”“过段时间”这种无法解析的模糊表达，next_contact_at 返回 null，不要编日期。
6. waiting 表示本轮动作尚未闭环且当前球明确在客户、内部、客户经理或约定时间一方；否则 completed。
7. 如果客户明确说“先放一放 / 再考虑 / 过几天或某月以后再联系”，且没有明确拒绝未来沟通，relationship_stage 应为 considering，本轮通常 completed，并设置可解析的未来 next_contact_at，而不是 waiting。
8. 只有明确表达“没有需求、不要再联系、近期不考虑且拒绝继续沟通”等拒绝语义时，relationship_stage 才使用 rejected。
9. reasoning_summary 只写简短可展示理由，不输出隐藏思维过程。
10. 结构化字段只是候选修改，最终由客户经理确认。"""


def build_interaction_user_prompt(
    *,
    customer: Mapping[str, Any],
    raw_content: str,
    channel: str,
    now: datetime,
) -> str:
    local_now = now.astimezone(BUSINESS_TZ)
    current = {
        "relationship_stage": customer.get("relationship_stage"),
        "intent_level": customer.get("intent_level"),
        "current_need": customer.get("current_need"),
        "current_obstacle": customer.get("current_obstacle"),
        "current_progress": customer.get("current_progress"),
        "next_step": customer.get("next_step"),
        "next_contact_at": customer.get("next_contact_at"),
        "customer_profile": customer.get("profile") or {},
        "profile_hypotheses": customer.get("profile_hypotheses") or [],
    }
    return (
        "当前时间（中国时区）: "
        + local_now.isoformat()
        + "\n沟通渠道: "
        + channel
        + "\n当前已确认客户状态:\n"
        + json.dumps(current, ensure_ascii=False, indent=2)
        + "\n\n客户经理本次原始记录:\n"
        + raw_content
    )


def brief_system_prompt() -> str:
    return """你是证券客户经理的客户经营摘要助手。根据当前已确认状态和完整活动记录生成30秒可读摘要。

要求：
- 聚焦客户经营上下文，不写空泛套话。
- 明确当前关注、障碍、尚未解决的问题以及下一次沟通最值得确认什么。
- 不推荐具体投资产品，不做收益承诺，不替代适当性流程。
- 结合家庭阶段、职业行业、现金流、投资目标、资金期限、沟通偏好等画像，但不得把画像标签当作确定结论。
- profile_hypotheses 属于待验证经营假设，必须明确当作假设而不是事实。
- 只依据输入信息，不编造。"""
