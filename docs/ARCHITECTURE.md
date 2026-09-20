# 系统架构

## 1. 架构目标

V1 优先：

- 简单
- 可解释
- 可测试
- 容易演示
- 容易替换真实数据源
- 不提前引入生产级复杂基础设施

整体采用单体 Web 应用：

```text
React / TypeScript
        │
        ▼
     FastAPI
        │
 ┌──────┼─────────────┐
 │      │             │
 ▼      ▼             ▼
Rules  AI Service   Sync Service
 │      │             │
 └──────┼─────────────┘
        ▼
   SQLModel / SQLite
```

## 2. 前端

### 基础

- React
- TypeScript
- Vite
- TanStack Query：服务端状态、刷新、mutation 后失效重拉
- React 本地 state：抽屉、筛选器、表单临时状态

V1 不引入 Redux / Zustand。只有当跨页面纯前端状态明显复杂以后再评估。

### 页面

- 今日工作台
  - 工作区
  - 发现区
  - 客户动态摘要
- 客户列表
- 客户详情 Drawer / 页面
- 客户动态
- AI 咨询上下文 Preview

## 3. 后端

### FastAPI

职责：

- REST API
- 输入输出校验
- 业务 service 入口
- connector 同步入口
- AI 提取入口
- Change Proposal 确认入口

不把业务规则直接塞在 router。

建议目录：

```text
backend/app/
  api/
  models/
  services/
  repositories/
  connectors/
  rules/
  ai/
  db/
```

### SQLModel

V1 建议从当前 raw sqlite3 scaffold 收敛到 SQLModel：

- 与 FastAPI / Pydantic 配合简单
- 底层仍是 SQLAlchemy
- SQLite → PostgreSQL 的迁移路径清晰
- 省去手工 JSON / row mapping 样板代码

正式施工时再迁移；本轮不改现有业务代码。

## 4. 数据库

V1：SQLite。

原因：

- 单机求职 Demo 足够
- 零额外服务
- 方便重置模拟数据
- 方便测试
- 面试现场可靠

建议开启：

- foreign_keys
- WAL

WAL 下读写可并发，适合这个“读取多、写入较轻”的单机工作台。

限制：

- SQLite 仍然是单 writer
- WAL 依赖同一主机，不适合网络文件系统
- 真实多人生产部署再迁 PostgreSQL

V1 模拟数据允许重建数据库，因此不急于引入 Alembic；开始保存不可丢真实数据之前再加迁移体系。

## 5. 核心服务边界

### CustomerService

- 客户 Snapshot
- 客户详情
- 客户筛选

### ActivityService

- 完整经营记录
- 时间线
- 原始内容
- 结构化内容
- 状态变更追踪

### DiscoveryService

流程：

1. 排除已经在工作区的客户
2. 判断是否存在 actionable reason
3. 生成候选
4. Rule-based Priority
5. 生成可解释原因

### WorkService

- 从发现区开始跟进
- 创建 WorkItem
- 待我处理 / 等待 / 今日完成
- 完成本次动作
- 未来到期后重新回流

### SyncService

- 调用 Connector
- 读取 cursor
- 增量拉取
- 去重
- 标准化 Activity Event
- 更新 sync cursor
- 生成待确认 Change Proposal

### AIService

- interaction extraction
- customer brief
- next-action wording
- signal candidate extraction
- AI context pack

### ContextPackService

- 字段白名单
- 脱敏
- 最近活动裁剪
- 生成可复制文本
- 不直接调用外部 AI

## 6. 数据接入：Connector 模式

不为每个来源写一套业务逻辑。

统一接口概念：

```text
Connector
  ├─ fetch_since(cursor)
  ├─ normalize(raw_item)
  └─ health()
```

V1 先做：

- Mock CRM Connector
- Mock WeCom Connector
- Mock Behavior Connector
- Manual Interaction Connector

真实企业落地时替换为获批 API。

## 7. 同步策略

不追求全渠道实时。

统一同步函数：

```text
sync_source(source_id)
sync_all()
```

触发方式共用同一实现：

1. 用户点击“立即刷新”
2. 可选定时同步
3. 未来若某来源提供 webhook，则 webhook 只负责写入统一事件入口

### V1 推荐

- 手动刷新：必须有
- 最近同步时间：必须显示
- 单数据源同步状态：可查看
- 周期同步：等 Mock Connector 完成后，用轻量 scheduler 验证即可
- 默认频率：产品配置，不写死业务规则

不在 V1 上 Redis / Celery。

FastAPI BackgroundTasks 不用于长期周期调度；它更适合一次请求返回后的轻量任务。

如果后续启用单实例周期同步，可选 APScheduler。生产多 worker 时调度器需要独立部署或共享协调，不把单机实现假装成生产架构。

## 8. 同步可靠性

每个外部事件具有：

- source
- source_event_id
- occurred_at
- received_at

唯一约束：

```text
(source, source_event_id)
```

保证重复同步不会重复写入。

每个 connector 保存：

- cursor
- last_success_at
- last_attempt_at
- last_error

同步流程：

```text
读取 cursor
→ 拉取增量
→ normalize
→ event idempotency check
→ 写 ActivityEvent
→ 生成候选变化
→ 成功后提交新 cursor
```

失败时不推进 cursor。

## 9. AI 写入边界

三类字段：

### Authority-owned

AI 不修改：

- 姓名身份
- 账号
- 权威风险等级
- 正式适当性信息
- 真实资产/持仓事实

### Safe deterministic facts

来源明确时可自动记录：

- 通话发生
- 消息发送/回复
- 明确事件时间
- 外部系统直接返回的事实

### Interpretive fields

AI 只生成 Change Proposal：

- stage
- intent
- need
- objection
- next step
- next contact
- relationship summary

默认人工确认后应用。

## 10. 不采用真正 Event Sourcing

V1 采用：

```text
Current Snapshot
+
Append-only Activity Timeline
+
Field Change Audit
```

而不是每次都从全部历史事件重放当前状态。

原因：

- 实现更简单
- 查询更直接
- 仍然可以完整复盘
- 足以支持面试 Demo

## 11. API 风格

REST 即可。

示例：

```text
GET  /api/workbench
GET  /api/discovery
GET  /api/work-items
GET  /api/activities
GET  /api/customers/{id}

POST /api/sync/refresh
POST /api/customers/{id}/interactions
POST /api/discovery/{candidate_id}/start
POST /api/work-items/{id}/complete
POST /api/change-proposals/{id}/apply
POST /api/customers/{id}/ai-context
```

不需要 GraphQL。

## 12. 后续扩展点

保持以下接口稳定：

- Connector
- PriorityRule
- AIExtractor
- ContextSanitizer

因此以后可以替换：

- Mock Connector → 券商内部 API
- SQLite → PostgreSQL
- Rule component → 预测模型
- 外部模型 → 企业 AI Gateway

而不需要推倒工作区 / 发现区 / Activity / WorkItem 产品模型。
