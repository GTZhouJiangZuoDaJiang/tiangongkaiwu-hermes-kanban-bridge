# 最小闭环

## 目标

先跑通一条最小链路：

> GitHub issue → 项目配置 → Hermes Kanban task plan → `hermes kanban create`

本阶段不做完整双向同步，不做消息总线，不替代 GitHub 总账本。

## 输入

- GitHub issue JSON
- `configs/tiangongkaiwu.yaml`
- assignee role，例如 `将作大匠`
- Hermes Kanban task id（运行态回写阶段）

## 输出

- dry-run JSON：包含 `plan` 与 `would_execute`
- 真实模式：调用 Hermes CLI 创建 Kanban task
- 状态摘要 JSON：包含 task id、status、assignee、idempotency-key、runs 摘要
- GitHub 审计评论：可 dry-run，也可真实回写

## 幂等键

默认：

```text
github:GTZhou/TianGongKaiWu#{issue_number}
```

Hermes Kanban 的 `--idempotency-key` 用于防止同一 GitHub issue 重复创建未归档任务。

## 状态分工

- GitHub：正式审计、需求、验收、跨角色留痕
- Hermes Kanban：运行态任务、派发、领取、阻塞、完成、run history
- 本仓库：配置映射、命令生成、fixtures、验收脚本

## 暂不纳入

- GitHub label 双向同步
- Telegram / Hermes 群通知镜像
- 多 issue 批量同步
- Hermes dashboard 定制
- 任何 Hermes 内部数据库写入
