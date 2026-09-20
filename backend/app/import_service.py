from __future__ import annotations

import csv
import hashlib
import io
import re
from datetime import datetime
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

from .time_utils import BUSINESS_TZ, to_iso


MAX_IMPORT_ROWS = 500

TEMPLATE_COLUMNS = [
    "customer_id",
    "name",
    "age_band",
    "service_tier",
    "risk_level",
    "total_assets_band",
    "investable_funds_band",
    "holdings_summary",
    "relationship_stage",
    "intent_level",
    "current_need",
    "current_obstacle",
    "current_progress",
    "next_step",
    "next_contact_at",
    "last_contact_at",
    "manager_note",
    "asset_change_30d_pct",
    "recent_product_interest",
    "recent_consult_topic",
    "residence_region",
    "occupation",
    "industry",
    "employer_type",
    "family_stage",
    "dependents_summary",
    "major_plan",
    "annual_income_band",
    "liabilities_band",
    "cash_flow_pattern",
    "liquidity_preference",
    "investment_experience",
    "primary_goal",
    "investment_horizon",
    "information_preference",
    "preferred_channel",
    "preferred_contact_time",
    "communication_style",
    "interests",
    "key_concerns",
    "trust_factors",
]

HEADER_ALIASES = {
    "customer_id": "customer_id",
    "客户编号": "customer_id",
    "客户id": "customer_id",
    "客户ID": "customer_id",
    "编号": "customer_id",
    "id": "customer_id",
    "name": "name",
    "姓名": "name",
    "客户姓名": "name",
    "age_band": "age_band",
    "年龄段": "age_band",
    "年龄区间": "age_band",
    "service_tier": "service_tier",
    "customer_level": "service_tier",
    "服务层级": "service_tier",
    "客户等级": "service_tier",
    "客户层级": "service_tier",
    "risk_level": "risk_level",
    "风险等级": "risk_level",
    "total_assets_band": "total_assets_band",
    "总资产": "total_assets_band",
    "总资产区间": "total_assets_band",
    "资产区间": "total_assets_band",
    "investable_funds_band": "investable_funds_band",
    "可投资资金": "investable_funds_band",
    "可投资资金区间": "investable_funds_band",
    "holdings_summary": "holdings_summary",
    "持仓摘要": "holdings_summary",
    "持仓": "holdings_summary",
    "relationship_stage": "relationship_stage",
    "关系阶段": "relationship_stage",
    "客户阶段": "relationship_stage",
    "intent_level": "intent_level",
    "当前意向": "intent_level",
    "意向": "intent_level",
    "current_need": "current_need",
    "当前需求": "current_need",
    "需求": "current_need",
    "current_obstacle": "current_obstacle",
    "当前障碍": "current_obstacle",
    "障碍": "current_obstacle",
    "current_progress": "current_progress",
    "当前进展": "current_progress",
    "进展": "current_progress",
    "next_step": "next_step",
    "下一步": "next_step",
    "next_contact_at": "next_contact_at",
    "下次联系": "next_contact_at",
    "下次联系时间": "next_contact_at",
    "last_contact_at": "last_contact_at",
    "最近联系": "last_contact_at",
    "最近联系时间": "last_contact_at",
    "manager_note": "manager_note",
    "客户经理备注": "manager_note",
    "备注": "manager_note",
    "asset_change_30d_pct": "asset_change_30d_pct",
    "近30日资产变化": "asset_change_30d_pct",
    "近30日资产变化%": "asset_change_30d_pct",
    "recent_product_interest": "recent_product_interest",
    "最近关注": "recent_product_interest",
    "recent_consult_topic": "recent_consult_topic",
    "最近咨询": "recent_consult_topic",
    "residence_region": "residence_region",
    "居住区域": "residence_region",
    "地区": "residence_region",
    "住址": "residence_region",
    "occupation": "occupation",
    "职业": "occupation",
    "industry": "industry",
    "行业": "industry",
    "employer_type": "employer_type",
    "单位类型": "employer_type",
    "family_stage": "family_stage",
    "家庭阶段": "family_stage",
    "dependents_summary": "dependents_summary",
    "家庭责任": "dependents_summary",
    "major_plan": "major_plan",
    "未来重要安排": "major_plan",
    "annual_income_band": "annual_income_band",
    "年收入区间": "annual_income_band",
    "年收入": "annual_income_band",
    "liabilities_band": "liabilities_band",
    "负债区间": "liabilities_band",
    "负债": "liabilities_band",
    "cash_flow_pattern": "cash_flow_pattern",
    "现金流特征": "cash_flow_pattern",
    "liquidity_preference": "liquidity_preference",
    "流动性偏好": "liquidity_preference",
    "investment_experience": "investment_experience",
    "投资经验": "investment_experience",
    "primary_goal": "primary_goal",
    "主要目标": "primary_goal",
    "投资目标": "primary_goal",
    "investment_horizon": "investment_horizon",
    "投资期限": "investment_horizon",
    "information_preference": "information_preference",
    "信息偏好": "information_preference",
    "preferred_channel": "preferred_channel",
    "偏好渠道": "preferred_channel",
    "preferred_contact_time": "preferred_contact_time",
    "偏好联系时间": "preferred_contact_time",
    "communication_style": "communication_style",
    "沟通偏好": "communication_style",
    "interests": "interests",
    "兴趣": "interests",
    "兴趣爱好": "interests",
    "key_concerns": "key_concerns",
    "主要顾虑": "key_concerns",
    "trust_factors": "trust_factors",
    "信任因素": "trust_factors",
    "建立信任的因素": "trust_factors",
}

