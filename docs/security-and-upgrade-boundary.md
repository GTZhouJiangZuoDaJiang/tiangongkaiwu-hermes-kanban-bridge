# 安全与升级边界

## 禁止项

本仓库不得：

1. 保存 token、cookie、OAuth refresh token、浏览器 profile 或 `gh` 配置目录。
2. 直接读写 Hermes `kanban.db`。
3. import Hermes 内部 Python 模块作为稳定 API。
4. fork 或 vendor Hermes 源码。
5. 把 GitHub wrapper 输出中的认证信息写入日志。

## 允许项

本仓库允许：

1. 调用 `HOME=/home/zhouyu /home/zhouyu/.local/bin/gh-jiangzuodajiang ...`。
2. 调用 `hermes kanban ... --json`。
3. 生成 dry-run JSON。
4. 保存脱敏 fixtures。
5. 保存项目级 YAML 映射。

## 升级兼容策略

Hermes 高频升级时，本仓库只依赖公开入口：

- `hermes kanban` CLI
- `gh` CLI
- GitHub REST/GraphQL 的公开字段

若 Hermes CLI 参数变更，应优先修改本仓库的命令渲染层和测试，不修改 Hermes 源码。
