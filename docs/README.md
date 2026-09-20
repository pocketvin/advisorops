# 项目文档索引

当前阶段：**产品与架构规划**。在 `PRODUCT-MODEL.md`、`ARCHITECTURE.md`、`FLOWS.md` 三份核心文档冻结前，不继续扩展业务实现。

## 唯一事实源

- `PRODUCT-MODEL.md`：产品定位、工作区/发现区、AI 职责、边界和验收目标。
- `ARCHITECTURE.md`：技术架构、模块边界、数据接入、同步方式和技术选型。
- `FLOWS.md`：客户动态、发现、执行、记录、回流、AI 咨询上下文的端到端流程。
- `DATA-MODEL.md`：核心实体、字段职责和状态约束。
- `IMPLEMENTATION-PLAN.md`：分阶段施工与验证顺序。
- `DEMO-SCENARIOS.md`：面试演示脚本。
- `RESEARCH-NOTES.md`：外部资料与设计依据。
- `REPOSITORY-GUIDE.md`：Git / GitHub 约定与后续 CI 准备。

## 文档原则

1. 项目不虚构已接入中信证券或任何券商内部系统。
2. V1 全部客户数据使用模拟数据。
3. 客户当前状态必须能追溯到完整活动记录，不能只保存 AI 抽取后的少数字段。
4. AI 负责理解、整理和辅助建议；确定性规则负责关键业务约束；客户经理保留最终确认。
5. 优先采用成熟、轻量方案，不提前引入微服务、消息队列、Redis、Celery、向量数据库或复杂 Agent。
6. 现有 `backend/` 是前一轮留下的早期 scaffold，不代表最终实现；正式施工前按本轮架构文档校正。