STAGE_ALIASES = {
    "new": "new",
    "新客户": "new",
    "新建": "new",
    "contacted": "contacted",
    "已联系": "contacted",
    "已沟通": "contacted",
    "interested": "interested",
    "有明确兴趣": "interested",
    "有兴趣": "interested",
    "高兴趣": "interested",
    "considering": "considering",
    "考虑中": "considering",
    "再考虑": "considering",
    "rejected": "rejected",
    "拒绝": "rejected",
    "近期明确拒绝": "rejected",
    "dormant": "dormant",
    "长期沉默": "dormant",
    "沉默": "dormant",
}

INTENT_ALIASES = {
    "unknown": "unknown",
    "未知": "unknown",
    "未判断": "unknown",
    "low": "low",
    "低": "low",
    "低意向": "low",
    "medium": "medium",
    "中": "medium",
    "中意向": "medium",
    "high": "high",
    "高": "high",
    "高意向": "high",
}

SERVICE_TIER_ALIASES = {
    "gold": "Gold",
    "金卡": "Gold",
    "platinum": "Platinum",
    "铂金": "Platinum",
    "black gold": "Black Gold",
    "黑金": "Black Gold",
    "diamond": "Diamond",
    "钻石": "Diamond",
    "black diamond": "Black Diamond",
    "黑钻": "Black Diamond",
    "黑钻石": "Black Diamond",
}

LIST_SPLIT_RE = re.compile(r"[|｜;；、,，]+")
COMMON_DATETIME_FORMATS = (
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%Y-%m-%d %H:%M",
    "%Y/%m/%d %H:%M",
    "%Y-%m-%d %H:%M:%S",
    "%Y/%m/%d %H:%M:%S",
)


def template_csv() -> str:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=TEMPLATE_COLUMNS, lineterminator="\n")
    writer.writeheader()
    return buffer.getvalue()


def sample_csv() -> str:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=TEMPLATE_COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerow(
        {
            "customer_id": "DEMO-001",
            "name": "示例客户",
            "age_band": "35-45",
            "service_tier": "Gold",
            "risk_level": "C3",
            "total_assets_band": "80-150万",
            "investable_funds_band": "20-50万",
            "holdings_summary": "ETF + 固收",
            "relationship_stage": "contacted",
            "intent_level": "medium",
            "current_need": "流动性与长期配置平衡",
            "residence_region": "杭州·余杭",
            "occupation": "产品经理",
            "industry": "互联网/软件",
            "family_stage": "育有学龄子女",
            "annual_income_band": "50-80万",
            "primary_goal": "子女教育",
            "investment_horizon": "3-5年",
            "preferred_channel": "企业微信+电话",
            "communication_style": "偏好先文字说明，再预约电话",
            "interests": "亲子教育|旅行",
            "key_concerns": "流动性|市场波动",
            "trust_factors": "风险讲清楚|按约定时间跟进",
        }
    )
    return buffer.getvalue()


def _normalize_header(value: str) -> str:
    text = value.strip().lstrip("\ufeff")
    return HEADER_ALIASES.get(text, HEADER_ALIASES.get(text.casefold(), ""))


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _split_list(value: str) -> List[str]:
    if not value.strip():
        return []
    return [item.strip() for item in LIST_SPLIT_RE.split(value) if item.strip()]


def _generated_customer_id(name: str, row_number: int) -> str:
    digest = hashlib.sha1(f"{name}|{row_number}".encode("utf-8")).hexdigest()[:8]
    return f"IMP-{digest.upper()}"


