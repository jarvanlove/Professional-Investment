# 设计文档：规则化投资信号仪表盘（一期）

- 日期：2026-08-05
- 状态：已获用户批准（2026-08-05）
- 上游依据：`docs/product/四只基金规则化交易与动态仓位管理方案_2026-08-05.pdf`（下称"方案 PDF"）
- 一期范围：信号仪表盘 + 交易日志
- 二期（不在本期）：回测、Ledoit-Wolf 协方差、参数调优
- 三期（不在本期）：agent 编排平台（LLM 调用 quant-core 工具层）

## 1. 目标与成功标准

把方案 PDF 中的规则化交易系统（趋势评分、分数凯利、波动率目标、回撤控制、费用约束）落地为本地可视化平台，替代手工 Excel 计算。

成功标准：

1. 每周五净值更新后，平台自动给出四只基金的评分、四道闸门结果、建议动作（含理由代码 B1-B4/S1-S4/P1-P2/N0），无需手工计算。
2. 方案 PDF 第 13 章三个算例（A/B/C）在 quant-core 黄金测试中金额完全一致。
3. 交易日志可录入、查询，录入时自动计算持有天数与赎回费估计。
4. akshare 抓取失败时可手动录入净值兜底，系统标记数据为 stale。
5. 一键本地启动（一个命令拉起 quant-api + web）。

## 2. 架构总览（方案 A：分层 Monorepo）

```
professional-investment/
├── packages/quant-core/      # 纯算法库：零 IO、纯函数、可单测，未来 agent 平台复用
├── services/quant-api/       # FastAPI：HTTP 层 + 数据管道(akshare) + SQLite 读写
└── apps/web/                 # Next.js (App Router)：UI + BFF Route Handlers 聚合 quant-api
```

```
┌─────────────────────────────────────────────────┐
│ apps/web (Next.js, App Router)                  │
│  仪表盘 / 每周信号 / 交易日志 / 持仓与资金        │
│  BFF Route Handlers → 转发并聚合 quant-api       │
└──────────────┬──────────────────────────────────┘
               │ HTTP (localhost:8000)
┌──────────────▼──────────────────────────────────┐
│ services/quant-api (FastAPI)                    │
│  /api/nav  /api/signals  /api/portfolio         │
│  /api/trades  /api/rebalance                    │
│  ├─ 数据管道：akshare 抓取 → 清洗 → 落库          │
│  ├─ 手动兜底：CSV 导入 / 单条净值修正接口          │
│  └─ SQLite (SQLAlchemy + Alembic)               │
└──────────────┬──────────────────────────────────┘
               │ import（纯函数调用，无框架依赖）
┌──────────────▼──────────────────────────────────┐
│ packages/quant-core (纯 Python 包)               │
│  indicators / scoring / sizing / rules / regime │
└─────────────────────────────────────────────────┘
```

关键边界：`quant-core` 不 import 任何 Web/DB 框架；输入输出为 `pandas.Series` 与 dataclass。这是三期 agent 平台直接复用的前提。

技术选型：

- 前端：Next.js（App Router）+ TypeScript + Tailwind CSS + shadcn/ui；图表用 Recharts
- 后端：FastAPI + SQLAlchemy 2.x + Alembic + SQLite（文件位于 `services/quant-api/data/investment.db`，不入库 Git）
- 算法库：Python 3.11+，pandas + numpy
- 数据源：akshare（天天基金/东方财富公开接口）
- Monorepo 工具：pnpm workspace（前端）+ uv/pip editable install（Python 包）

## 3. quant-core 模块设计

方案 PDF 每条规则映射为一个可单测的纯函数：

| 模块 | 函数（示例） | 对应 PDF 章节 |
|---|---|---|
| `indicators` | `ma(nav, window)`, `period_return(nav, n)`, `realized_vol(nav, 20)`, `drawdown_from_high(nav, 20)` | 04 量化框架 |
| `scoring` | `trend_score(nav) -> int 0..5`（5 个条件各 1 分） | 06 信号引擎 |
| `sizing` | `fractional_kelly(mu, cov, alpha=0.25)`, `vol_multiplier(vol, fund_type)`, `target_weights(scores, vols, dd, mode)` | 04 / 05 |
| `regime` | `market_regime(scores, portfolio_dd, peak_profit) -> Regime`（进攻/中性/保护/防守） | 05 四种市场状态 |
| `rules` | `evaluate_buy(...) -> B1..B4 | None`, `evaluate_sell(...) -> S1..S4 | P1..P2 | None` | 08 / 09 / 10 |
| `constraints` | `apply_caps(weights, mode)`（单只上限、科技合计 ≤60%、现金下限、无杠杆） | 05 / 08 |
| `fees` | `redemption_fee(fund, holding_days)`, `min_holding_ok(fund, trade_date)` | 03 赎回费约束 |

统一输出 `SignalReport` dataclass：

