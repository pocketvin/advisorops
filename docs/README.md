# 项目文档索引

当前阶段：**V1 已实现，进入用户体验测试与迭代。**

## 事实源

- `PRODUCT-MODEL.md`：产品定位、工作区 / 发现区、AI 职责与边界。
- `ARCHITECTURE.md`：技术架构、模块边界、同步与数据访问。
- `FLOWS.md`：客户动态、发现、执行、记录、回流、AI Context 的端到端流程。
- `DATA-MODEL.md`：核心实体、字段职责和状态约束。
- `IMPLEMENTATION-PLAN.md`：V1 已完成内容与后续方向。
- `DEMO-SCENARIOS.md`：面试演示主线。
- `RESEARCH-NOTES.md`：外部调研与技术选择依据。
- `REPOSITORY-GUIDE.md`：Git / GitHub / CI / Secrets 约定。

## 当前工程原则

1. 不虚构已接入中信证券或任何券商内部系统。
2. V1 全部客户数据为固定模拟数据。
3. Customer Snapshot 必须能追溯到完整 Activity。
4. AI 负责理解和候选建议；确定性规则负责关键约束；客户经理保留最终确认。
5. 权威事实与 AI 解释性字段严格区分。
6. Kimi K3 失败时不阻塞手工记录。
7. 优先轻量成熟方案，不提前引入微服务、消息队列、Redis、Celery、向量数据库或复杂 Agent。
