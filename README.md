# 证券客户经营工作台（工作名）

用于证券客户经理日常存量客户经营的轻量 Web 原型。

这不是完整 CRM，也不连接任何券商内部系统。项目使用模拟客户数据，重点演示：

- 今日重点客户动态排序
- 可解释的 Rule-based Prioritization
- Next Best Action（下一步工作建议）
- 客户跟进状态机与时间线
- 拒绝降权、再考虑到期回流、人工置顶、行为信号升权
- 投资者适当性与人工确认边界

## 技术栈

- React + TypeScript + Vite
- Python + FastAPI
- SQLite（Python sqlite3）
- 规则引擎独立于 Web 框架，便于测试和后续替换

## 目录

- backend/app：API、SQLite repository、规则引擎、种子数据
- backend/tests：核心规则与业务闭环测试
- frontend/src：工作台、客户列表、详情抽屉与跟进操作
- docs：产品模型和演示场景

## 本地启动

依赖安装完成后，在 backend 中运行 uv sync 和 uvicorn；在 frontend 中运行 npm install 和 npm run dev。
