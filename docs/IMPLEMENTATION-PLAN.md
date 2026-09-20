# 实施计划与 V1 状态

更新：2026-09-20

## 当前结论

V1 已完成到“可本地运行、可演示、可继续真机体验修改”的状态。

完成的主链：

```text
客户动态 / 人工记录
→ 完整 Activity
→ AI / 规则理解
→ Change Proposal
→ 人工确认
→ Customer Snapshot
→ 发现区
→ WorkItem
→ 工作区
→ 记录沟通
→ 状态更新
→ 未来到期后重新发现
```

## Phase 0：产品与架构规划 — 完成

- 工作区 / 发现区分离
- Relationship Stage / Follow-up State / Work State 分离
- AI 写入边界
- Connector + cursor 同步思路
- Snapshot + Activity + WorkItem + ChangeProposal 数据模型
- Git / GitHub 约定

## Phase 1：最小完整闭环 — 完成

- 发现区出现客户
- 可解释排序原因
- 开始跟进
- 进入工作区
- 完整原始沟通记录
- 结构化经营字段
- 人工确认
- Activity + Snapshot + WorkItem 原子更新
- Timeline 与 Field Change Audit

## Phase 2：时间回流 — 完成

- 再考虑 3 天
- 未到期抑制
- 到期回流
- 逾期紧迫度
- 明确拒绝 30 天 cooldown
- cooldown 后低打扰服务复核
- 可注入 / 可推进 Demo Clock

## Phase 3：客户动态与同步 — 完成

V1 Mock 来源：

- Mock CRM
- Mock WeCom
- Mock Behavior

实现：

- 主动刷新
- incremental cursor
- `(source, source_event_id)` 幂等
- 单来源错误状态
- SyncState
- 完整 Activity
- Kimi Change Proposal
- pending / apply / reject

V1 **不加入 APScheduler**。原因：求职 Demo 并不需要持续后台服务；手动刷新可以更清楚展示数据同步机制，真实机构落地再按部署方式选择调度器或 webhook。

## Phase 4：固定模拟客户 — 完成

40 个固定客户，覆盖：

- 到期 / 逾期
- 刚联系无需重复触达
- 考虑中未到期
- 明确拒绝 / 冷静期
- 行为变化
- 工作区待处理
- 等待客户
- 等待内部资料
- 今日已完成
- 人工置顶
- 长期沉默

不使用随机 Faker 决定核心演示场景。

## Phase 5：完整前端 — 完成

主入口：

- 今日工作台
- 全部客户
- 客户动态

已实现：

- 工作区 / 发现区
- 搜索 / 状态 / 风险 / 意向 / 资产筛选
- 当前优先级 / 最近联系 / 姓名排序
- 客户详情 Drawer
- Activity Timeline
- Field Change Audit
- pending AI Proposal
- 人工置顶
- 3 天后再看
- 任意客户手工记录动态
- 明确拒绝 / 再考虑快捷模板
- Reset Demo
- Demo Clock
- loading / error / empty state

## Phase 6：AI V1 — 完成

模型：本机已有 **Kimi K3**。

实现：

- 沟通自然语言 → 结构化候选字段
- JSON Schema 输出 + 容错解析 + 有界重试
- 模型失败可手工继续
- 客户 30 秒摘要
- 外部企业微信消息 → Change Proposal
- AI Context Pack
- Context Pack 默认脱敏

没有做“AI 黑盒 Priority”。发现和排序仍由确定性规则控制。

NBA 文案仍以规则为主，刻意没有每次都额外调用 Kimi，以降低延迟、费用和不稳定性。

## Phase 7：质量收敛 — 完成

后端覆盖：

- SQLite WAL / foreign keys
- legacy demo schema rebuild
- active WorkItem 去重
- completed_today 当日抑制
- recent contact suppression
- new signal exception
- due / overdue
- defer
- rejected cooldown 与恢复
- pin 不污染 score
- AI Proposal 未确认不改 Snapshot
- apply Proposal 写 audit
- Sync cursor / idempotency
- 40 客户固定 seed
- Context Pack 脱敏
- 客户筛选 / 排序

前端：

- TypeScript strict typecheck
- Vite production build
- 实际后端联调
- 浏览器人工走查

## Phase 8：GitHub 工程准备 — 完成（未创建远端）

已加入：

- `backend/uv.lock`
- `frontend/package-lock.json`
- GitHub Actions backend / frontend CI
- Dependabot：uv / npm / GitHub Actions
- Secret / local DB ignore

暂未执行：

- 创建 GitHub remote
- push
- 公开仓库
- 部署公开 Demo

原因：最终项目名称和仓库公开策略尚未由用户确定，且没有 push / 发布授权。

## 后续不是“补 V1”，而是体验优化

下一轮应以用户实际体验反馈为主，例如：

- 首页信息密度
- 卡片字段取舍
- 动效与交互手感
- AI 提取字段是否符合真实沟通习惯
- Priority 权重是否符合实际客户经理判断
- 客户动态是否需要自动轮询
- 最终项目命名
- 面试演示脚本和截图

不应在没有真实需求前引入 Redis、Celery、Kafka、RAG、Agent、微服务或机器学习转化率模型。
