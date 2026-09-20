# 证券客户经营工作台（工作名）

一个面向证券客户经理日常客户经营的轻量 Web 产品原型。

当前阶段：**Phase 1 单客户闭环施工。**

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
- Python sqlite3 + 薄 Repository
- SQLite（WAL）
- pytest

V1 不提前引入 Redis、Celery、Kafka、向量数据库或微服务。

## Phase 1 当前实现

已实现：

- 3 个固定模拟客户
- 工作区 / 发现区分离
- actionable reason 过滤后再排序
- 最近刚联系且没有新理由时抑制重复触达
- 到期 / 逾期跟进重新进入发现区
- 开始跟进后创建 WorkItem 并从发现区移出
- 待我处理 / 等待中 / 今日已完成
- 原始沟通内容 + 结构化经营记录同时保存
- Customer Snapshot 更新
- Field Change Audit
- 客户完整 Activity 时间线
- FastAPI API
- React 工作台第一版源码

当前验证：

- 13 条领域 / SQLite 测试通过
- FastAPI TestClient 完整闭环烟测通过
- 前端 TS/TSX 语法编译检查通过
- 尚未在本项目安装前端依赖，因此真实 `npm typecheck/build` 和浏览器联调仍待执行

## 本地运行

后端依赖准备好以后：

```bash
cd /Users/yu0/Workspace/10-Projects/Securities-Client-Workbench/backend
uv sync
uv run uvicorn app.main:app --reload --port 8010
```

前端依赖准备好以后：

```bash
cd /Users/yu0/Workspace/10-Projects/Securities-Client-Workbench/frontend
npm install
npm run dev
```

前端开发服务器会把 `/api` 代理到 `127.0.0.1:8010`。

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

当前正在按纵向切片实现 Phase 1。

V1 暂时保留 Python 标准库 sqlite3，而不是为了 ORM 迁移本身引入额外依赖。当前优先统一：

- 单一排序列表 → 工作区 + 发现区
- interaction 只改字段 → 完整 Activity + Field Change Audit（AI Change Proposal 后续接入）
- 直接状态修改 → 可追溯状态变化

## 数据与合规声明

- 所有 Demo 客户均为模拟数据。
- 不暗示已接入中信证券或任何券商真实 CRM。
- Priority 仅用于客户经理工作顺序，不是投资建议或成交概率。
- 具体产品/服务仍需遵循真实机构的适当性和权限流程。
- 真实客户信息不应默认导出到个人外部 AI。
