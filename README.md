# AdvisorOps

> 面向证券客户经理的可解释客户经营工作台原型。
>
> Explainable client-operations workbench for securities relationship managers.

**Version:** 0.6.0 · **Status:** local demo / portfolio prototype

AdvisorOps 解决的不是“再做一套完整 CRM”，而是 CRM 之上的日常经营问题：客户信息散落在电话、企业微信、外部系统和客户经理笔记里，客户经理需要知道 **今天手上要做什么、下一位值得联系谁、上次聊到哪里、下一步是什么**。

项目使用固定模拟数据，不连接中信证券或任何真实券商内部系统。

## Why AdvisorOps

核心闭环：

~~~text
零散客户信息
      ↓
完整 Activity
      ↓
Current Snapshot
      ↓
Discovery Engine
      ↓
发现区 → 开始跟进 → WorkItem → 工作区
                           ↓
                     新一轮沟通
                           ↓
                        Activity
                           └────────→ 回流
~~~

项目坚持三个原则：

- **AI 负责理解**：把自然语言、聊天截图和历史记录整理成候选结构化信息；
- **规则负责约束**：Priority、到期/逾期、冷静期和重复触达抑制保持确定性；
- **人负责决策**：解释性状态变化默认由客户经理确认后才落库。

## Product

### 1. 今日工作台

工作台分成两个不同队列：

- **工作区**：已经决定处理的客户，回答“我手上的事做到哪了？”
- **发现区**：当前存在新行动理由的客户，回答“如果现在有空，下一个应该找谁？”

发现区不是给所有客户强行打分。系统先做 eligibility 判断，再对候选客户使用可解释 Rule-based Priority。

进行中的工作项可以显式“取消跟进”或“结束跟进”：取消只撤销 WorkItem，必要时重新回发现区；结束会记为今日完成并留下 Activity，但不会伪造客户沟通或修改客户阶段/意向。

### 2. 对话式记录进展

记录客户沟通默认只需要：

- 一段自然语言；
- 可选聊天截图 / 资料图片；
- 沟通渠道。

系统会先生成结果卡：摘要、客户反馈、阶段、意向、下一步和下次联系时间。详细字段默认折叠，只有识别不准确时才展开修改。

图片支持 JPEG / PNG / WebP，确认保存后文件只落在本地 work/attachments/，Activity 保存附件元数据和哈希，附件不进入 Git。

### 3. 客户全景画像

客户画像不仅包含资产和风险，还包含：

- 粗粒度居住区域、职业、行业；
- 家庭阶段、家庭责任、未来重大安排；
- 收入、负债、现金流与流动性偏好；
- 投资经验、主要目标、期限和信息偏好；
- 沟通渠道 / 时间偏好；
- 兴趣、主要顾虑和建立信任的因素。

“决策偏慢”“重大事项会与家人商量”等软判断单独保存为 **待验证经营假设**，不作为事实，也不直接参与 Priority。

### 4. 客户经营判断

客户详情采用 action-first 信息结构，第一屏只回答三件事：

1. **当前状态**：客户现在处于什么阶段、真正关心什么、当前障碍是什么；
2. **下一步行动**：现在应该推进、等待还是先准备；如果要联系，需要问清哪些问题、做到什么算完成；
3. **下一次怎么沟通**：建议开场、沟通方式以及当前应该避免什么。

完整资产、经营事实和客户全景画像默认折叠到第二层。判断由已确认 Snapshot、WorkItem、最近 Activity 和画像即时生成，不额外调用模型；每条结论仍可展开查看依据。

### 5. 客户动态 / 多源信息

V0.6 提供三个 Mock 数据源：CRM、企业微信、行为数据，演示：

- incremental cursor；
- (source, source_event_id) 幂等；
- 确定事实自动写 Activity；
- 解释性变化生成 Change Proposal；
- 人工确认后才更新 Customer Snapshot。

### 6. 批量客户管理

“全部客户”支持：

- CSV 批量导入；
- 中文 / 英文字段别名归一化；
- 枚举、日期和重复客户检查；
- 导入前预览；
- 仅导入有效行；
- 当前筛选结果多选；
- 批量删除客户及其关联 Activity / WorkItem / Proposal；
- 删除后清理仅由这些客户引用的本地附件。

导入细节见 [docs/IMPORT-GUIDE.md](docs/IMPORT-GUIDE.md)。

## Architecture

~~~text
React + TypeScript + TanStack Query
                │
                ▼
             FastAPI
                │
        ┌───────┼────────┐
        ▼       ▼        ▼
  Priority   AIService  SyncService
        │       │        │
        └───────┼────────┘
                ▼
          WorkbenchService
                │
                ▼
           Repository
                │
                ▼
          SQLite + WAL
~~~

关键后端模块：

