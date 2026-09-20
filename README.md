# 证券客户经营工作台（工作名）

面向证券客户经理日常存量客户经营的轻量 Web 产品原型。

当前状态：**V1 可演示 / 可本地运行**。

它不是完整 CRM，也不虚构已经接入中信证券或其他券商内部系统。项目全部使用固定模拟客户数据，重点证明：

- 能把零散客户信息沉淀成连续经营上下文；
- 能区分“我手上正在做什么”和“下一位值得联系谁”；
- 能把客户经理自然语言沟通记录变成可确认的结构化经营状态；
- 能让状态、下一步、下一次联系时间和推荐队列形成闭环；
- 能完整追溯原始记录、结构化结果和字段变化。

## 产品结构

### 1. 今日工作台

**工作区**回答：

> 我已经决定处理哪些客户，现在做到哪一步？

包含：

- 待我处理
- 等待中
- 今日已完成

**发现区**回答：

> 如果现在有时间，下一位值得新发起动作的客户是谁？

发现区不是“所有客户强行打分”，而是：

```text
全量客户
→ 排除已在工作区 / 今日已完成 / 冷静期
→ 判断是否存在 actionable reason
→ 对候选客户做可解释 Rule-based Priority
→ 形成建议跟进列表
```

支持：

- 开始跟进
- 3 天后再看
- 人工置顶
- 查看原因
- 进入客户详情

Priority 只代表**今日经营工作顺序**，不代表成交概率、客户价值或投资建议。

### 2. 客户动态

用于处理分散来源的信息。

V1 提供三个固定 Mock 数据源：

- Mock CRM
- Mock 企业微信
- Mock 行为数据

支持：

- 主动“立即刷新”
- incremental cursor
- `(source, source_event_id)` 幂等
- 各来源独立同步状态
- 确定事实自动写 Activity
- 企业微信文本调用 Kimi K3 生成 Change Proposal
- AI 解释性变化必须人工确认后才修改 Customer Snapshot

电话、线下等无法自动获得的信息，可以从任意客户详情直接点击“记录客户动态”补录。

### 3. 客户档案

40 个固定模拟客户，不使用随机 Faker 生成。

每个客户保留：

- 年龄段 / 客户等级 / 风险等级
- 总资产区间 / 可投资资金区间 / 持仓摘要
- 最近登录 / 最近交易
- 近 30 日资产变化
- 最近关注产品主题 / 最近咨询主题
- Relationship Stage / Intent Level
- 当前需求 / 当前障碍 / 当前进展
- 下一步 / 下一次联系时间 / 冷静期
- 完整 Activity Timeline
- Field Change Audit
- 当前 WorkItem
- 待确认 AI Proposal

客户列表支持：

- 搜索
- 关系阶段筛选
- 风险等级筛选
- 当前意向筛选
- 资产区间筛选
- 当前经营优先级 / 最近联系 / 姓名排序

## AI：Kimi K3

项目原则：

> **AI 负责理解，规则负责约束，人负责决策。**

本机开发环境复用已配置的 Kimi K3（OpenAI-compatible Chat Completions），不把 API Key 写进仓库。

V1 已实现：

- 沟通原话 → Kimi K3 结构化候选结果
- 关系阶段 / 意向 / 需求 / 障碍 / 下一步 / 下次联系时间 Proposal
- 客户 30 秒经营摘要
- AI 结果预填后人工修改与确认
- 外部企业微信消息 → pending Change Proposal
- 脱敏 AI Context Pack 预览与复制

AI 不直接修改：

- 身份信息
- 账户信息
- 权威风险等级
- 正式适当性信息
- 真实资产/持仓事实

AI 失败时，原始记录仍可手工保存，模型不是客户记录链路的单点故障。

## 高频业务闭环

### 明确拒绝

记录“明确拒绝”后：

- relationship_stage → rejected
- intent → low
- 自动进入 30 天触达冷静期
- 清除人工置顶
- 当天完成本次 WorkItem
- 冷静期内不进入发现区
- 冷静期结束后只形成“低打扰服务复核”，不会直接恢复成营销跟进

### 再考虑 3 天

记录“再考虑 3 天”后：

- relationship_stage → considering
- 保存 `next_contact_at`
- 当天完成本次 WorkItem
- 未到期不进入发现区
- 到期后自动重新进入发现区
- 逾期后提高跟进紧迫度

V1 不依赖凌晨定时任务修改状态；Follow-up State 根据当前时间动态计算。

### 新行为信号

新的资产变化 / 产品关注等确定事实进入 Activity，并更新结构化行为字段。

若当前没有 active WorkItem，系统可产生新的发现理由：

> 先核实新信号背后的真实需求。

不会直接生成具体金融产品推荐。

## 技术栈

- React
- TypeScript
- Vite
- TanStack Query
- Python
- FastAPI
- Python `sqlite3` + 薄 Repository
- SQLite WAL
- pytest

V1 不引入 Redis、Celery、Kafka、向量数据库、微服务或自主 Agent。

## 本地运行

### Backend

```bash
cd /Users/yu0/Workspace/10-Projects/Securities-Client-Workbench/backend
uv sync --frozen
uv run uvicorn app.main:app --reload --port 8010
```

AI 配置优先读取：

- `WORKBENCH_KIMI_API_KEY`
- `WORKBENCH_KIMI_BASE_URL`
- `WORKBENCH_KIMI_MODEL`

本机开发环境在这些变量未设置时，可复用相邻 Floweroll 项目已经配置的 Planner Kimi 环境；不会复制或打印 API Key。

### Frontend

```bash
cd /Users/yu0/Workspace/10-Projects/Securities-Client-Workbench/frontend
npm ci
npm run dev
```

Vite 默认把 `/api` 代理到 `127.0.0.1:8010`。

## 验证

本地工程门：

```bash
cd backend
uv run pytest -q

cd ../frontend
npm run typecheck
npm run build
```

当前 V1：

- 31 条后端领域 / 数据库 / 同步 / AI 边界测试
- FastAPI 真实 API 链路
- Kimi K3 真实结构化调用
- TypeScript typecheck
- Vite production build
- GitHub Actions backend/frontend CI
- Dependabot 配置

## Demo 工具

顶部“演示工具”支持：

- 时间推进 +1 天
- 时间推进 +3 天
- 重置固定演示数据

用于现场演示“再考虑 → 未到期 → 到期回流”，无需真的等待三天。

## 数据与合规边界

- 全部客户均为模拟数据。
- 不暗示已经接入任何券商真实 CRM、企业微信或电话系统。
- Priority 不是投资建议或成交概率。
- 具体产品/服务仍应遵循真实机构的权限和投资者适当性流程。
- AI Context Pack 默认去除姓名、手机号、账号、身份证、住址等直接身份信息。
- 真实机构落地时，应接公司批准的数据源与 AI Gateway，而不是默认把真实客户资料复制到个人外部 AI。

## 文档

- `docs/PRODUCT-MODEL.md`
- `docs/ARCHITECTURE.md`
- `docs/FLOWS.md`
- `docs/DATA-MODEL.md`
- `docs/DEMO-SCENARIOS.md`
- `docs/RESEARCH-NOTES.md`
- `docs/REPOSITORY-GUIDE.md`
