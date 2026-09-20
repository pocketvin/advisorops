# 数据模型

## 1. 设计原则

V1 数据模型围绕五类对象展开：

1. CustomerSnapshot：客户当前快照
2. ActivityEvent：完整经营活动
3. WorkItem：当前执行工作
4. ChangeProposal：AI / 规则提出但尚未确认的变化
5. SyncState：外部数据源同步状态

目标是同时满足：

- 当前页面查询快
- 历史可以完整复盘
- AI 的解释性修改可审核
- 外部重复同步不会产生重复记录

## 2. CustomerSnapshot

表示“现在我们对客户的已确认认知”。

### 基本身份

Demo 仅使用模拟信息：

- customer_id
- display_name
- age_band
- customer_level（服务层级；Demo 使用公开层级名称模拟，不模拟内部资产门槛）
- profile_json（多维已确认客户画像）
- profile_hypotheses_json（待验证经营假设）

### 客户全景画像

`profile_json` 采用分组 JSON，避免为每个画像标签增加数据库列：

- demographics：粗粒度居住区域、职业、行业、单位类型
- family_and_life：家庭阶段、家庭责任、未来重要安排
- financial_context：收入区间、负债区间、现金流特征、流动性偏好
- investment_context：投资经验、主要目标、投资期限、信息偏好
- service_preferences：偏好渠道、联系时间、沟通方式
- relationship_context：兴趣、主要顾虑、建立信任的因素

`profile_hypotheses_json` 与事实严格分离，用于保存“决策风格”等待验证经营假设，并包含 confidence / basis / status。软画像暂不参与 Priority 加减分。

### 权威业务事实

- risk_level
- total_assets_band
- holdings_summary
- investable_funds_band
- recent_login_at
- recent_trade_at
- asset_change_30d_pct
- recent_product_interest
- recent_consult_topic

这些是确定事实字段。真实企业环境中应由权威系统/获批数据源同步，不由 AI 改写。

### 当前经营状态

- relationship_stage
- intent_level
- current_need
- current_obstacle
- current_progress
- next_step
- next_contact_at
- cooldown_until
- pinned
- manager_note（人工字段，AI 不自动修改）

### 派生字段

不持久化或只做缓存：

- follow_up_state
- discovery_score
- discovery_reasons
- latest_activity_at
- current_work_state

## 3. ActivityEvent

ActivityEvent 是复盘事实源。

建议字段：

- id
- customer_id
- source
- source_event_id
- channel
- activity_type
- occurred_at
- received_at
- raw_content
- structured_summary
- customer_feedback
- needs
- objections
- action_taken
- next_step
- next_contact_at
- created_by
- ai_extraction_version
- created_at

### source 示例

- manual
- mock_crm
- mock_wecom
- mock_call
- mock_behavior

### channel 示例

- phone
- wecom
- meeting
- app
- system
- other

### activity_type 示例

- interaction
- behavior_signal
- note
- sync_fact
- work_started
- work_completed
- state_change

### 原始记录原则

raw_content 不因为 AI 已经结构化就删除。

如果来源未来包含录音等大型文件，不直接塞进 SQLite BLOB；只保留经过权限控制的引用和必要元数据。

## 4. WorkItem

WorkItem 表示“客户经理已经决定处理的工作”。

字段：

- id
- customer_id
- title
- status
- waiting_on
- source_candidate_id
- current_progress
- next_action
- due_at
- started_at
- completed_at
- completion_activity_id
- created_at
- updated_at

### status

- action_required
- waiting
- completed_today
- cancelled

### waiting_on

- customer
- manager
- internal
- scheduled_time
- none

原则：

- 一个客户同一时刻默认只有一个 active WorkItem。
- active WorkItem 存在时，客户不重复进入发现区。
- completed_today 在跨日后不再作为活跃工作项展示。
- 若完成后设置未来联系时间，等时间到期再重新形成 Discovery Candidate。

## 5. Discovery Candidate

V1 可选择不单独持久化 Candidate，而是动态计算。

输入：

- CustomerSnapshot
- 最新 Activity
- 当前时间
- active WorkItem

输出：

- customer_id
- actionable_reason
- score
- score_breakdown
- suggested_action_type
- explanation

如果后续需要保存“系统当时为何推荐”，再增加 RecommendationSnapshot 表，不在 V1 预建。

## 6. ChangeProposal

用于避免 AI 直接改解释性字段。

字段：

- id
- customer_id
- activity_id
- status
- proposed_changes_json
- extraction_summary
- confidence
- created_at
- reviewed_at
- applied_at
- reviewer_note

status：

- pending
- applied
- partially_applied
- rejected

### proposed_changes 示例

```json
{
  "relationship_stage": {
    "from": "interested",
    "to": "considering",
    "reason": "客户明确表示需要一段时间考虑"
  },
  "next_contact_at": {
    "from": null,
    "to": "2026-10-01T09:00:00+08:00",
    "reason": "客户要求十月后再联系"
  }
}
```

V1 不保存模型 chain-of-thought，只保存：

- 最终抽取结果
- 简短理由
- extractor / prompt 版本
- 可选置信度

## 7. FieldChangeAudit

任何已确认 Snapshot 变化都可留下最小审计记录：

- id
- customer_id
- source_activity_id
- source_proposal_id
- field_name
- old_value
- new_value
- changed_by
- changed_at

这样点击“为什么现在是考虑中”时，可以追溯到原始 Activity。

## 8. SyncState

每个 Connector 一条状态：

- source
- cursor
- last_attempt_at
- last_success_at
- last_error
- last_result_count

外部事件唯一键：

```text
(source, source_event_id)
```

避免轮询重复写入。

## 9. AI 咨询上下文

Context Pack 默认不作为新的客户事实保存。

它是按需从：

- CustomerSnapshot
- 最近 Activity
- WorkItem
- 当前发现原因

生成的临时视图。

可记录：

- 生成时间
- 使用的脱敏策略版本

但不需要把每一次生成的全文长期存数据库。

## 10. 时间规则

数据库统一保存带时区的 ISO 时间或 UTC 时间，UI 负责按用户时区显示。

follow_up_state 动态计算：

- next_contact_at is null → none
- cooldown_until > now → cooldown
- next_contact_at > now → scheduled
- 当日到期 → due
- next_contact_at < now 且尚未处理 → overdue

不依赖每天凌晨批量改状态。

## 11. 批量导入与删除

### Import Preview

Import Preview 不持久化，是 CSV 进入正式数据库前的临时标准化视图：row_number、status、normalized Customer payload、errors、warnings。确认导入后，有效行进入 customers，并追加一条 source=import 的 ActivityEvent，保存来源行号。

### 删除语义

V0.6 的本地 Demo 支持 Customer 物理删除。依赖 SQLite foreign key cascade 清理 activity_events、work_items、field_change_audit、change_proposals 和相关 external_events。附件文件不在数据库中；删除客户后，仅清理不再被任何剩余 Activity 引用的 work/attachments 文件。

真实生产系统不应直接沿用这一物理删除策略，而应按机构的数据保留、归档、审计和个人信息治理要求重新设计。
