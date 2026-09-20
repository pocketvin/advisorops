# Git / GitHub 约定

## 当前状态

- 本地仓库：已初始化
- 默认分支：main
- 远端仓库：暂不创建
- push：未授权，不执行
- 项目名：仍为工作名，因此不提前绑定 GitHub repo 名称

## 为什么现在不直接创建 GitHub 仓库

还有两个产品问题未冻结：

1. 最终项目名
2. 未来仓库是否公开

因此当前先保证本地仓库结构、历史和忽略规则干净。产品名冻结后再创建 remote，避免无意义重命名。

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

## CI 计划

等 Phase 1 有真实测试、前端入口完整后加入：

### backend

- uv sync --frozen
- pytest
- 可选 ruff

### frontend

- npm ci
- typecheck
- test
- build

当前不提交一个必然失败的 CI workflow。

## GitHub 安全准备

仓库创建后：

- 首选先 private
- 确认无真实客户信息后再考虑 public
- 开启 secret scanning / push protection（若账户能力可用）
- 增加 Dependabot
- 增加 SECURITY.md
- CI 只使用仓库 secrets，不写明文凭证

## 发布前公开检查

公开仓库前检查：

- README 未暗示接入中信内部系统
- 截图和 seed data 全部模拟
- 日志无真实手机号 / 账号 / token
- work/outputs 无临时敏感材料
- .env 未被跟踪
- Git 历史中没有误提交秘密
- License 已明确选择

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