def _normalize_datetime(value: str) -> Tuple[Optional[str], Optional[str]]:
    raw = value.strip()
    if not raw:
        return None, None

    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=BUSINESS_TZ)
        return to_iso(parsed), None
    except ValueError:
        pass

    for fmt in COMMON_DATETIME_FORMATS:
        try:
            parsed = datetime.strptime(raw, fmt).replace(tzinfo=BUSINESS_TZ)
            return to_iso(parsed), None
        except ValueError:
            continue
    return None, f"无法识别时间：{raw}"


def _normalize_float(value: str) -> Tuple[float, Optional[str]]:
    raw = value.strip().replace("%", "")
    if not raw:
        return 0.0, None
    try:
        return float(raw), None
    except ValueError:
        return 0.0, f"无法识别数值：{value}"


def _normalize_row(
    row: Mapping[str, str],
    *,
    row_number: int,
    now_iso: str,
    existing_ids: Set[str],
    seen_ids: Set[str],
    existing_names: Set[str],
) -> Dict[str, Any]:
    errors: List[str] = []
    warnings: List[str] = []

    name = _clean(row.get("name"))
    if not name:
        errors.append("缺少姓名")

    customer_id = _clean(row.get("customer_id"))
    if not customer_id and name:
        customer_id = _generated_customer_id(name, row_number)
        warnings.append(f"未提供客户编号，已生成 {customer_id}")

    if customer_id:
        if customer_id in existing_ids:
            errors.append(f"客户编号已存在：{customer_id}")
        if customer_id in seen_ids:
            errors.append(f"导入文件内客户编号重复：{customer_id}")
        seen_ids.add(customer_id)

    if name and name in existing_names:
        warnings.append("系统中存在同名客户，请确认不是重复客户")

    stage_raw = _clean(row.get("relationship_stage"))
    stage = STAGE_ALIASES.get(stage_raw.casefold(), STAGE_ALIASES.get(stage_raw))
    if not stage:
        if stage_raw:
            errors.append(f"无法识别关系阶段：{stage_raw}")
        stage = "new"

    intent_raw = _clean(row.get("intent_level"))
    intent = INTENT_ALIASES.get(intent_raw.casefold(), INTENT_ALIASES.get(intent_raw))
    if not intent:
        if intent_raw:
            errors.append(f"无法识别当前意向：{intent_raw}")
        intent = "unknown"

    tier_raw = _clean(row.get("service_tier"))
    tier = SERVICE_TIER_ALIASES.get(tier_raw.casefold(), tier_raw or "未分层")
    if tier_raw and tier_raw.casefold() not in SERVICE_TIER_ALIASES and tier_raw not in SERVICE_TIER_ALIASES.values():
        warnings.append(f"服务层级“{tier_raw}”不是演示标准层级，已原样保留")

    risk = _clean(row.get("risk_level")).upper() or "未记录"
    if risk != "未记录" and risk not in {"C1", "C2", "C3", "C4", "C5"}:
        warnings.append(f"风险等级“{risk}”不是 C1-C5，已原样保留")

    next_contact_at, next_error = _normalize_datetime(_clean(row.get("next_contact_at")))
    if next_error:
        errors.append("下次联系时间：" + next_error)
    last_contact_at, last_error = _normalize_datetime(_clean(row.get("last_contact_at")))
    if last_error:
        errors.append("最近联系时间：" + last_error)

    asset_change, asset_error = _normalize_float(_clean(row.get("asset_change_30d_pct")))
    if asset_error:
        errors.append("近30日资产变化：" + asset_error)

    residence = _clean(row.get("residence_region"))
    if residence and re.search(r"\d+号|\d+室|\d+幢|\d+栋", residence):
        warnings.append("居住区域疑似包含精确门牌；公开 Demo 建议只保留城市/区级信息")

    profile = {
        "demographics": {
            "residence_region": residence,
            "occupation": _clean(row.get("occupation")),
            "industry": _clean(row.get("industry")),
            "employer_type": _clean(row.get("employer_type")),
        },
        "family_and_life": {
            "family_stage": _clean(row.get("family_stage")),
            "dependents_summary": _clean(row.get("dependents_summary")),
            "major_plan": _clean(row.get("major_plan")),
        },
        "financial_context": {
            "annual_income_band": _clean(row.get("annual_income_band")),
            "liabilities_band": _clean(row.get("liabilities_band")),
            "cash_flow_pattern": _clean(row.get("cash_flow_pattern")),
            "liquidity_preference": _clean(row.get("liquidity_preference")),
        },
        "investment_context": {
            "experience": _clean(row.get("investment_experience")),
            "primary_goal": _clean(row.get("primary_goal")),
            "investment_horizon": _clean(row.get("investment_horizon")),
            "information_preference": _clean(row.get("information_preference")),
        },
        "service_preferences": {
            "preferred_channel": _clean(row.get("preferred_channel")),
            "preferred_contact_time": _clean(row.get("preferred_contact_time")),
            "communication_style": _clean(row.get("communication_style")),
        },
        "relationship_context": {
            "interests": _split_list(_clean(row.get("interests"))),
            "key_concerns": _split_list(_clean(row.get("key_concerns"))),
            "trust_factors": _split_list(_clean(row.get("trust_factors"))),
        },
    }

    normalized = {
        "customer_id": customer_id,
        "name": name,
        "age_band": _clean(row.get("age_band")) or "未记录",
        "customer_level": tier,
        "risk_level": risk,
        "total_assets_band": _clean(row.get("total_assets_band")) or "未记录",
        "investable_funds_band": _clean(row.get("investable_funds_band")) or "未记录",
        "profile": profile,
        "profile_hypotheses": [],
        "holdings_summary": _clean(row.get("holdings_summary")),
        "recent_login_at": None,
        "recent_trade_at": None,
        "asset_change_30d_pct": asset_change,
        "recent_product_interest": _clean(row.get("recent_product_interest")),
        "recent_consult_topic": _clean(row.get("recent_consult_topic")),
        "relationship_stage": stage,
        "intent_level": intent,
        "current_need": _clean(row.get("current_need")),
        "current_obstacle": _clean(row.get("current_obstacle")),
        "current_progress": _clean(row.get("current_progress")) or "通过 CSV 批量导入，尚未开始经营",
        "next_step": _clean(row.get("next_step")),
        "next_contact_at": next_contact_at,
        "cooldown_until": None,
        "pinned": False,
        "manager_note": _clean(row.get("manager_note")),
        "last_contact_at": last_contact_at,
        "recent_signal": "",
        "created_at": now_iso,
        "updated_at": now_iso,
    }

    return {
        "row_number": row_number,
        "status": "invalid" if errors else "valid",
        "normalized": normalized,
        "errors": errors,
        "warnings": warnings,
    }


