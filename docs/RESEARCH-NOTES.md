# 外部调研与设计依据

调研时间：2026-09-20

本文件记录“为什么这样选”，避免后续为了技术复杂度重复推翻简单方案。

## 1. CRM 的活动时间线模型

参考 HubSpot CRM：

- CRM record 之外单独存在 calls、emails、notes、tasks、meetings 等 activities。
- activities 可关联到联系人等 CRM 对象。
- Calling 能记录通话并在 CRM 中查看记录和笔记。

参考：

- https://developers.hubspot.com/blueprints/etl
- https://developers.hubspot.com/docs/api-reference/latest/crm/extensions/calling-extensions/receive-incoming-calls
- https://developers.hubspot.com/blog/how-to-use-apis-to-supercharge-hubspots-crm

对本项目的结论：

> 不把一次客户沟通压缩成几个 Customer 字段后丢弃，而是保留 Activity timeline，再维护 Current Snapshot。

## 2. 数据同步采用 Connector + Cursor

Airbyte 的成熟方向是把各种来源抽象成 connectors，并支持连接与同步，而不是把每个来源的业务代码散落在产品层。

参考：

- https://docs.airbyte.com/

本项目不引入 Airbyte 本身，因为对 Demo 太重；只借鉴：

- Connector 抽象
- 增量 cursor
- sync state
- 来源隔离

V1 自己实现薄接口即可。

## 3. FastAPI 后台任务边界

FastAPI 官方 BackgroundTasks 是“请求返回后执行”的轻量机制。官方也明确提示，重后台计算如果无需共享同一进程内存，可能更适合 Celery 等更大的工具，但会带来 Redis / RabbitMQ 等额外复杂度。

参考：

- https://fastapi.tiangolo.com/tutorial/background-tasks/

结论：

- 不拿 FastAPI BackgroundTasks 当长期轮询调度器。
- V1 的同步业务统一写成普通 service。
- 手动刷新直接调用 service。
- 真需要周期任务时单独挂 scheduler。

## 4. APScheduler 只作为单实例 Demo 调度候选

APScheduler 支持 interval / cron 等调度。

但官方文档也说明：

- 默认 MemoryDataStore 在进程退出后不保留任务。
- 多 scheduler 共享持久存储时，需要 event broker 协调，避免重复处理。

参考：

- https://apscheduler.readthedocs.io/en/master/userguide.html

结论：

> V1 可以在单实例 Demo 中使用，但不要把它包装成真实券商生产级调度方案。

## 5. FastAPI + SQLite 数据访问

调研过 SQLModel：FastAPI 官方 SQL 教程使用 SQLModel，它建立在 SQLAlchemy 和 Pydantic 之上，也支持从 SQLite 走向 PostgreSQL。

参考：

- https://fastapi.tiangolo.com/tutorial/sql-databases/
- https://sqlmodel.tiangolo.com/

当前 V1 最终选择仍是 Python 标准库 `sqlite3` + 薄 Repository，原因是：

- 当前只有少量表和明确查询，已有 SQL 很直接
- 不为 ORM 本身增加依赖和迁移成本
- Service 与 SQL 已通过 Repository 隔离
- 未来需要 PostgreSQL / Alembic 时再迁移，不影响上层工作流

SQLModel 保留为后续候选，而不是 V1 强制依赖。

## 6. SQLite WAL

SQLite 官方 WAL 文档说明：

- readers 不阻塞 writer，writer 不阻塞 readers；
- 读写可以并发；
- 仍然同一时刻只有一个 writer；
- WAL 依赖同一台主机，不适合网络文件系统。

参考：

- https://www.sqlite.org/wal.html

结论：

> 对单机求职 Demo 合适；真实多人服务再迁 PostgreSQL。

## 7. 前端服务器状态：TanStack Query

TanStack Query 提供：

- query cache
- mutation
- mutation 成功后的 invalidate / refetch
- staleTime
- 可选 refetchInterval
- query cancellation

参考：

- https://tanstack.com/query/latest/docs/framework/react/guides/invalidations-from-mutations
- https://tanstack.com/query/latest/docs/framework/react/guides/important-defaults

结论：

> 工作台里“记录跟进后工作区和发现区同时刷新”“手动刷新客户动态”等行为不自己造 cache 状态机，用 TanStack Query。

V1 不再额外加 Redux / Zustand。

## 8. GitHub CI

GitHub 官方对 Python 和 Node.js 都提供标准的 build / test Actions 工作流模板，并推荐 Node 使用 lock file + npm ci 获得可重复安装。

参考：

- https://docs.github.com/en/actions/tutorials/build-and-test-code/python
- https://docs.github.com/en/actions/tutorials/build-and-test-code/nodejs

结论：

> 当前先初始化 Git 和规划 CI；等 Python / npm lock file 与正式测试命令稳定后再加入不会失败的 CI。

## 9. 证券客户管理和适当性边界

证监会《证券经纪业务管理办法》强调：

- 客户管理职责
- 客户适当性
- 业务流程事前、事中、事后管控
- 内部合规和信息系统建设

参考：

- https://www.csrc.gov.cn/csrc/c100028/c6987711/content.shtml

《证券期货投资者适当性管理办法》要求经营机构了解投资者相关信息、落实适当性管理，并保存相关资料。

参考：

- https://www.csrc.gov.cn/csrc/c106256/c1653849/content.shtml

结论：

- Priority 只是工作顺序，不是投资建议。
- AI 不替代正式适当性流程。
- 产品/服务匹配必须保留人工和权威系统边界。

## 10. 客户数据和 AI 外部上下文

《证券期货业网络和信息安全管理办法》覆盖投资者个人信息保护。

参考：

- https://www.csrc.gov.cn/csrc/c100028/c7202729/content.shtml

《个人信息保护法》将金融账户等列为敏感个人信息，对敏感个人信息处理提出更严格要求。

参考：

- https://www.cac.gov.cn/2021-08/20/c_1631050028355286.htm

结论：

Demo：

- 只使用模拟客户数据。

架构：

- AI Context Pack 默认做白名单和脱敏。
- 不设计“完整真实客户数据一键复制到个人外部 AI”作为生产方案。
- 企业真实落地应接公司批准的 AI Gateway / 模型服务。


## 11. Kimi K3 推理强度

Kimi 官方文档说明：

- Kimi K3 始终进行推理。
- 顶层 `reasoning_effort` 支持 `low / high / max`。
- 默认值是 `max`。
- 官方结构化输出支持 `response_format=json_schema` + `strict=true`，最终只解析 `message.content`。

参考：

- https://platform.kimi.com/docs/guide/use-reasoning-effort
- https://platform.kimi.com/docs/guide/kimi-k3-quickstart

本项目的自然语言沟通抽取和 30 秒摘要属于低复杂度结构化知识工作，不需要最大推理深度，因此 V1 显式使用：

```text
reasoning_effort = low
```

目的：

- 降低交互延迟
- 降低 reasoning token 消耗
- 给最终 JSON 留出更稳定的 completion 预算

复杂客户沟通策略本身不在项目内强行用同一调用解决，而是通过脱敏 AI Context Pack 交给更强的独立 AI 会话。