- 每只基金：净值、MA20/MA60、R20/R60、20 日波动率、评分、目标乘数、目标权重、目标金额、理论差额
- 四道闸门逐项结果：组合风险闸门 / 趋势闸门 / 追高闸门 / 费用闸门
- 建议动作：理由代码 + 金额上限（风险子单元约束，全账户每周 ≤2 单元）+ 解释文本
- 组合级：当前模式、组合回撤、峰值利润率、现金下限校验

所有规则参数（阈值、上限、单元金额）集中在 `quant-core/config.py` 的 dataclass，一期写死为 PDF 默认值；未来 agent 调参 = 改配置对象，可审计。

基金静态参数（初始值来自 PDF）：

- 财通成长优选混合A：核心主动仓，上限 30%，默认目标 25%，评分阈值 ≥3，A 类赎回费阶梯
- 长盛上证科创板芯片指数C：行业核心仓，上限 20%，默认目标 15%，评分阈值 ≥3，<7 日 1.5%
- 广发科创芯片设计ETF联接C：卫星仓，上限 10%，默认目标 10%，评分阈值 ≥4，历史不足 60 交易日时用 589210 ETF 净值做信号代理
- 摩根港股低波红利C：防御仓，上限 25%，默认目标 25%，评分阈值 ≥3，波动率目标 18%

## 4. 数据模型（SQLite，5 张表）

- `funds` — 基金主档：代码、名称、角色（core/satellite/defensive/cash）、硬上限、默认目标权重、费用规则 JSON、信号代理代码（广发→589210）
- `nav_history` — 日净值：fund_id, date, nav, source(auto/manual), created_at；唯一约束 (fund_id, date)
- `trades` — 交易日志：日期、fund_id、方向（buy/sell)、金额、份额、确认净值、理由代码、批次持有天数、费用估计、交易后权重、现金比例、备注（对应 PDF 15.2 模板）
- `weekly_signals` — 每周信号快照：日期、SignalReport 序列化 JSON；用于复盘"当时系统说了什么"
- `account_state` — 账户状态流水：日期、总资产、净投入本金、组合峰值、回撤、峰值利润率（算利润锁定与组合回撤用）

## 5. 前端页面（4 个）

1. **仪表盘** `/`：账户总资产、当前权重 vs 目标权重（偏离 >3pp 高亮）、组合回撤、当前市场模式徽章、现金比例
2. **每周信号页** `/signals`（核心）：四只基金评分、四道闸门逐项 ✅/❌、建议动作卡片（如"摩根：B4 再平衡买入 ≤1,067 元"）、防追高提示、"本周 N0 无交易"也是合法输出
3. **交易日志** `/trades`：录入 / 列表 / 按理由代码筛选；录入时自动带出持有天数与赎回费估计
4. **持仓与资金** `/portfolio`：各批次份额、费用窗口倒计时、现金比例、追加资金计划进度（4 个风险单元已用几个）

## 6. 数据流与错误处理

- 每周流程：点"更新数据"（或本地计划任务）→ akshare 拉净值 → 落库 → 重算信号 → 写 `weekly_signals` 快照 → 前端展示
- 抓取失败：保留上次数据并标记 stale，前端横幅提示；提供 CSV 导入与单条净值修正接口
- 广发 C 历史 <60 交易日：自动切换 589210 ETF 净值做 MA/波动率/评分代理，前端标注"信号来自代理 ETF"
- akshare 接口变动：解析集中在数据管道层 `fetcher.py` 单点修改
- 未知价原则：系统所有信号基于已确认净值，UI 明确提示"成交净值以确认日为准，阈值非精确价格止损"
- quant-api 对 quant-core 的计算异常返回 422 + 结构化错误，BFF 透传，前端显示"数据不足/计算失败"而非崩溃

## 7. 测试策略

- **黄金测试（核心）**：PDF 第 13 章算例 A/B/C 转为 pytest 参数化用例，输出金额必须与 PDF 表格一致（算例 A：财通 ≤663 元、长盛 ≤477 元、广发不动、摩根 ≤1,068 元、合计约 2,208 元）
- quant-core：每个规则函数的单元测试（评分边界、闸门组合、回撤档位切换、费用窗口）
- quant-api：FastAPI TestClient + 内存 SQLite 的接口测试
- web：关键 BFF 转发的集成测试 + 页面渲染冒烟测试（Playwright 或 React Testing Library，一期从简）
- 验证命令：`pnpm test`（web）+ `pytest`（quant-core + quant-api），写入 `TESTING.md`

## 8. 面向 agent 平台的演化预留

- quant-core 每个公开函数即未来 agent 的 tool；三期 = LLM 编排层调用 tool + 读 `weekly_signals` 生成解释
- 规则参数集中 config dataclass，agent 调参可审计、可回滚
- 二期/三期只做加法：不改一期表结构与 API 契约

## 9. 非目标（本期明确不做）

- 实时行情、盘中信号（违反方案 PDF 的未知价原则）
- 自动下单 / 对接销售平台 API
- 多用户、鉴权、云端部署
- 回测引擎、参数寻优（二期）
- 其他基金/资产品类的扩展（配置结构预留，UI 不做通用化）