def preview_csv_import(
    csv_text: str,
    *,
    existing_ids: Sequence[str],
    existing_names: Sequence[str],
    now_iso: str,
) -> Dict[str, Any]:
    if not csv_text.strip():
        raise ValueError("CSV 内容为空")
    if len(csv_text.encode("utf-8")) > 2_000_000:
        raise ValueError("CSV 文件不能超过 2MB")

    stream = io.StringIO(csv_text.lstrip("\ufeff"))
    try:
        reader = csv.DictReader(stream)
    except csv.Error as exc:
        raise ValueError("CSV 格式无法解析") from exc

    if not reader.fieldnames:
        raise ValueError("CSV 缺少表头")

    canonical_headers: List[str] = []
    ignored_columns: List[str] = []
    seen_headers: Set[str] = set()
    for raw in reader.fieldnames:
        canonical = _normalize_header(raw or "")
        canonical_headers.append(canonical)
        if not canonical:
            ignored_columns.append((raw or "").strip())
            continue
        if canonical in seen_headers:
            raise ValueError(f"CSV 存在重复含义的列：{raw}")
        seen_headers.add(canonical)

    if "name" not in seen_headers:
        raise ValueError("CSV 必须包含姓名列（name / 姓名 / 客户姓名）")

    existing_id_set = set(existing_ids)
    existing_name_set = set(existing_names)
    seen_ids: Set[str] = set()
    rows: List[Dict[str, Any]] = []

    try:
        for index, raw_row in enumerate(reader, start=2):
            if index - 1 > MAX_IMPORT_ROWS:
                raise ValueError(f"单次最多导入 {MAX_IMPORT_ROWS} 位客户")
            canonical_row: Dict[str, str] = {}
            for raw_header, canonical in zip(reader.fieldnames, canonical_headers):
                if canonical:
                    canonical_row[canonical] = _clean(raw_row.get(raw_header))
            if not any(canonical_row.values()):
                continue
            rows.append(
                _normalize_row(
                    canonical_row,
                    row_number=index,
                    now_iso=now_iso,
                    existing_ids=existing_id_set,
                    seen_ids=seen_ids,
                    existing_names=existing_name_set,
                )
            )
    except csv.Error as exc:
        raise ValueError("CSV 数据行格式错误") from exc

    if not rows:
        raise ValueError("CSV 没有可导入的数据行")

    valid_count = sum(1 for row in rows if row["status"] == "valid")
    warning_count = sum(len(row["warnings"]) for row in rows)
    invalid_count = len(rows) - valid_count

    return {
        "summary": {
            "total": len(rows),
            "valid": valid_count,
            "invalid": invalid_count,
            "warnings": warning_count,
        },
        "ignored_columns": [item for item in ignored_columns if item],
        "rows": rows,
    }
