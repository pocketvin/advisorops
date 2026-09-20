# 证券客户经营工作台（工作名）

一个面向证券客户经理日常客户经营的轻量 Web 产品原型。

当前阶段：**规划优先，暂不继续扩展业务实现。**

项目不做完整 CRM，也不虚构已经接入任何真实券商内部系统。V1 使用固定模拟客户数据，重点验证：

```text
零散客户信息
→ 完整经营记录
→ 客户当前状态
→ 发现值得处理的客户
→ 进入工作区
→ 执行与记录
→ 状态更新
→ 未来到期后再次发现
```

## 核心产品结构

### 工作区

回答：

> 我已经决定处理哪些客户，现在做到哪一步？

包含：

- 待我处理
- 等待中
- 今日已完成

### 发现区

回答：

> 如果我现在有时间，下一位值得主动处理的客户是谁？

先判断是否存在真正的行动理由，再做可解释的 Rule-based Priority。

### 客户动态

回答：

> 外部渠道刚刚出现了哪些新信息？

统一承接 Mock CRM、Mock 企业微信、Mock 行为数据和人工沟通记录。

## AI

项目原则：

> **AI 负责理解，规则负责约束，人负责决策。**

V1 计划使用 AI：

- 自然语言沟通 → 结构化经营记录
- 客户历史 → 30 秒摘要
- 发现潜在需求 / 障碍 / 时间信号
- 规则动作 → 更具体的下一步建议
- 生成脱敏 AI 咨询上下文

AI 不负责：

- 最终优先级黑盒排序
- 正式适当性判断
- 自动修改权威客户事实
- 自动发送金融建议
- 自动替客户做投资决策

## 技术基线

计划：

- React + TypeScript + Vite
- TanStack Query
- FastAPI
- SQLModel
- SQLite（WAL）
- pytest

V1 不提前引入 Redis、Celery、Kafka、向量数据库或微服务。

## 文档

从这里开始：

- `docs/README.md`
- `docs/PRODUCT-MODEL.md`
- `docs/ARCHITECTURE.md`
- `docs/FLOWS.md`
- `docs/DATA-MODEL.md`
- `docs/IMPLEMENTATION-PLAN.md`
- `docs/DEMO-SCENARIOS.md`
- `docs/RESEARCH-NOTES.md`
- `docs/REPOSITORY-GUIDE.md`

## 当前代码说明

`backend/` 和 `frontend/` 中已有一份前一轮产生的早期 scaffold。

它仅用于保留已有工作，不代表最终架构。正式施工前需要按本轮规划统一：

- raw sqlite3 → SQLModel
- 单一排序列表 → 工作区 + 发现区
- interaction 只改字段 → 完整 Activity + Change Proposal
- 直接状态修改 → 可追溯状态变化

## 数据与合规声明

- 所有 Demo 客户均为模拟数据。
- 不暗示已接入中信证券或任何券商真实 CRM。
- Priority 仅用于客户经理工作顺序，不是投资建议或成交概率。
- 具体产品/服务仍需遵循真实机构的适当性和权限流程。
- 真实客户信息不应默认导出到个人外部 AI。
