# Testing

## 一条命令

`pnpm test`（根目录）= quant-core pytest + quant-api pytest + web vitest。

## 分层

| 层 | 命令 | 关键测试 |
|---|---|---|
| quant-core | `uv run --directory packages/quant-core pytest` | `tests/test_golden_examples.py`：PDF 第13章算例 A/B/C 金额必须一致（±1元） |
| quant-api | `uv run --directory services/quant-api pytest` | 账本校验、nav 幂等导入、stale 标记、信号端到端（内存 SQLite） |
| web | `pnpm --dir apps/web test` | 页面渲染冒烟（mock fetch） |

## 红线

- 改动 `quant_core/config.py` 任何参数 → 必须重跑黄金测试；破坏算例需在 commit message 说明原因。
- 任何买入建议必须带理由代码与闸门结果；UI 不得出现"盘中/实时"字样。

## Minimum Verification Matrix

| Change type | Required checks |
|---|---|
| Documentation/config only | Read-through and affected-link check |
| UI/frontend | Build/typecheck/lint where available plus manual UI smoke |
| Backend/domain/API | Targeted test plus startup/request smoke |
| Database/auth/security/deployment | Dedicated review, migration/rollback notes, and manual smoke |

## Completion Rule

Report exact commands run. If commands are TODO or cannot run locally, state the blocker and the remaining risk.

## When To Update This File

Update this file when:

- Verification commands change.
- A new test class, smoke path, or manual check becomes required.
- A bug fix adds a regression path that future agents must keep running.