| Module | Responsibility |
| --- | --- |
| main.py | HTTP / REST 入口 |
| service.py | 业务流程编排 |
| repository.py | SQLite 数据访问 |
| priority.py | Discovery eligibility + Priority |
| judgment.py | 可追溯客户经营判断 |
| ai_service.py | 沟通抽取、摘要、Change Proposal |
| sync_service.py | 外部事件增量同步与幂等 |
| import_service.py | CSV 字段归一化、预览、校验 |
| context_pack.py | 脱敏 AI 咨询上下文 |
| attachments.py | 图片校验、保存和清理 |

## Data model

AdvisorOps 不把所有东西塞进一张客户表：

~~~text
Customer Snapshot  ─ 当前已确认认知
Activity Event     ─ 完整历史事实
WorkItem           ─ 客户经理当前执行工作
Change Proposal    ─ AI / 外部信息提出、尚未确认的解释
Field Change Audit ─ 字段为什么发生变化
~~~

Priority 是 derived data，不作为客户权威事实持久化。

## Quick start

### Prerequisites

- Python 3.12 recommended
- Node.js 22 recommended
- uv
- npm

### Backend

~~~bash
cd backend
cp .env.example .env
uv sync --frozen
uv run uvicorn app.main:app --reload --port 8010
~~~

不配置 AI 也能运行，记录链路会退化为人工确认模式。

如果需要启用结构化 AI：

~~~env
ADVISOROPS_AI_API_KEY=...
ADVISOROPS_AI_BASE_URL=https://your-openai-compatible-endpoint/v1
ADVISOROPS_AI_MODEL=your-model
ADVISOROPS_AI_MAX_COMPLETION_TOKENS=4096
~~~

### Frontend

~~~bash
cd frontend
npm ci
npm run dev
~~~

默认 Vite 会把 /api 和 /attachments 代理到 http://127.0.0.1:8010。

## Bulk import

推荐直接从页面下载模板。仓库也提供：

- [examples/customer-import-template.csv](examples/customer-import-template.csv)
- [examples/customer-import-sample.csv](examples/customer-import-sample.csv)

当前采用 **new-only import**：已有 customer_id 不会被覆盖；同名不同 ID 只提醒，不自动合并。

## Testing

Backend:

~~~bash
cd backend
uv lock --check
uv sync --frozen
uv run python -m compileall -q app tests
uv run pytest -q
~~~

Frontend:

~~~bash
cd frontend
npm ci
npm run typecheck
npm run build
npm audit --audit-level=high
~~~

GitHub Actions 会在 push / pull request 上执行后端测试和前端 typecheck/build。

## Repository structure

~~~text
advisorops/
├── backend/
│   ├── app/
│   └── tests/
├── frontend/
│   └── src/
├── docs/
├── examples/
├── .github/
├── SECURITY.md
└── README.md
~~~

## Documentation

- [docs/PRODUCT-MODEL.md](docs/PRODUCT-MODEL.md) — 产品模型
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — 当前技术架构
- [docs/FLOWS.md](docs/FLOWS.md) — 端到端业务流程
- [docs/DATA-MODEL.md](docs/DATA-MODEL.md) — 数据对象与状态约束
- [docs/IMPORT-GUIDE.md](docs/IMPORT-GUIDE.md) — CSV 导入规范
- [docs/EVOLUTION.md](docs/EVOLUTION.md) — 产品演进（Evo）
- [docs/RESEARCH-NOTES.md](docs/RESEARCH-NOTES.md) — 外部调研依据
- [CHANGELOG.md](CHANGELOG.md) — 版本变更
- [CONTRIBUTING.md](CONTRIBUTING.md) — 贡献与本地验证约定

## Security & privacy

- 仓库只允许模拟客户数据；
- .env、本地 SQLite、附件、Token 和日志不进入 Git；
- Context Pack 默认移除直接身份标识；
- 精确地址、身份证、证券账号、银行账号不属于公开 Demo 字段；
- 真实券商生产化需要独立完成 IAM、权限、审计、数据保留、网络边界、模型网关和个人信息治理。

详见 [SECURITY.md](SECURITY.md)。

## Non-goals

当前版本明确不做：

- 完整 CRM 替代；
- 真实券商内部系统集成；
- 自动金融产品推荐；
- 自动客户触达；
- 黑盒成交概率预测；
- RAG / 自主 Agent / 微服务；
- 生产级多租户与权限系统。

## Evolution

项目从“单列表 Priority Demo”逐步演进到“工作区 / 发现区 + Activity + WorkItem + Change Proposal + 多源同步 + 图片记录 + 批量管理”。完整决策历史见 [docs/EVOLUTION.md](docs/EVOLUTION.md)。

## License

当前仓库尚未授予开源复用许可证。公开 GitHub 用于作品集、学习和代码评审；如后续需要开放复用，再单独选择并加入许可证。
