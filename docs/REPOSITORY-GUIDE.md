# Git / GitHub 约定

## 当前状态

- 本地仓库：已初始化
- 默认分支：main
- 远端仓库：暂不创建
- push：未授权，不执行
- 项目名：AdvisorOps
- 推荐 GitHub repo：`advisorops`

## GitHub 发布状态

项目名已经冻结为 **AdvisorOps**。当前仍不自动创建 remote / push，因为远端创建和公开发布需要用户明确执行。

本地发布前目标：

- `main` clean tree；
- README / Security / Import Guide / Evolution 完整；
- CI 与 lock file 可重复；
- 仓库无真实客户数据、凭证、本地数据库或附件；
- package / API 元数据统一为 AdvisorOps v0.6.0。

## Commit 约定

保持小而清晰：

- `docs:` 产品 / 架构 / 研究文档
- `feat:` 新功能
- `fix:` 缺陷修复
- `refactor:` 不改变产品行为的结构调整
- `test:` 测试
- `chore:` 工程和仓库维护

每个施工阶段结束前：

```bash
git status --short
git diff --check
```

必须说明是否有未提交修改。

## 分支

当前个人快速开发：

- main 保持可运行
- 较大施工可临时 feature branch
- 不为了流程而制造大量长期分支

## Secrets

禁止提交：

- API keys
- tokens
- 密码
- 真实客户数据
- .env
- 本地数据库

只允许：

- .env.example
- 模拟数据
- 非敏感默认配置

## Lock files

正式开始依赖安装后必须提交：

- backend 的 uv.lock
- frontend 的 package-lock.json

GitHub CI 应使用 lock file 做可重复安装。

## CI

已加入 `.github/workflows/ci.yml`：

### backend

- uv lock --check
- uv sync --frozen
- compileall
- pytest

### frontend

- npm ci
- typecheck
- production build
- npm audit --audit-level=high

CI 不依赖真实 AI Key；模型相关测试使用 Fake Client，避免 CI 消费外部额度。

## GitHub 安全准备

仓库创建后：

- 首选先 private
- 确认无真实客户信息后再考虑 public
- 开启 secret scanning / push protection（若账户能力可用）
- Dependabot 已配置（uv / npm / GitHub Actions）
- SECURITY.md 已加入
- CI 只使用仓库 secrets，不写明文凭证

## 发布前公开检查

公开仓库前检查：

- README 未暗示接入中信内部系统
- 截图和 seed data 全部模拟
- 日志无真实手机号 / 账号 / token
- work/outputs 无临时敏感材料
- .env 未被跟踪
- Git 历史中没有误提交秘密
- License 状态已明确：当前未授予开源复用许可证；若要开放复用，再单独选择许可证

## GitHub README 最终应包含

- 业务问题
- 产品截图 / GIF
- 工作区 + 发现区 + 客户动态
- 一条完整 Demo 流程
- 架构图
- 技术栈
- 如何运行
- 数据声明
- 合规边界
- 测试方式
