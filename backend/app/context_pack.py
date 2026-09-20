from __future__ import annotations

from typing import Any, Dict, Optional

from . import repository
from .db import PathLike, connect


class ContextPackService:
    def __init__(self, db_path: Optional[PathLike] = None) -> None:
        self.db_path = db_path

    def build(self, customer_id: str, question: str = "") -> Dict[str, Any]:
        with connect(self.db_path) as conn:
            customer = repository.get_customer(conn, customer_id)
            if customer is None:
                raise KeyError(customer_id)
            activities = repository.list_activities(conn, customer_id, limit=5)
            active_work = repository.get_active_work_for_customer(conn, customer_id)

        lines = [
            "【客户背景】",
            f"客户代号：{customer['customer_id']}",
            f"年龄段：{customer['age_band']}",
            f"客户等级：{customer['customer_level']}",
            f"风险等级：{customer['risk_level']}",
            f"资产区间：{customer['total_assets_band']}",
            f"可投资资金区间：{customer['investable_funds_band']}",
            f"当前持仓摘要：{customer['holdings_summary'] or '暂无记录'}",
            "",
            "【近期行为事实】",
            f"近30日资产变化：{customer['asset_change_30d_pct']:+.1f}%",
            f"最近关注：{customer['recent_product_interest'] or '无'}",
            f"最近咨询：{customer['recent_consult_topic'] or '无'}",
            f"最近登录：{customer['recent_login_at'] or '无'}",
            f"最近交易：{customer['recent_trade_at'] or '无'}",
            "",
            "【当前经营状态】",
            f"阶段：{customer['relationship_stage']}",
            f"意向：{customer['intent_level']}",
            f"当前需求：{customer['current_need'] or '暂无明确记录'}",
            f"当前障碍：{customer['current_obstacle'] or '暂无明确记录'}",
            f"当前进展：{customer['current_progress'] or '暂无明确记录'}",
            f"下一步：{customer['next_step'] or '尚未安排'}",
            f"下次联系：{customer['next_contact_at'] or '尚未安排'}",
        ]

        if active_work:
            lines += [
                "",
                "【当前工作项】",
                f"状态：{active_work['status']}",
                f"下一动作：{active_work['next_action'] or '未填写'}",
                f"当前进展：{active_work['current_progress'] or '未填写'}",
            ]

        lines += ["", "【最近沟通】"]
        if not activities:
            lines.append("暂无记录")
        else:
            for item in reversed(activities):
                summary = item["structured_summary"] or item["raw_content"] or "无摘要"
                feedback = item["customer_feedback"]
                lines.append(f"- {item['occurred_at']} · {item['channel']}：{summary}")
                if feedback:
                    lines.append(f"  客户反馈：{feedback}")

        lines += [
            "",
            "【希望 AI 帮助】",
            question.strip()
            or "请分析下一次沟通应该重点确认哪些问题，以及如何自然展开沟通。不要代替客户作投资决策，也不要推荐具体投资产品。",
            "",
            "【边界】",
            "仅用于客户经理沟通准备；不替代适当性判断，不作投资决策。",
        ]

        return {
            "text": "\n".join(lines),
            "included_fields": [
                "customer_id",
                "age_band",
                "customer_level",
                "risk_level",
                "total_assets_band",
                "investable_funds_band",
                "holdings_summary",
                "asset_change_30d_pct",
                "recent_product_interest",
                "recent_consult_topic",
                "recent_login_at",
                "recent_trade_at",
                "relationship_stage",
                "intent_level",
                "current_need",
                "current_obstacle",
                "current_progress",
                "next_step",
                "next_contact_at",
                "recent_activities",
            ],
            "redacted_fields": [
                "name",
                "phone",
                "identity_document",
                "securities_account",
                "address",
                "exact_transaction_history",
            ],
        }
