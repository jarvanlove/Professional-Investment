# Architecture

> 详细设计见 `docs/superpowers/specs/2026-08-05-signal-dashboard-design.md`（一期：信号仪表盘 + 交易日志）。

## System Shape

分层 Monorepo，纯本地单机运行：

```
packages/quant-core/   纯 Python 算法库（零 IO、纯函数、可单测）
services/quant-api/    FastAPI + SQLAlchemy + SQLite（数据管道 + HTTP 层）
apps/web/              Next.js (App Router) + TypeScript + Tailwind + shadcn/ui
```

运行形态：quant-api 监听 `localhost:8010`，apps/web 监听 `localhost:3010`，web 的 BFF Route Handlers 聚合转发 quant-api。SQLite 文件位于 `services/quant-api/data/investment.db`，不提交 Git。

## Module Boundaries

| Module | Owns | Must not do |
|---|---|---|
| `quant-core` | 指标计算、趋势评分、分数凯利仓位、市场模式判定、买卖规则(B1-B4/S1-S4/P1-P2)、约束投影、费用规则 | import 任何 Web/DB/网络框架；直接读写数据库或文件 |
| `quant-api` | akshare 数据抓取与清洗、手动录入兜底、SQLite 持久化、调用 quant-core 生成 SignalReport、HTTP API | 自行实现策略规则（一律委托 quant-core） |
| `apps/web` | 四个页面的渲染与交互、BFF 聚合、stale 数据提示 | 包含任何策略计算逻辑；绕过 BFF 直连数据库 |

## Data / Contract Boundaries

- Data model：5 张表 —— `funds`、`nav_history`、`trades`、`weekly_signals`、`account_state`（详见设计文档第 4 节）
- API contract：`/api/nav` `/api/signals` `/api/portfolio` `/api/trades` `/api/rebalance`；计算失败返回 422 + 结构化错误
- Auth/permission model：无（纯本地单机单用户，一期非目标）
- External integrations：akshare（天天基金/东方财富公开净值接口）；抓取解析集中在 quant-api 数据管道层单点

## Invariants

- 策略规则只有一个实现来源：`quant-core`；前端和 API 层不得复制规则逻辑。
- 所有信号基于已确认净值（未知价原则）；不得引入盘中实时信号。
- 规则参数集中在 `quant-core/config.py` 的 dataclass，不得散落在代码中。
- `weekly_signals` 快照只增不改，保证可复盘"当时系统说了什么"。
- Do not change module boundaries without updating this file.
- Do not change public behavior without updating tests or acceptance criteria.
- Do not introduce new infrastructure without an explicit task and rationale.

## When To Update This File

Update this file when:

- Module boundaries, data flow, API contracts, auth boundaries, or external integrations change.
- A new runtime, service, queue, database, storage layer, or deployment dependency is introduced.
- A repeated implementation rule should become a durable architecture constraint.

For significant decisions, add an ADR in `docs/adr/` and optionally summarize it in the project wiki decisions page.

## Architecture Decisions

- 2026-08-05：选定"分层 Monorepo（方案 A）"——quant-core 独立为纯算法库，为三期 agent 平台复用算法层预留路径。依据：`docs/superpowers/specs/2026-08-05-signal-dashboard-design.md`；替代方案（Next.js 全栈为主 / FastAPI 全包）已评估并否决。
