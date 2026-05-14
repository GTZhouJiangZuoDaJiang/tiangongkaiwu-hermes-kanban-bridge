# tiangongkaiwu-hermes-kanban-bridge

TianGongKaiWu 的 Hermes Kanban 松耦合集成实验仓。

本仓库只承载 **项目侧集成代码与测试**，不是 Hermes fork，也不 vendor Hermes 源码。

## 边界

本仓库做：

- 读取项目配置：`configs/tiangongkaiwu.yaml`
- 将 GitHub issue 映射成 Hermes Kanban task plan
- 生成 `hermes kanban create` 的 dry-run 参数
- 在需要时通过 Hermes 官方 CLI 创建 Kanban task
- 保留 fixtures、测试和验收脚本

本仓库不做：

- 不 fork Hermes
- 不 vendor Hermes 源码
- 不直接写 `kanban.db`
- 不 import Hermes 内部 Python API 作为稳定接口
- 不保存 token、cookie、OAuth 凭据或本地敏感配置

## 最小命令

Dry-run：

```bash
./scripts/github-issue-to-kanban \
  --config configs/tiangongkaiwu.yaml \
  --issue-json fixtures/github_issue_100.json \
  --assignee-role 将作大匠 \
  --dry-run
```

从 GitHub issue 读取并 dry-run：

```bash
./scripts/github-issue-to-kanban \
  --config configs/tiangongkaiwu.yaml \
  --repo GTZhou/TianGongKaiWu \
  --issue-number 100 \
  --assignee-role 将作大匠 \
  --dry-run
```

真实创建 Kanban task（建议首轮加 `--triage`，先验证创建与幂等，不触发 dispatcher 接单）：

```bash
./scripts/github-issue-to-kanban \
  --config configs/tiangongkaiwu.yaml \
  --repo GTZhou/TianGongKaiWu \
  --issue-number 100 \
  --assignee-role 将作大匠 \
  --triage
```

查询 Kanban task 状态：

```bash
./scripts/kanban-task-status \
  --config configs/tiangongkaiwu.yaml \
  --board tiangongkaiwu \
  --task-id <task-id>
```

生成并 dry-run GitHub 审计回写：

```bash
./scripts/kanban-to-github-comment \
  --config configs/tiangongkaiwu.yaml \
  --status-json /tmp/tgkw-kanban-status.json \
  --issue-number 100 \
  --dry-run
```

受控推进 `triage -> ready` 并观察 dispatcher / worker pickup：

```bash
./scripts/kanban-promote-watch \
  --config configs/tiangongkaiwu.yaml \
  --board tiangongkaiwu \
  --task-id <task-id> \
  --promote \
  --output /tmp/tgkw-kanban-promote-watch.json
```

该脚本只调用 Hermes 官方 CLI：`hermes kanban show/runs/specify --json`，不直接写 `kanban.db`，不 import Hermes 内部 Python API。

## GitHub 访问口径

所有 GitHub 访问默认使用身份隔离后的 wrapper：

```bash
HOME=/home/zhouyu /home/zhouyu/.local/bin/gh-jiangzuodajiang ...
```

该命令写在 `configs/tiangongkaiwu.yaml` 的 `github.gh_command` 中。不要把 token 写入本仓库。

## Hermes 调用口径

只走 Hermes 官方 CLI：

```bash
hermes kanban --board tiangongkaiwu create ... --json
```

如果后续要做 GitHub 回写，也应作为可选同步桥，不作为 Kanban task 创建的前置条件。

## 测试

```bash
python3 -m pytest -q
```

## 与 TianGongKaiWu 的关系

- 正式总账本：`GTZhou/TianGongKaiWu` issue / comment / PR
- 运行编排：Hermes Kanban
- 本仓库：二者之间的项目侧薄桥接与测试夹具

父议题：<https://github.com/GTZhou/TianGongKaiWu/issues/99>
子议题：<https://github.com/GTZhou/TianGongKaiWu/issues/100>
