# Product Spec

## Product

- Name: Professional-Investment
- Project slug: `professional-investment`
- Target users: 项目所有者本人（个人单用户，本地单机）
- Core problem: 手工执行《四只基金规则化交易与动态仓位管理方案》（`docs/product/`）成本高、易情绪化——需要平台自动计算评分/信号/目标仓位并记录交易日志
- Promise: 每周五净值更新后一键得到四道闸门校验过的买卖建议（含理由代码），长期演化为以被验证算法为底层的专业 agent 平台

## Current Scope

一期（信号仪表盘 + 交易日志），Must have:

- 净值数据自动抓取（akshare）+ 手动录入兜底（CSV/单条修正），失败标记 stale
- 每周信号页：趋势评分(0-5)、四道闸门逐项结果、建议动作（B1-B4/S1-S4/P1-P2/N0 + 金额上限）
- 仪表盘：权重 vs 目标、组合回撤、市场模式、现金比例
- 交易日志：录入自动带持有天数与赎回费估计；按理由代码筛选
- 持仓与资金：批次份额、费用窗口、风险单元使用进度
- quant-core 黄金测试：PDF 第 13 章算例 A/B/C 金额完全一致

Explicitly not doing unless added to `TASKS.md`:

- 实时行情/盘中信号、自动下单、多用户/鉴权/云部署
- 回测引擎与参数寻优（二期）、agent 编排（三期）
- 其他资产品类的通用化 UI

## Core User Flows

### Flow 1：每周信号决策

- Entry: 每周五净值披露后打开"每周信号页"，点"更新数据"
- Steps: 抓取净值落库 → quant-core 重算 → 写 weekly_signals 快照 → 展示评分/闸门/建议动作
- Success: 用户按建议（含 N0 无交易）在下一开放日 15:00 前在场外平台手动下单，并在交易日志录入
- Failure states: 抓取失败 → stale 横幅 + 手动录入兜底；数据不足（如广发 C <60 交易日）→ 自动用 025343 代理并标注

### Flow 2：交易记录与复盘

- Entry: 成交确认后打开"交易日志"
- Steps: 录入日期/基金/方向/金额/份额/确认净值/理由代码 → 系统算持有天数与费用估计
- Success: 日志可查可筛，月度复盘数据（次数/费用/纪律执行率）可统计
- Failure states: 理由代码缺失时提示补录；金额与份额×净值偏差 >1% 时警告

## Acceptance Criteria

- Every non-trivial task is represented in `TASKS.md`.
- Scope changes update this file before implementation.
- Implementation work follows `ARCHITECTURE.md` and is verified through `TESTING.md`.

## When To Update This File

Update this file when:

- A user-facing requirement changes.
- MVP scope, non-goals, target users, or acceptance criteria change.
- A task requires behavior not already covered by this spec.

Do not update this file for routine implementation details, refactors, or bug fixes that do not change product behavior.

## Change Log

| Date | Change | Reason | Impact |
|---|---|---|---|
| 2026-08-05 | Project control files initialized | Attach project to ObsidianToWiki AI workflow | Documentation/control-plane only |
| 2026-08-05 | 填充产品定义与一期范围（信号仪表盘+交易日志） | 一期设计文档获批：`docs/superpowers/specs/2026-08-05-signal-dashboard-design.md` | 确定 MVP 边界与两条核心流程 |
