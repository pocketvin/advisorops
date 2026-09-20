# 实施计划

## 总原则

先做完整 vertical slice，再扩数据和功能。

不按“先把整个后端写完 → 再写前端”的方式推进。

每个阶段都必须能运行、能演示、能测试。

## Phase 0：规划冻结

本阶段目标：

- 产品定位
- 工作区 / 发现区
- 核心数据对象
- AI 边界
- 数据接入策略
- 技术选型
- Demo 主线
- Git / GitHub 约定

完成标准：

- 文档不存在互相冲突
- 不再使用“单一客户状态解决所有问题”
- 不再使用“所有客户统一强行打分”
- 不再把人工置顶写成普通分数项
- 不把 AI 直接写解释性客户字段作为默认行为

## Phase 1：单客户闭环

只用 1～3 个固定客户。

跑通：

1. 发现区出现客户
2. 显示为什么值得处理
3. 开始跟进
4. 进入工作区
5. 记录自然语言沟通
6. 结构化 Preview
7. 人工确认
8. Activity + Snapshot + WorkItem 同步更新
9. 客户离开今天待处理
10. 时间线完整可复盘

必须先测业务状态，再做视觉 polish。

## Phase 2：时间回流

跑通：

- 再考虑 3 天
- 未到期不出现
- 到期进入发现区
- 逾期紧迫度上升
- 明确拒绝进入 cooldown
- cooldown 后仅允许服务复核

测试使用可注入 clock，不等待真实三天。

## Phase 3：客户动态与同步

实现 Mock Connectors：

- Mock CRM
- Mock WeCom
- Mock Behavior

实现：

- 手动刷新
- incremental cursor
- idempotency
- 单来源失败隔离
- Change Proposal
- 最近同步时间

此时再评估是否加入单实例 APScheduler 做 10 分钟级自动演示同步。

## Phase 4：40 个固定模拟客户

不是 Faker 随机堆数据。

预设：

- 到期
- 逾期
- 刚联系无需重复
- 考虑中未到期
- 明确拒绝
- 行为变化
- 工作区等待反馈
- 人工置顶
- 长期沉默
- 已完成今日动作

确保 Demo 每次重置后顺序稳定。

## Phase 5：完整前端

完成：

- 今日工作台
- 客户列表
- 客户详情
- 时间线
- 客户动态
- 状态变化确认
- 筛选 / 搜索
- Reset Demo

再进行：

- 动画
- 排序变化反馈
- 视觉层级
- 空状态
- loading / error

## Phase 6：AI V1

顺序：

### 6.1 沟通记录结构化

最高优先级。

输入自然语言，输出：

- 结构化经营摘要
- 客户反馈
- need
- obstacle
- stage proposal
- intent proposal
- next step
- next contact

人工确认。

### 6.2 客户 30 秒摘要

由最近若干 Activity + Snapshot 生成。

### 6.3 NBA 文案增强

规则决定动作类型，AI 只负责结合上下文写得具体。

### 6.4 AI 咨询上下文

脱敏、预览、复制。

## Phase 7：质量收敛

### 后端核心测试

- duplicate event 不重复写入
- sync failure 不推进 cursor
- active WorkItem 不重复进入发现区
- completed_today 当日不重新发现
- recent contact + no new reason 被抑制
- due follow-up 正常进入
- rejected cooldown 正常生效
- AI proposal 未确认不修改 Snapshot
- apply proposal 写 audit
- AI 失败仍可手工保存 Activity

### 前端

- mutation 后相关 query 正确 invalidate
- 工作区/发现区不会重复显示同客户
- 刷新状态清晰
- 表单失败不丢原始记录

## Phase 8：GitHub / Demo 发布

代码稳定后：

- 生成 dependency lock files
- 添加 GitHub Actions
  - backend tests
  - frontend build / tests
- Dependabot
- SECURITY.md
- README 演示截图
- 架构图
- Demo 数据声明
- 部署 Demo

不在 lock file 和测试命令稳定前提交一个必然失败的 CI。

## 不做的提前优化

在以下条件出现前不引入：

- Redis：单机缓存/状态明显不够
- Celery / 队列：真实后台任务需要独立可靠执行
- PostgreSQL：多人/部署/并发需求出现
- WebSocket：轮询和 query invalidation 已无法满足
- RAG：存在真实大规模非结构化资料检索需求
- Agent：存在明确需要自主多步工具执行的任务
