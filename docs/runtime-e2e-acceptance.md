# Runtime E2E Acceptance

本文件定义第二阶段最小运行态闭环：

> GitHub issue → Hermes Kanban task → 状态 / runs 查询 → GitHub issue 审计评论回写

## 前提

- Hermes Kanban board 已存在：`tiangongkaiwu`
- 不运行 standalone `hermes kanban daemon`
- 如需 dispatcher，使用 gateway 内置 dispatcher
- GitHub 访问使用身份隔离 wrapper：

```bash
HOME=/home/zhouyu /home/zhouyu/.local/bin/gh-jiangzuodajiang ...
```

## 1. 创建或复用 Kanban task

建议首轮仍使用 `--triage`，避免 dispatcher 立即接单：

```bash
./scripts/github-issue-to-kanban \
  --config configs/tiangongkaiwu.yaml \
  --repo GTZhou/TianGongKaiWu \
  --issue-number 101 \
  --assignee-role 将作大匠 \
  --triage \
  --output /tmp/tgkw-kanban-create-101.json
```

输出中的 `stdout` 是 Hermes Kanban 创建结果。重复执行应返回同一个 task id。

## 2. 查询运行态状态

```bash
./scripts/kanban-task-status \
  --config configs/tiangongkaiwu.yaml \
  --board tiangongkaiwu \
  --task-id <task-id> \
  --output /tmp/tgkw-kanban-status-101.json
```

状态摘要应包含：

- `task_id`
- `board`
- `status`
- `assignee`
- `tenant`
- `idempotency_key`
- `source_issue_url`
- `run_count`
- `latest_run_summary`

## 3. dry-run 生成 GitHub 回写评论

```bash
./scripts/kanban-to-github-comment \
  --config configs/tiangongkaiwu.yaml \
  --status-json /tmp/tgkw-kanban-status-101.json \
  --issue-number 101 \
  --dry-run \
  --output /tmp/tgkw-kanban-comment-101.json
```

dry-run 会生成：

- `comment_body`
- `body_file`
- `would_execute`

不会向 GitHub 发评论。

## 4. 真实回写 GitHub comment

确认 dry-run 内容后执行：

```bash
./scripts/kanban-to-github-comment \
  --config configs/tiangongkaiwu.yaml \
  --status-json /tmp/tgkw-kanban-status-101.json \
  --issue-number 101 \
  --output /tmp/tgkw-kanban-comment-101-real.json
```

返回的 `stdout` 应为 GitHub issue comment URL。

## 验收标准

- `python -m pytest -q` 通过
- `scripts/kanban-task-status` 能从公开 CLI 查询 task 状态
- `scripts/kanban-to-github-comment --dry-run` 能生成完整审计评论
- 真实模式能回写 GitHub issue comment
- 不直接写 `kanban.db`
- 不依赖 Hermes 内部 Python API
- 仓库内不保存 token / cookie / OAuth 凭据

## 当前边界

此阶段只验证单 task 的运行态回写。批量同步、自动关闭 issue、label 双向同步、正式 dispatcher 执行生产任务，均留到后续议题。
