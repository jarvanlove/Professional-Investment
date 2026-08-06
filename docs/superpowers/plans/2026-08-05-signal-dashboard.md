# 一期信号仪表盘 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把《四只基金规则化交易与动态仓位管理方案》落地为本地可视化平台：每周信号计算（评分/闸门/建议动作）+ 交易日志，纯本地单机运行。

**Architecture:** 分层 Monorepo。`packages/quant-core` 为纯算法库（零 IO、纯函数）；`services/quant-api` 为 FastAPI 数据管道与 HTTP 层；`apps/web` 为 Next.js (App Router) UI + BFF 代理。详细设计见 `docs/superpowers/specs/2026-08-05-signal-dashboard-design.md`。

**Tech Stack:** Python 3.11+ / uv / FastAPI / SQLAlchemy 2.x / SQLite / akshare / pandas；Node 20+ / pnpm 9+ / Next.js 15 / TypeScript / Tailwind / shadcn/ui / Recharts / Vitest。

## Global Constraints

- Python 版本 ≥3.11；Node ≥20；包管理：Python 用 `uv`，前端用 `pnpm`。
- `quant-core` 禁止 import 任何 Web/DB/网络框架（无 fastapi/sqlalchemy/requests）；输入输出为 `pandas.Series` 与 dataclass。
- 规则参数唯一来源：`packages/quant-core/quant_core/config.py`。前端和 API 层不得复制任何阈值。
- 理由代码固定集合：`B1 B2 B3 B4 S1 S2 S3 S4 P1 P2 N0`。
- 基金代码：财通成长A=`001480`，长盛芯片C=`025343`，广发芯片设计C=`027521`（信号代理 ETF=`589210`），摩根红利C=`005052`。
- SQLite 文件路径：`services/quant-api/data/investment.db`，必须被 `.gitignore` 排除。
- 端口：quant-api=8000，web=3000。
- 与 spec 的两处有意偏差（已向用户披露）：(1) 一期不引入 Alembic，用 `Base.metadata.create_all`，首次需要改表结构时再补 Alembic；(2) 交易表 `trades` 同时承担出入金账本（direction 含 `deposit`/`withdraw`），现金与净投入由账本推导，不另建表。
- 所有信号基于已确认净值；UI 不得出现"盘中""实时"字样。

## File Structure

```
packages/quant-core/
├── pyproject.toml
├── quant_core/
│   ├── __init__.py            # 公开 API re-export
│   ├── config.py              # 全部规则参数（唯一来源）
│   ├── indicators.py          # MA/收益/波动率/回撤
│   ├── scoring.py             # 0-5 趋势评分
│   ├── sizing.py              # 波动率乘数、目标权重
│   ├── constraints.py         # 约束投影（单只/科技桶/现金）
│   ├── regime.py              # 市场模式判定
│   ├── fees.py                # 赎回费阶梯
│   ├── rules.py               # 闸门 + B/S 信号识别
│   └── engine.py              # SignalReport 组装
└── tests/
    ├── test_config.py  test_indicators.py  test_scoring.py
    ├── test_sizing.py  test_regime.py  test_fees.py
    ├── test_rules.py   test_engine.py
    └── test_golden_examples.py   # PDF 第13章算例 A/B/C

services/quant-api/
├── pyproject.toml
├── app/
│   ├── main.py                # FastAPI 入口 + CORS
│   ├── db.py                  # engine/session/create_all
│   ├── models.py              # Fund/NavHistory/Trade/WeeklySignal
│   ├── schemas.py             # Pydantic 请求/响应
│   ├── fetcher.py             # akshare 抓取（唯一天天基金依赖点）
│   ├── ledger.py              # 账本推导：现金/份额/持仓/净投入
│   └── routers/
│       ├── funds.py  nav.py  trades.py  signals.py  portfolio.py
└── tests/
    ├── test_trades_api.py  test_nav_api.py  test_signals_api.py

apps/web/
├── app/
│   ├── layout.tsx  page.tsx            # 仪表盘
│   ├── signals/page.tsx                # 每周信号
│   ├── trades/page.tsx                 # 交易日志
│   ├── portfolio/page.tsx              # 持仓与资金
│   └── api/[...path]/route.ts          # BFF 代理到 quant-api
├── lib/api.ts                          # 类型化 fetch 客户端
├── lib/types.ts                        # 与 SignalReport 对齐的 TS 类型
├── components/                         # StatCard, WeightBar, DecisionCard, GateList...
└── __tests__/dashboard.test.tsx        # 渲染冒烟（mock fetch）
```

---

### Task 1: Monorepo 脚手架 + quant-core 包骨架

**Files:**
- Create: `package.json`（根）
- Create: `.gitignore`
- Create: `packages/quant-core/pyproject.toml`
- Create: `packages/quant-core/quant_core/__init__.py`
- Test: `packages/quant-core/tests/test_smoke.py`

**Interfaces:**
- Produces: 可 `uv run --directory packages/quant-core pytest` 的包骨架；根 `pnpm dev`/`pnpm test` 脚本（后续任务填充目标）。

- [ ] **Step 1: 写根 package.json 与 .gitignore**

```json
// package.json
{
  "name": "professional-investment",
  "private": true,
  "scripts": {
    "dev": "concurrently -k -n api,web \"uv run --directory services/quant-api uvicorn app.main:app --reload --port 8000\" \"pnpm --dir apps/web dev\"",
    "dev:api": "uv run --directory services/quant-api uvicorn app.main:app --reload --port 8000",
    "dev:web": "pnpm --dir apps/web dev",
    "test": "uv run --directory packages/quant-core pytest && uv run --directory services/quant-api pytest && pnpm --dir apps/web test"
  },
  "devDependencies": {
    "concurrently": "^9.1.0"
  }
}
```

```gitignore
# .gitignore
node_modules/
.next/
__pycache__/
.pytest_cache/
.venv/
*.egg-info/
services/quant-api/data/
wiki.context.json
.obsidiantowiki/
```

- [ ] **Step 2: 写 quant-core pyproject.toml 与包骨架**

```toml
# packages/quant-core/pyproject.toml
[project]
name = "quant-core"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = ["pandas>=2.2", "numpy>=1.26"]

[dependency-groups]
dev = ["pytest>=8.0"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["quant_core"]
```

```python
# packages/quant-core/quant_core/__init__.py
"""纯算法库：方案 PDF 规则的代码化。禁止 import Web/DB/网络框架。"""
```

```python
# packages/quant-core/tests/test_smoke.py
import quant_core


def test_package_importable():
    assert quant_core.__doc__
```

- [ ] **Step 3: 安装并跑通**

Run: `uv run --directory packages/quant-core pytest -v`
Expected: 1 passed（uv 自动建 venv 并安装 pandas/numpy/pytest）

- [ ] **Step 4: 安装根依赖**

Run: `pnpm install`
Expected: concurrently 安装成功

- [ ] **Step 5: Commit**

```bash
git add package.json pnpm-lock.yaml .gitignore packages/quant-core
git commit -m "chore: monorepo 脚手架 + quant-core 包骨架"
```

---

### Task 2: quant-core 规则参数 config.py

**Files:**
- Create: `packages/quant-core/quant_core/config.py`
- Test: `packages/quant-core/tests/test_config.py`

**Interfaces:**
- Produces: `FundConfig`, `FeeTier`, `FUNDS`, `TECH_CODES`, `REGIME_WEIGHTS`, `REGIME_CASH_MIN`, `SCORE_MULTIPLIERS`, `UNIT_LIMITS`，常量 `TECH_TOTAL_CAP / DD_WARN(0.06) / DD_REDUCE(0.08) / DD_DEFENSIVE(0.12) / DD_HARD(0.15) / PROFIT_PROTECT_TRIGGER(0.08) / PROFIT_PULLBACK_TRIGGER(0.04) / PROFIT_LOCK_12(0.12) / PROFIT_LOCK_20(0.20) / DEADBAND_AMOUNT(300.0) / DEADBAND_WEIGHT(0.03) / MAX_UNITS_PER_WEEK(2)`。

- [ ] **Step 1: 写失败测试**

```python
# tests/test_config.py
from quant_core.config import (
    FUNDS, TECH_CODES, REGIME_WEIGHTS, REGIME_CASH_MIN,
    SCORE_MULTIPLIERS, UNIT_LIMITS, TECH_TOTAL_CAP,
)


def test_four_funds_present():
    assert set(FUNDS) == {"001480", "025343", "027521", "005052"}


def test_tech_bucket_membership():
    assert set(TECH_CODES) == {"001480", "025343", "027521"}
    assert FUNDS["005052"].bucket == "dividend"


def test_neutral_weights_sum_tech_50_dividend_25():
    w = REGIME_WEIGHTS["neutral"]
    assert sum(w[c] for c in TECH_CODES) == 0.50
    assert w["005052"] == 0.25


def test_caps_match_pdf():
    assert FUNDS["001480"].cap == 0.30
    assert FUNDS["025343"].cap == 0.20
    assert FUNDS["027521"].cap == 0.10
    assert FUNDS["005052"].cap == 0.25
    assert TECH_TOTAL_CAP == 0.60


def test_score_multipliers():
    assert SCORE_MULTIPLIERS == {5: 1.0, 4: 0.75, 3: 0.5, 2: 0.25, 1: 0.0, 0: 0.0}


def test_unit_limits_15k_sum():
    assert sum(UNIT_LIMITS["15k"].values) == 663 + 477 + 352 + 1067


def test_proxy_only_for_guangfa():
    assert FUNDS["027521"].proxy_code == "589210"
    assert all(f.proxy_code is None for c, f in FUNDS.items() if c != "027521")


def test_cash_min_by_regime():
    assert REGIME_CASH_MIN == {
        "offensive": 0.15, "neutral": 0.25, "protect": 0.40, "defensive": 0.60,
    }
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run --directory packages/quant-core pytest tests/test_config.py -v`
Expected: FAIL `ModuleNotFoundError: quant_core.config`

- [ ] **Step 3: 写实现**

```python
# quant_core/config.py
"""方案 PDF（2026-08-05）全部规则参数。唯一参数来源，禁止散落到其他模块。"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FeeTier:
    max_days: int | None  # None = 及以上
    rate: float


@dataclass(frozen=True)
class FundConfig:
    code: str
    name: str
    bucket: str  # 'tech' | 'dividend'
    role: str    # 'core_active' | 'core_index' | 'satellite' | 'defensive'
    cap: float
    min_score_to_buy: int
    core_weight: float          # S2 硬风控核心仓权重（财通10/长盛5/广发0/摩根10）
    vol_bands: tuple[tuple[float, float], ...]  # (年化波动上界, 乘数) 升序
    fee_tiers: tuple[FeeTier, ...]
    proxy_code: str | None = None


_TECH_VOL_BANDS = ((0.30, 1.00), (0.45, 0.75), (0.60, 0.50), (float("inf"), 0.25))

FUNDS: dict[str, FundConfig] = {
    "001480": FundConfig(
        code="001480", name="财通成长优选混合A", bucket="tech", role="core_active",
        cap=0.30, min_score_to_buy=3, core_weight=0.10, vol_bands=_TECH_VOL_BANDS,
        fee_tiers=(FeeTier(7, 0.015), FeeTier(30, 0.0075), FeeTier(365, 0.005),
                   FeeTier(730, 0.0025), FeeTier(None, 0.0)),
    ),
    "025343": FundConfig(
        code="025343", name="长盛上证科创板芯片指数C", bucket="tech", role="core_index",
        cap=0.20, min_score_to_buy=3, core_weight=0.05, vol_bands=_TECH_VOL_BANDS,
        fee_tiers=(FeeTier(7, 0.015), FeeTier(None, 0.0)),
    ),
    "027521": FundConfig(
        code="027521", name="广发科创芯片设计ETF联接C", bucket="tech", role="satellite",
        cap=0.10, min_score_to_buy=4, core_weight=0.0, vol_bands=_TECH_VOL_BANDS,
        fee_tiers=(FeeTier(7, 0.015), FeeTier(None, 0.0)),
        proxy_code="589210",
    ),
    "005052": FundConfig(
        code="005052", name="摩根标普港股通低波红利指数C", bucket="dividend", role="defensive",
        cap=0.25, min_score_to_buy=3, core_weight=0.10,
        vol_bands=((0.15, 1.00), (0.22, 0.75), (0.30, 0.50), (float("inf"), 0.25)),
        fee_tiers=(FeeTier(7, 0.015), FeeTier(30, 0.005), FeeTier(None, 0.0)),
    ),
}

TECH_CODES: tuple[str, ...] = tuple(c for c, f in FUNDS.items() if f.bucket == "tech")

# 四种市场模式下各基金基准权重（PDF 05 章；protect/defensive 科技桶按 3:2:1 拆分）
REGIME_WEIGHTS: dict[str, dict[str, float]] = {
    "offensive": {"001480": 0.30, "025343": 0.20, "027521": 0.10, "005052": 0.25},
    "neutral":   {"001480": 0.25, "025343": 0.15, "027521": 0.10, "005052": 0.25},
    "protect":   {"001480": 0.175, "025343": 0.117, "027521": 0.058, "005052": 0.25},
    "defensive": {"001480": 0.075, "025343": 0.05, "027521": 0.025, "005052": 0.25},
}

REGIME_CASH_MIN = {"offensive": 0.15, "neutral": 0.25, "protect": 0.40, "defensive": 0.60}

TECH_TOTAL_CAP = 0.60
SCORE_MULTIPLIERS = {5: 1.0, 4: 0.75, 3: 0.5, 2: 0.25, 1: 0.0, 0: 0.0}

# 组合回撤档位（PDF 9.4）
DD_WARN = 0.06
DD_REDUCE = 0.08
DD_DEFENSIVE = 0.12
DD_HARD = 0.15

# 利润锁定档位（PDF 10.2）
PROFIT_PROTECT_TRIGGER = 0.08
PROFIT_PULLBACK_TRIGGER = 0.04
PROFIT_LOCK_12 = 0.12
PROFIT_LOCK_20 = 0.20

DEADBAND_AMOUNT = 300.0
DEADBAND_WEIGHT = 0.03
MAX_UNITS_PER_WEEK = 2

# 每个风险子单元的单基金金额上限（PDF 07 章）
UNIT_LIMITS = {
    "15k": {"001480": 663.0, "025343": 477.0, "027521": 352.0, "005052": 1067.0},
    "20k": {"001480": 976.0, "025343": 664.0, "027521": 477.0, "005052": 1380.0},
}
```

- [ ] **Step 4: 跑测试确认通过**

Run: `uv run --directory packages/quant-core pytest tests/test_config.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add packages/quant-core
git commit -m "feat(quant-core): 规则参数 config（基金/模式/费用/单元上限）"
```

---

### Task 3: indicators.py 指标计算

**Files:**
- Create: `packages/quant-core/quant_core/indicators.py`
- Test: `packages/quant-core/tests/test_indicators.py`

**Interfaces:**
- Produces: `ma(nav: pd.Series, window: int) -> float`；`period_return(nav, n) -> float`；`realized_vol(nav, window=20) -> float`（年化）；`drawdown_from_high(nav, window=20) -> float`（正值=低于高点的比例）；`last_daily_return(nav) -> float`。序列不足时抛 `ValueError`。

- [ ] **Step 1: 写失败测试**

```python
# tests/test_indicators.py
import numpy as np
import pandas as pd
import pytest

from quant_core.indicators import (
    ma, period_return, realized_vol, drawdown_from_high, last_daily_return,
)


def make_nav(values):
    idx = pd.date_range("2026-01-01", periods=len(values), freq="B")
    return pd.Series(values, index=idx, dtype=float)


def test_ma_basic():
    nav = make_nav(range(1, 31))
    assert ma(nav, 20) == pytest.approx(np.mean(range(11, 31)))


def test_ma_insufficient_raises():
    with pytest.raises(ValueError):
        ma(make_nav([1.0] * 10), 20)


def test_period_return():
    nav = make_nav([100.0] * 60 + [110.0])
    assert period_return(nav, 20) == pytest.approx(0.10)


def test_realized_vol_annualized():
    nav = make_nav((100 * 1.001 ** np.arange(60)).tolist())
    rets = nav.pct_change().dropna().iloc[-20:]
    assert realized_vol(nav, 20) == pytest.approx(rets.std(ddof=1) * np.sqrt(252))


def test_drawdown_from_high_positive_when_below():
    nav = make_nav([100.0] * 15 + [120.0, 110.0, 108.0, 105.0, 90.0])
    # 20日高点=120，最新=90 → 低于高点 25%
    assert drawdown_from_high(nav, 20) == pytest.approx(0.25)


def test_last_daily_return():
    nav = make_nav([100.0, 105.0])
    assert last_daily_return(nav) == pytest.approx(0.05)
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run --directory packages/quant-core pytest tests/test_indicators.py -v`
Expected: FAIL `ModuleNotFoundError`

- [ ] **Step 3: 写实现**

```python
# quant_core/indicators.py
"""指标计算。约定：nav 为按日期升序的日净值 Series；回撤用正值表示低于高点的比例。"""
from __future__ import annotations

import numpy as np
import pandas as pd


def ma(nav: pd.Series, window: int) -> float:
    if len(nav) < window:
        raise ValueError(f"need >= {window} points, got {len(nav)}")
    return float(nav.iloc[-window:].mean())


def period_return(nav: pd.Series, n: int) -> float:
    if len(nav) < n + 1:
        raise ValueError(f"need >= {n + 1} points, got {len(nav)}")
    return float(nav.iloc[-1] / nav.iloc[-1 - n] - 1)


def realized_vol(nav: pd.Series, window: int = 20, trading_days: int = 252) -> float:
    rets = nav.pct_change().dropna().iloc[-window:]
    if len(rets) < window:
        raise ValueError(f"need >= {window} returns, got {len(rets)}")
    return float(rets.std(ddof=1) * np.sqrt(trading_days))


def drawdown_from_high(nav: pd.Series, window: int = 20) -> float:
    """最新净值低于 window 内最高净值的比例（>=0）。"""
    if len(nav) < 1:
        raise ValueError("empty nav series")
    high = float(nav.iloc[-window:].max())
    return float(1 - nav.iloc[-1] / high)


def last_daily_return(nav: pd.Series) -> float:
    if len(nav) < 2:
        raise ValueError("need >= 2 points")
    return float(nav.iloc[-1] / nav.iloc[-2] - 1)
```

- [ ] **Step 4: 跑测试确认通过**

Run: `uv run --directory packages/quant-core pytest tests/test_indicators.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add packages/quant-core
git commit -m "feat(quant-core): 指标计算（MA/收益/波动率/回撤）"
```

---

### Task 4: scoring.py 趋势评分

**Files:**
- Create: `packages/quant-core/quant_core/scoring.py`
- Test: `packages/quant-core/tests/test_scoring.py`

**Interfaces:**
- Consumes: `indicators.ma`, `indicators.period_return`，`config.SCORE_MULTIPLIERS`
- Produces: `trend_score(nav: pd.Series) -> int`（0-5）；`score_multiplier(score: int) -> float`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_scoring.py
import numpy as np
import pandas as pd
import pytest

from quant_core.scoring import trend_score, score_multiplier


def uptrend(days=80, daily=1.002):
    vals = 100 * daily ** np.arange(days)
    idx = pd.date_range("2026-01-01", periods=days, freq="B")
    return pd.Series(vals, index=idx)


def test_perfect_uptrend_scores_5():
    # 温和上升：nav>MA20, MA20>MA60, R20>0, R60>0, 偏离在 [-3%,+8%] 内
    assert trend_score(uptrend()) == 5


def test_spike_above_8pct_loses_position_point():
    nav = uptrend()
    nav.iloc[-1] = nav.iloc[-2] * 1.10  # 单日+10%，偏离 MA20 必然 >8%
    assert trend_score(nav) == 4


def test_downtrend_scores_low():
    vals = 100 * 0.998 ** np.arange(80)
    idx = pd.date_range("2026-01-01", periods=80, freq="B")
    nav = pd.Series(vals, index=idx)
    assert trend_score(nav) <= 1


def test_score_multiplier_mapping():
    assert score_multiplier(5) == 1.0
    assert score_multiplier(4) == 0.75
    assert score_multiplier(2) == 0.25
    assert score_multiplier(0) == 0.0
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run --directory packages/quant-core pytest tests/test_scoring.py -v`
Expected: FAIL `ModuleNotFoundError`

- [ ] **Step 3: 写实现**

```python
# quant_core/scoring.py
"""0-5 趋势评分（PDF 06 章）。"""
from __future__ import annotations

import pandas as pd

from .config import SCORE_MULTIPLIERS
from .indicators import ma, period_return


def trend_score(nav: pd.Series) -> int:
    last = float(nav.iloc[-1])
    ma20 = ma(nav, 20)
    ma60 = ma(nav, 60)
    dev = last / ma20 - 1
    score = 0
    score += last > ma20                    # 短期趋势为正
    score += ma20 > ma60                    # 中期趋势为正
    score += period_return(nav, 20) > 0     # 月度动量为正
    score += period_return(nav, 60) > 0     # 季度动量为正
    score += -0.03 <= dev <= 0.08           # 无破位、无严重追高
    return int(score)


def score_multiplier(score: int) -> float:
    return SCORE_MULTIPLIERS[score]
```

- [ ] **Step 4: 跑测试确认通过**

Run: `uv run --directory packages/quant-core pytest tests/test_scoring.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add packages/quant-core
git commit -m "feat(quant-core): 0-5 趋势评分"
```

---

### Task 5: sizing.py + constraints.py 目标权重与约束投影

**Files:**
- Create: `packages/quant-core/quant_core/sizing.py`
- Create: `packages/quant-core/quant_core/constraints.py`
- Test: `packages/quant-core/tests/test_sizing.py`

**Interfaces:**
- Consumes: `config.FUNDS / REGIME_WEIGHTS / TECH_CODES / TECH_TOTAL_CAP`，`scoring.score_multiplier`
- Produces: `vol_multiplier(vol: float, bands) -> float`；`base_weight(regime: str, code: str) -> float`；`target_weight(regime, code, score, vol) -> float`（含单只 cap）；`apply_caps(weights: dict[str, float], regime: str) -> dict[str, float]`（科技桶等比压缩）

- [ ] **Step 1: 写失败测试**

```python
# tests/test_sizing.py
import pytest

from quant_core.config import FUNDS, TECH_CODES
from quant_core.sizing import vol_multiplier, base_weight, target_weight
from quant_core.constraints import apply_caps


def test_vol_multiplier_tech_bands():
    bands = FUNDS["001480"].vol_bands
    assert vol_multiplier(0.25, bands) == 1.0
    assert vol_multiplier(0.35, bands) == 0.75
    assert vol_multiplier(0.50, bands) == 0.50
    assert vol_multiplier(0.70, bands) == 0.25


def test_vol_multiplier_dividend_bands():
    bands = FUNDS["005052"].vol_bands
    assert vol_multiplier(0.10, bands) == 1.0
    assert vol_multiplier(0.20, bands) == 0.75
    assert vol_multiplier(0.25, bands) == 0.50
    assert vol_multiplier(0.35, bands) == 0.25


def test_target_weight_example_a():
    # PDF 算例A：中性，财通4分 → 25%×75%×1.0 = 18.75%
    assert target_weight("neutral", "001480", score=4, vol=0.20) == pytest.approx(0.1875)
    assert target_weight("neutral", "025343", score=3, vol=0.20) == pytest.approx(0.075)
    assert target_weight("neutral", "027521", score=2, vol=0.20) == pytest.approx(0.025)
    assert target_weight("neutral", "005052", score=4, vol=0.10) == pytest.approx(0.1875)


def test_target_weight_never_exceeds_cap():
    assert target_weight("offensive", "001480", score=5, vol=0.20) <= 0.30


def test_apply_caps_scales_tech_bucket():
    weights = {"001480": 0.30, "025343": 0.20, "027521": 0.10, "005052": 0.25}
    out = apply_caps(weights, "offensive")
    assert out == weights
    over = {"001480": 0.35, "025343": 0.25, "027521": 0.10, "005052": 0.20}
    out = apply_caps(over, "offensive")
    assert out["001480"] <= 0.30
    assert sum(out[c] for c in TECH_CODES) <= 0.60 + 1e-9
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run --directory packages/quant-core pytest tests/test_sizing.py -v`
Expected: FAIL `ModuleNotFoundError`

- [ ] **Step 3: 写实现**

```python
# quant_core/sizing.py
"""目标权重：基准权重 × 评分乘数 × 波动率乘数，再受单只 cap 约束（PDF 4.4）。"""
from __future__ import annotations

from .config import FUNDS, REGIME_WEIGHTS
from .scoring import score_multiplier


def vol_multiplier(vol: float, bands: tuple[tuple[float, float], ...]) -> float:
    for upper, mult in bands:
        if vol < upper:
            return mult
    return bands[-1][1]


def base_weight(regime: str, code: str) -> float:
    return REGIME_WEIGHTS[regime][code]


def target_weight(regime: str, code: str, score: int, vol: float) -> float:
    fund = FUNDS[code]
    w = base_weight(regime, code) * score_multiplier(score) * vol_multiplier(vol, fund.vol_bands)
    return min(w, fund.cap)
```

```python
# quant_core/constraints.py
"""约束投影 Π_C：单只上限、科技合计上限（PDF 4.4 / 05 章相关性闸门）。"""
from __future__ import annotations

from .config import FUNDS, TECH_CODES, TECH_TOTAL_CAP, REGIME_WEIGHTS


def apply_caps(weights: dict[str, float], regime: str) -> dict[str, float]:
    out = {c: min(w, FUNDS[c].cap) for c, w in weights.items()}
    tech_total = sum(out[c] for c in TECH_CODES)
    regime_tech = sum(REGIME_WEIGHTS[regime][c] for c in TECH_CODES)
    cap = min(TECH_TOTAL_CAP, regime_tech)
    if tech_total > cap > 0:
        scale = cap / tech_total
        for c in TECH_CODES:
            out[c] *= scale
    return out
```

- [ ] **Step 4: 跑测试确认通过**

Run: `uv run --directory packages/quant-core pytest tests/test_sizing.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add packages/quant-core
git commit -m "feat(quant-core): 目标权重与约束投影"
```

---

### Task 6: regime.py 市场模式判定

**Files:**
- Create: `packages/quant-core/quant_core/regime.py`
- Test: `packages/quant-core/tests/test_regime.py`

**Interfaces:**
- Consumes: `config.DD_* / PROFIT_*` 常量
- Produces: `market_regime(tech_scores: dict[str, int], portfolio_dd: float, peak_profit_rate: float) -> str`，返回 `"offensive" | "neutral" | "protect" | "defensive"`；优先级 defensive > protect > offensive > neutral

- [ ] **Step 1: 写失败测试**

```python
# tests/test_regime.py
from quant_core.regime import market_regime


def test_defensive_on_big_drawdown():
    assert market_regime({"a": 5, "b": 5, "c": 5}, portfolio_dd=0.13, peak_profit_rate=0.0) == "defensive"


def test_defensive_on_two_weak_tech():
    assert market_regime({"a": 2, "b": 1, "c": 5}, portfolio_dd=0.02, peak_profit_rate=0.0) == "defensive"


def test_protect_on_profit_pullback():
    assert market_regime({"a": 4, "b": 4, "c": 3}, portfolio_dd=0.05, peak_profit_rate=0.09) == "protect"


def test_offensive_when_strong():
    assert market_regime({"a": 4, "b": 5, "c": 3}, portfolio_dd=0.02, peak_profit_rate=0.0) == "offensive"


def test_neutral_default():
    assert market_regime({"a": 3, "b": 4, "c": 2}, portfolio_dd=0.02, peak_profit_rate=0.0) == "neutral"


def test_defensive_beats_offensive():
    assert market_regime({"a": 5, "b": 5, "c": 5}, portfolio_dd=0.13, peak_profit_rate=0.0) == "defensive"
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run --directory packages/quant-core pytest tests/test_regime.py -v`
Expected: FAIL `ModuleNotFoundError`

- [ ] **Step 3: 写实现**

```python
# quant_core/regime.py
"""市场模式判定（PDF 05 章）。优先级：defensive > protect > offensive > neutral。"""
from __future__ import annotations

from .config import (
    DD_DEFENSIVE, DD_WARN, PROFIT_PROTECT_TRIGGER, PROFIT_PULLBACK_TRIGGER,
)


def market_regime(
    tech_scores: dict[str, int],
    portfolio_dd: float,
    peak_profit_rate: float,
) -> str:
    if portfolio_dd >= DD_DEFENSIVE or sum(s <= 2 for s in tech_scores.values()) >= 2:
        return "defensive"
    if peak_profit_rate >= PROFIT_PROTECT_TRIGGER and portfolio_dd >= PROFIT_PULLBACK_TRIGGER:
        return "protect"
    if portfolio_dd < DD_WARN and sum(s >= 4 for s in tech_scores.values()) >= 2:
        return "offensive"
    return "neutral"
```

- [ ] **Step 4: 跑测试确认通过**

Run: `uv run --directory packages/quant-core pytest tests/test_regime.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add packages/quant-core
git commit -m "feat(quant-core): 市场模式判定"
```

---

### Task 7: fees.py 赎回费阶梯

**Files:**
- Create: `packages/quant-core/quant_core/fees.py`
- Test: `packages/quant-core/tests/test_fees.py`

**Interfaces:**
- Consumes: `config.FUNDS`, `config.FeeTier`
- Produces: `redemption_fee_rate(code: str, holding_days: int) -> float`；`holding_days(buy_date: date, as_of: date) -> int`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_fees.py
from datetime import date

from quant_core.fees import redemption_fee_rate, holding_days


def test_caitong_fee_ladder():
    assert redemption_fee_rate("001480", 3) == 0.015
    assert redemption_fee_rate("001480", 10) == 0.0075
    assert redemption_fee_rate("001480", 100) == 0.005
    assert redemption_fee_rate("001480", 400) == 0.0025
    assert redemption_fee_rate("001480", 800) == 0.0


def test_c_share_fee_free_after_7_days():
    assert redemption_fee_rate("025343", 5) == 0.015
    assert redemption_fee_rate("025343", 7) == 0.0
    assert redemption_fee_rate("027521", 6) == 0.015
    assert redemption_fee_rate("027521", 8) == 0.0


def test_morgan_fee_ladder():
    assert redemption_fee_rate("005052", 3) == 0.015
    assert redemption_fee_rate("005052", 15) == 0.005
    assert redemption_fee_rate("005052", 30) == 0.0


def test_holding_days():
    assert holding_days(date(2026, 7, 1), date(2026, 8, 5)) == 35
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run --directory packages/quant-core pytest tests/test_fees.py -v`
Expected: FAIL `ModuleNotFoundError`

- [ ] **Step 3: 写实现**

```python
# quant_core/fees.py
"""赎回费阶梯（PDF 03 章）。执行前仍须以销售平台实际持有天数为准。"""
from __future__ import annotations

from datetime import date

from .config import FUNDS


def redemption_fee_rate(code: str, days: int) -> float:
    for tier in FUNDS[code].fee_tiers:
        if tier.max_days is None or days < tier.max_days:
            return tier.rate
    return 0.0


def holding_days(buy_date: date, as_of: date) -> int:
    return (as_of - buy_date).days
```

- [ ] **Step 4: 跑测试确认通过**

Run: `uv run --directory packages/quant-core pytest tests/test_fees.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add packages/quant-core
git commit -m "feat(quant-core): 赎回费阶梯"
```

---

### Task 8: rules.py 闸门与买卖信号识别

**Files:**
- Create: `packages/quant-core/quant_core/rules.py`
- Test: `packages/quant-core/tests/test_rules.py`

**Interfaces:**
- Consumes: `config`, `indicators`
- Produces:
  - `gate_portfolio_ok(portfolio_dd: float, bucket: str) -> bool` — dd≥6% 禁止新增科技
  - `gate_score_ok(code: str, score: int) -> bool`
  - `gate_position_ok(code: str, nav: pd.Series) -> bool` — 科技偏离 MA20 ≤+8% 且单日涨幅 ≤5%
  - `detect_buy_signal(code, nav, score, prev_score: int | None) -> str | None` — 返回 `B1|B2|B3|None`（B4 由 engine 按权重差判定）；优先级 B2 > B1 > B3
  - `detect_sell_signal(code, nav, score, prev_score) -> tuple[str, float | str] | None` — 返回 `(理由, 卖出比例)` 或 `(理由, "to_core")`；多触发取卖出最多者

- [ ] **Step 1: 写失败测试**

```python
# tests/test_rules.py
import numpy as np
import pandas as pd

from quant_core.rules import (
    gate_portfolio_ok, gate_score_ok, gate_position_ok,
    detect_buy_signal, detect_sell_signal,
)


def series(vals):
    idx = pd.date_range("2026-01-01", periods=len(vals), freq="B")
    return pd.Series(vals, index=idx, dtype=float)


def uptrend(days=80, daily=1.002):
    return series((100 * daily ** np.arange(days)).tolist())


# --- 闸门 ---

def test_portfolio_gate_blocks_tech_at_6pct():
    assert gate_portfolio_ok(0.05, "tech") is True
    assert gate_portfolio_ok(0.07, "tech") is False
    assert gate_portfolio_ok(0.07, "dividend") is True   # 6-8% 仍可补摩根
    assert gate_portfolio_ok(0.10, "tech") is False


def test_score_gate_thresholds():
    assert gate_score_ok("001480", 3) is True
    assert gate_score_ok("001480", 2) is False
    assert gate_score_ok("027521", 3) is False  # 广发要求 ≥4
    assert gate_score_ok("027521", 4) is True


def test_position_gate_chase_rules():
    nav = uptrend()
    assert gate_position_ok("001480", nav) is True
    spiked = nav.copy()
    spiked.iloc[-1] = spiked.iloc[-2] * 1.06   # 单日 +6% > 5%
    assert gate_position_ok("001480", spiked) is False
    far = nav.copy()
    far.iloc[-1] = far.iloc[-1] * 1.09          # 偏离 MA20 >8%
    assert gate_position_ok("001480", far) is False
    assert gate_position_ok("005052", far) is True  # 位置闸门只管科技


# --- 买入信号 ---

def test_b1_trend_entry():
    nav = uptrend()
    assert detect_buy_signal("001480", nav, score=4, prev_score=4) == "B1"
    assert detect_buy_signal("001480", nav, score=4, prev_score=2) is None


def test_b2_pullback():
    vals = (100 * 1.002 ** np.arange(75)).tolist()
    peak = vals[-1] * 1.01
    vals += [peak, peak * 0.97, peak * 0.955, peak * 0.945, peak * 0.955]
    nav = series(vals)  # 高点回撤后单日转正，MA20>MA60 且 nav>MA60
    sig = detect_buy_signal("001480", nav, score=4, prev_score=4)
    # B2（回撤 4%-8% 且当日转正）或 B1（连续高分）均为合法；实现按 B2 优先
    assert sig in ("B2", "B1")


def test_b3_breakout():
    nav = uptrend(daily=1.0015)
    nav.iloc[-1] = nav.iloc[-1] * 1.02  # 创 20 日新高但偏离 MA20 不超过 6%
    assert detect_buy_signal("001480", nav, score=4, prev_score=3) == "B3"


# --- 卖出信号 ---

def test_s2_below_ma60_with_falling_ma20():
    vals = (100 * 1.003 ** np.arange(60)).tolist()
    decline = (vals[-1] * np.array([1.0, .97, .94, .91, .88, .85, .83, .81, .79, .77,
                                    .75, .73, .71, .69, .67, .65, .63, .61, .59, .57])).tolist()
    nav = series(vals + decline)
    sig = detect_sell_signal("001480", nav, score=1, prev_score=3)
    assert sig is not None and sig[0] == "S2" and sig[1] == "to_core"


def test_s3_fund_drawdown_ladder():
    base = uptrend().tolist()
    dd8 = series(base[:-1] + [base[-1] * 0.92])   # 距20日高点约 -8%
    sig = detect_sell_signal("001480", dd8, score=3, prev_score=4)
    assert sig is not None and sig[0] == "S3" and sig[1] == 0.25
    dd18 = series(base[:-1] + [base[-1] * 0.80])  # -20% ≥ 18% → 退出全部战术仓
    sig = detect_sell_signal("001480", dd18, score=1, prev_score=3)
    assert sig is not None and sig[0] == "S3" and sig[1] == 1.0


def test_morgan_drawdown_rules():
    base = uptrend().tolist()
    dd6 = series(base[:-1] + [base[-1] * 0.935])
    sig = detect_sell_signal("005052", dd6, score=3, prev_score=4)
    assert sig is not None and sig[0] == "S3" and sig[1] == 0.20
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run --directory packages/quant-core pytest tests/test_rules.py -v`
Expected: FAIL `ModuleNotFoundError`

- [ ] **Step 3: 写实现**

```python
# quant_core/rules.py
"""买入四闸门 + B/S 信号识别（PDF 06/08/09 章）。engine 负责金额与周单元预算。"""
from __future__ import annotations

import pandas as pd

from .config import DD_WARN, FUNDS
from .indicators import drawdown_from_high, last_daily_return, ma


# --- 闸门 ---

def gate_portfolio_ok(portfolio_dd: float, bucket: str) -> bool:
    """组合回撤 ≥6% 停止新增科技；≥8% 只允许补防御仓（对基金买入等价）。"""
    return bucket != "tech" or portfolio_dd < DD_WARN


def gate_score_ok(code: str, score: int) -> bool:
    return score >= FUNDS[code].min_score_to_buy


def gate_position_ok(code: str, nav: pd.Series) -> bool:
    """科技基金：偏离 MA20 ≤ +8% 且单日涨幅 ≤5%（防追高）。"""
    if FUNDS[code].bucket != "tech":
        return True
    dev = float(nav.iloc[-1]) / ma(nav, 20) - 1
    if dev > 0.08:
        return False
    return last_daily_return(nav) <= 0.05


# --- 买入信号（B4 由 engine 按权重差判定） ---

def detect_buy_signal(
    code: str, nav: pd.Series, score: int, prev_score: int | None,
) -> str | None:
    ma20, ma60 = ma(nav, 20), ma(nav, 60)
    last = float(nav.iloc[-1])
    dd20 = drawdown_from_high(nav, 20)
    # B2 回撤加仓（优先级最高）：MA20>MA60、nav>MA60、距20日高点回撤4%-8%、当日转正
    if ma20 > ma60 and last > ma60 and 0.04 <= dd20 <= 0.08 and last_daily_return(nav) > 0:
        return "B2"
    # B1 趋势建仓：连续两次周度评分≥4 且 nav>MA60
    if prev_score is not None and prev_score >= 4 and score >= 4 and last > ma60:
        return "B1"
    # B3 突破加仓：创20日新高、评分≥4、偏离 MA20 ≤6%
    if last >= float(nav.iloc[-20:].max()) * (1 - 1e-9) and score >= 4 and last / ma20 - 1 <= 0.06:
        return "B3"
    return None


# --- 卖出信号 ---

def _ma_at(nav: pd.Series, window: int, offset: int) -> float:
    """offset 个交易日之前的 MA(window)。offset=0 即当前。"""
    end = len(nav) - offset
    return float(nav.iloc[end - window:end].mean())


def detect_sell_signal(
    code: str, nav: pd.Series, score: int, prev_score: int | None,
) -> tuple[str, float | str] | None:
    """返回 (理由, 卖出比例) 或 (理由, "to_core")。多个触发取最保守（卖出最多）。"""
    fund = FUNDS[code]
    last = float(nav.iloc[-1])
    ma20, ma60 = ma(nav, 20), ma(nav, 60)
    dd20 = drawdown_from_high(nav, 20)
    candidates: list[tuple[str, float | str]] = []

    if fund.bucket == "tech":
        if dd20 >= 0.18:
            candidates.append(("S3", 1.0))                     # 退出全部战术仓
        elif dd20 >= 0.12 and last < ma60:
            candidates.append(("S3", 0.5))                     # 卖剩余战术仓 50%
        elif dd20 >= 0.08 and last < ma20:
            candidates.append(("S3", 0.25))
    else:
        if dd20 >= 0.10 and last < ma60:
            candidates.append(("S3", "to_core"))               # 摩根降至核心仓
        elif dd20 >= 0.06 and last < ma20:
            candidates.append(("S3", 0.20))

    # S2：低于 MA60 且 MA20 斜率为负 → 降至核心仓
    if last < ma60 and ma20 < _ma_at(nav, 20, 1):
        candidates.append(("S2", "to_core"))

    # S1：连续 2 日低于 MA20 且评分下降 ≥2 → 卖 25%（engine 再与"降至目标"取大）
    if (
        last < ma20
        and float(nav.iloc[-2]) < _ma_at(nav, 20, 1)
        and prev_score is not None
        and prev_score - score >= 2
    ):
        candidates.append(("S1", 0.25))

    if not candidates:
        return None

    def severity(item: tuple[str, float | str]) -> float:
        return 1.0 if item[1] == "to_core" else float(item[1])

    return max(candidates, key=severity)
```

- [ ] **Step 4: 跑测试确认通过**

Run: `uv run --directory packages/quant-core pytest tests/test_rules.py -v`
Expected: 9 passed

- [ ] **Step 5: Commit**

```bash
git add packages/quant-core
git commit -m "feat(quant-core): 四闸门与 B/S 信号识别"
```

---

### Task 9: engine.py SignalReport 组装

**Files:**
- Create: `packages/quant-core/quant_core/engine.py`
- Test: `packages/quant-core/tests/test_engine.py`

**Interfaces:**
- Consumes: 前面全部模块
- Produces（后续 quant-api 与 golden 测试依赖这些确切签名）:
  - `Metrics` dataclass：`last, ma20, ma60, r20, r60, vol20, dd20, day_ret: float`
  - `compute_metrics(nav: pd.Series) -> Metrics`
  - `AccountState` dataclass：`total_value, cash_value, peak_value, net_contributed, peak_profit_rate: float`；属性 `portfolio_dd -> float`
  - `FundDecision` dataclass：`code, name, score, score_multiplier, vol20, vol_multiplier, regime_base_weight, target_weight, current_value, target_value, gap, action, reason_code, amount, units, gates: dict[str, bool], notes: list[str]`
  - `SignalReport` dataclass：`as_of: str, regime, total_value, portfolio_dd, peak_profit_rate, cash_value, cash_weight, decisions: list[FundDecision], weekly_unit_budget: int, account_actions: list[str]`
  - `build_decisions(regime, scores, vols, navs, holdings, account, capital_plan="15k", prev_scores=None) -> list[FundDecision]`
  - `build_signal_report(navs, holdings, account, capital_plan="15k", prev_scores=None, as_of=None) -> SignalReport`

规则要点（PDF 08/09/10 章）：
- 死区：`|gap| < 300` 或 `|gap|/total < 0.03` → HOLD/N0
- 买入金额：`min(gap, unit_limit × factor, 可用现金)`；B3 factor=0.5，其余 1.0；可用现金 = `cash - total × cash_min(regime)`
- 周单元预算：全账户合计 `units ≤ MAX_UNITS_PER_WEEK`；按 B2 > B1 > B4 > B3 排序分配（B3 计 0.5 单元）
- 卖出：S1 取 `max(0.25×current, current - target_value)`；`to_core` → `current - total × core_weight`；硬风控（S2/组合档）不受每周 25% 缓冲
- 账户级动作（写入 `account_actions`）：峰值利润率 ≥12% → "P2 至少锁定一半浮盈转现金"；≥20% → "现金 ≥50%"；dd≥15% → "硬防御：现金 ≥70%，仅保留核心仓"

- [ ] **Step 1: 写失败测试**

```python
# tests/test_engine.py
import numpy as np
import pandas as pd
import pytest

from quant_core.engine import (
    AccountState, build_decisions, build_signal_report, compute_metrics,
)


def uptrend(days=80, daily=1.002):
    vals = 100 * daily ** np.arange(days)
    return pd.Series(vals, index=pd.date_range("2026-01-01", periods=days, freq="B"))


def make_account(total=19044.07, cash=15000.0):
    return AccountState(
        total_value=total, cash_value=cash, peak_value=total,
        net_contributed=total, peak_profit_rate=0.0,
    )


def test_compute_metrics_keys():
    m = compute_metrics(uptrend())
    assert m.ma20 > 0 and m.ma60 > 0 and m.vol20 >= 0
    assert m.last == pytest.approx(float(uptrend().iloc[-1]))


def test_build_decisions_example_a():
    scores = {"001480": 4, "025343": 3, "027521": 2, "005052": 4}
    vols = {"001480": 0.20, "025343": 0.20, "027521": 0.20, "005052": 0.10}
    navs = {c: uptrend() for c in scores}
    holdings = {"001480": 2107.85, "025343": 949.85, "027521": 495.12, "005052": 491.25}
    decisions = build_decisions(
        "neutral", scores, vols, navs, holdings, make_account(), capital_plan="15k",
    )
    by_code = {d.code: d for d in decisions}
    assert by_code["001480"].target_weight == pytest.approx(0.1875)
    assert by_code["001480"].amount == pytest.approx(663.0)   # 受单元上限
    assert by_code["025343"].amount == pytest.approx(477.0)
    assert by_code["027521"].action == "HOLD"                 # gap=-19 死区
    assert by_code["005052"].amount == pytest.approx(1067.0)
    buys = [d for d in decisions if d.action == "BUY"]
    assert sum(d.units for d in buys) <= 2                    # 周单元预算


def test_sell_to_core_bypasses_weekly_buffer():
    scores = {"001480": 2, "025343": 4, "027521": 4, "005052": 4}
    vols = {c: 0.20 for c in scores}
    # 财通跌破 MA60 的下行序列
    vals = (100 * 1.003 ** np.arange(60)).tolist()
    decline = (vals[-1] * np.array([1.0, .97, .94, .91, .88, .85, .83, .81, .79, .77,
                                    .75, .73, .71, .69, .67, .65, .63, .61, .59, .57])).tolist()
    navs = {c: uptrend() for c in scores}
    navs["001480"] = pd.Series(vals + decline,
                               index=pd.date_range("2026-01-01", periods=80, freq="B"))
    holdings = {"001480": 6000.0, "025343": 3000.0, "027521": 1000.0, "005052": 5000.0}
    account = AccountState(total_value=24000.0, cash_value=9000.0, peak_value=24000.0,
                           net_contributed=24000.0, peak_profit_rate=0.0)
    decisions = build_decisions("neutral", scores, vols, navs, holdings, account)
    ct = {d.code: d for d in decisions}["001480"]
    assert ct.action == "SELL"
    # 目标 6.25%×24000=1500；硬风控卖到目标：4500（不受 25% 缓冲）
    assert ct.amount == pytest.approx(4500.0)
    assert ct.reason_code == "S2"


def test_build_signal_report_end_to_end():
    navs = {c: uptrend() for c in ("001480", "025343", "027521", "005052")}
    holdings = {"001480": 2107.85, "025343": 949.85, "027521": 495.12, "005052": 491.25}
    report = build_signal_report(navs, holdings, make_account())
    assert report.regime in ("offensive", "neutral", "protect", "defensive")
    assert len(report.decisions) == 4
    assert report.cash_weight == pytest.approx(15000.0 / 19044.07)


def test_profit_lock_account_action():
    account = AccountState(total_value=22400.0, cash_value=5000.0, peak_value=22400.0,
                           net_contributed=20000.0, peak_profit_rate=0.12)
    navs = {c: uptrend() for c in ("001480", "025343", "027521", "005052")}
    holdings = {"001480": 5000.0, "025343": 3000.0, "027521": 1500.0, "005052": 7900.0}
    report = build_signal_report(navs, holdings, account)
    assert any("P2" in a for a in report.account_actions)
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run --directory packages/quant-core pytest tests/test_engine.py -v`
Expected: FAIL `ModuleNotFoundError`

- [ ] **Step 3: 写实现**

```python
# quant_core/engine.py
"""SignalReport 组装：指标 → 评分 → 模式 → 目标权重 → 闸门 → 建议动作（PDF 16 章伪代码）。"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import pandas as pd

from .config import (
    DEADBAND_AMOUNT, DEADBAND_WEIGHT, FUNDS, MAX_UNITS_PER_WEEK,
    PROFIT_LOCK_12, PROFIT_LOCK_20, DD_HARD, REGIME_CASH_MIN, UNIT_LIMITS,
)
from .constraints import apply_caps
from .indicators import (
    drawdown_from_high, last_daily_return, ma, period_return, realized_vol,
)
from .regime import market_regime
from .rules import (
    detect_buy_signal, detect_sell_signal,
    gate_portfolio_ok, gate_position_ok, gate_score_ok,
)
from .scoring import score_multiplier, trend_score
from .sizing import target_weight as _target_weight, vol_multiplier as _vol_mult


@dataclass(frozen=True)
class Metrics:
    last: float
    ma20: float
    ma60: float
    r20: float
    r60: float
    vol20: float
    dd20: float
    day_ret: float


def compute_metrics(nav: pd.Series) -> Metrics:
    return Metrics(
        last=float(nav.iloc[-1]), ma20=ma(nav, 20), ma60=ma(nav, 60),
        r20=period_return(nav, 20), r60=period_return(nav, 60),
        vol20=realized_vol(nav, 20), dd20=drawdown_from_high(nav, 20),
        day_ret=last_daily_return(nav),
    )


@dataclass(frozen=True)
class AccountState:
    total_value: float
    cash_value: float
    peak_value: float
    net_contributed: float
    peak_profit_rate: float

    @property
    def portfolio_dd(self) -> float:
        return 1 - self.total_value / self.peak_value if self.peak_value > 0 else 0.0


@dataclass
class FundDecision:
    code: str
    name: str
    score: int
    score_multiplier: float
    vol20: float
    vol_multiplier: float
    regime_base_weight: float
    target_weight: float
    current_value: float
    target_value: float
    gap: float
    action: str          # 'BUY' | 'SELL' | 'HOLD'
    reason_code: str     # B1-B4 / S1-S4 / P1-P2 / N0
    amount: float
    units: float
    gates: dict[str, bool] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


@dataclass
class SignalReport:
    as_of: str
    regime: str
    total_value: float
    portfolio_dd: float
    peak_profit_rate: float
    cash_value: float
    cash_weight: float
    decisions: list[FundDecision]
    weekly_unit_budget: int
    account_actions: list[str]


_BUY_PRIORITY = {"B2": 0, "B1": 1, "B4": 2, "B3": 3}


def build_decisions(
    regime: str,
    scores: dict[str, int],
    vols: dict[str, float],
    navs: dict[str, pd.Series],
    holdings: dict[str, float],
    account: AccountState,
    capital_plan: str = "15k",
    prev_scores: dict[str, int] | None = None,
) -> list[FundDecision]:
    total = account.total_value
    dd = account.portfolio_dd
    unit_limits = UNIT_LIMITS[capital_plan]
    prev_scores = prev_scores or {}

    raw_weights = {
        c: _target_weight(regime, c, scores[c], vols[c]) for c in FUNDS
    }
    weights = apply_caps(raw_weights, regime)

    cash_min_value = total * REGIME_CASH_MIN[regime]
    cash_available = max(0.0, account.cash_value - cash_min_value)

    decisions: list[FundDecision] = []
    for code, fund in FUNDS.items():
        nav = navs[code]
        score = scores[code]
        vol = vols[code]
        current = holdings[code]
        tw = weights[code]
        target_value = total * tw
        gap = target_value - current
        gates = {
            "portfolio": gate_portfolio_ok(dd, fund.bucket),
            "score": gate_score_ok(code, score),
            "position": gate_position_ok(code, nav),
        }
        d = FundDecision(
            code=code, name=fund.name, score=score,
            score_multiplier=score_multiplier(score), vol20=vol,
            vol_multiplier=_vol_mult(vol, fund.vol_bands),
            regime_base_weight=raw_weights[code], target_weight=tw,
            current_value=current, target_value=target_value, gap=gap,
            action="HOLD", reason_code="N0", amount=0.0, units=0.0, gates=gates,
        )

        in_deadband = abs(gap) < DEADBAND_AMOUNT or abs(gap) / total < DEADBAND_WEIGHT

        if gap < 0 and not in_deadband:
            # --- 卖出侧 ---
            sell = detect_sell_signal(code, nav, score, prev_scores.get(code))
            if sell is not None:
                reason, frac = sell
                if frac == "to_core":
                    amount = max(0.0, current - total * fund.core_weight)
                else:
                    amount = float(frac) * current
                    if reason == "S1":
                        amount = max(amount, current - target_value)
                d.action, d.reason_code = "SELL", reason
                d.amount = round(amount, 2)
            else:
                # 目标权重纠偏卖出：普通缓冲每周最多 25%
                d.action, d.reason_code = "SELL", "S4" if dd >= DD_HARD else "S1"
                d.amount = round(min(-gap, current * 0.25), 2)
                d.notes.append("普通纠偏受每周25%缓冲约束")
        elif gap > 0 and not in_deadband:
            # --- 买入侧 ---
            if all(gates.values()) and cash_available > 0:
                signal = detect_buy_signal(code, nav, score, prev_scores.get(code))
                if signal is None and gap / total >= DEADBAND_WEIGHT and score >= 3:
                    signal = "B4"  # 再平衡买入
                if signal is not None:
                    factor = 0.5 if signal == "B3" else 1.0
                    amount = min(gap, unit_limits[code] * factor, cash_available)
                    if amount >= DEADBAND_AMOUNT:
                        d.action, d.reason_code = "BUY", signal
                        d.amount = round(amount, 2)
                        d.units = factor
            elif not gates["portfolio"]:
                d.notes.append("组合回撤闸门：禁止新增科技")
            elif not gates["score"]:
                d.notes.append(f"评分 {score} 未达买入门槛 {fund.min_score_to_buy}")
            elif not gates["position"]:
                d.notes.append("位置闸门：偏离 MA20 过高或单日涨幅>5%")
        decisions.append(d)

    # 周单元预算：按 B2>B1>B4>B3 分配，超额者降级 HOLD
    budget = float(MAX_UNITS_PER_WEEK)
    for d in sorted((x for x in decisions if x.action == "BUY"),
                    key=lambda x: _BUY_PRIORITY[x.reason_code]):
        if d.units <= budget:
            budget -= d.units
        else:
            d.action, d.reason_code, d.amount, d.units = "HOLD", "N0", 0.0, 0.0
            d.notes.append("超出本周单元预算，顺延")
    return decisions


def build_signal_report(
    navs: dict[str, pd.Series],
    holdings: dict[str, float],
    account: AccountState,
    capital_plan: str = "15k",
    prev_scores: dict[str, int] | None = None,
    as_of: date | None = None,
) -> SignalReport:
    scores = {c: trend_score(navs[c]) for c in FUNDS}
    vols = {c: realized_vol(navs[c], 20) for c in FUNDS}
    tech_scores = {c: scores[c] for c in FUNDS if FUNDS[c].bucket == "tech"}
    regime = market_regime(tech_scores, account.portfolio_dd, account.peak_profit_rate)
    decisions = build_decisions(
        regime, scores, vols, navs, holdings, account, capital_plan, prev_scores,
    )

    account_actions: list[str] = []
    if account.peak_profit_rate >= PROFIT_LOCK_20:
        account_actions.append("P2 峰值利润率≥20%：现金 ≥50%，等待新中期趋势")
    elif account.peak_profit_rate >= PROFIT_LOCK_12:
        lock = 0.5 * max(0.0, account.peak_value - account.net_contributed)
        account_actions.append(f"P2 峰值利润率≥12%：至少锁定 {lock:.0f} 元浮盈转现金，现金 ≥40%")
    if account.portfolio_dd >= DD_HARD:
        account_actions.append("S4 硬防御：现金 ≥70%，仅保留核心仓，重新评估风险承受能力")

    return SignalReport(
        as_of=(as_of or date.today()).isoformat(),
        regime=regime,
        total_value=account.total_value,
        portfolio_dd=account.portfolio_dd,
        peak_profit_rate=account.peak_profit_rate,
        cash_value=account.cash_value,
        cash_weight=account.cash_value / account.total_value if account.total_value else 0.0,
        decisions=decisions,
        weekly_unit_budget=MAX_UNITS_PER_WEEK,
        account_actions=account_actions,
    )
```

- [ ] **Step 4: 跑测试确认通过**

Run: `uv run --directory packages/quant-core pytest tests/test_engine.py -v`
Expected: 5 passed

- [ ] **Step 5: 更新 `quant_core/__init__.py` re-export**

```python
"""纯算法库：方案 PDF 规则的代码化。禁止 import Web/DB/网络框架。"""
from .engine import (  # noqa: F401
    AccountState, FundDecision, SignalReport, build_decisions, build_signal_report,
    compute_metrics,
)
```

- [ ] **Step 6: Commit**

```bash
git add packages/quant-core
git commit -m "feat(quant-core): SignalReport 引擎组装"
```

---

### Task 10: 黄金测试 —— PDF 第 13 章算例 A/B/C

**Files:**
- Test: `packages/quant-core/tests/test_golden_examples.py`

**Interfaces:**
- Consumes: `engine.build_decisions`, `engine.AccountState`，`sizing.target_weight`
- Produces: 防回归的权威基准；任何参数改动若破坏算例必须显式更新本文件并在 PR 说明

- [ ] **Step 1: 写黄金测试**

```python
# tests/test_golden_examples.py
"""PDF 第 13 章三个算例的金额必须与方案表格一致（允许 ±1 元舍入差）。"""
import numpy as np
import pandas as pd
import pytest

from quant_core.engine import AccountState, build_decisions
from quant_core.sizing import target_weight

CODES = ("001480", "025343", "027521", "005052")


def uptrend(days=80, daily=1.002):
    vals = 100 * daily ** np.arange(days)
    return pd.Series(vals, index=pd.date_range("2026-01-01", periods=days, freq="B"))


def test_example_a_first_weekly_check():
    """追加1.5万后首次周度检查：中性，评分 4/3/2/4，回撤2%（忽略波动缩放）。"""
    total = 19044.07
    scores = {"001480": 4, "025343": 3, "027521": 2, "005052": 4}
    vols = {"001480": 0.20, "025343": 0.20, "027521": 0.20, "005052": 0.10}
    navs = {c: uptrend() for c in CODES}
    holdings = {"001480": 2107.85, "025343": 949.85, "027521": 495.12, "005052": 491.25}
    account = AccountState(total_value=total, cash_value=15000.0,
                           peak_value=total / 0.98, net_contributed=total,
                           peak_profit_rate=0.011)
    decisions = {d.code: d for d in build_decisions(
        "neutral", scores, vols, navs, holdings, account, capital_plan="15k")}

    # 目标权重（PDF 表格）
    assert decisions["001480"].target_weight == pytest.approx(0.1875)
    assert decisions["025343"].target_weight == pytest.approx(0.075)
    assert decisions["027521"].target_weight == pytest.approx(0.025)
    assert decisions["005052"].target_weight == pytest.approx(0.1875)
    # 目标金额（PDF 表格：3571 / 1428 / 476 / 3571）
    assert decisions["001480"].target_value == pytest.approx(3571, abs=1)
    assert decisions["025343"].target_value == pytest.approx(1428, abs=1)
    assert decisions["027521"].target_value == pytest.approx(476, abs=1)
    assert decisions["005052"].target_value == pytest.approx(3571, abs=1)
    # 执行金额受单元上限约束
    assert decisions["001480"].amount == pytest.approx(663, abs=1)
    assert decisions["025343"].amount == pytest.approx(477, abs=1)
    assert decisions["005052"].amount == pytest.approx(1067, abs=1)
    # 广发理论卖出 19 元 < 300 死区 → 不动
    assert decisions["027521"].action == "HOLD"
    # 本周合计约 2,207-2,208 元
    spent = sum(d.amount for d in decisions.values() if d.action == "BUY")
    assert spent == pytest.approx(2208, abs=2)


def test_example_b_trend_break_sell():
    """财通评分 4→2 且跌破 MA60：目标 6.25%，硬风控直接卖到目标。"""
    assert target_weight("neutral", "001480", score=2, vol=0.20) == pytest.approx(0.0625)
    total, current = 24000.0, 6000.0
    target_value = total * 0.0625
    assert target_value == pytest.approx(1500.0)
    assert current - target_value == pytest.approx(4500.0)
    # 端到端验证（nav 序列构造跌破 MA60 且 MA20 下行）
    vals = (100 * 1.003 ** np.arange(60)).tolist()
    decline = (vals[-1] * np.array([1.0, .97, .94, .91, .88, .85, .83, .81, .79, .77,
                                    .75, .73, .71, .69, .67, .65, .63, .61, .59, .57])).tolist()
    navs = {c: uptrend() for c in CODES}
    navs["001480"] = pd.Series(vals + decline,
                               index=pd.date_range("2026-01-01", periods=80, freq="B"))
    scores = {"001480": 2, "025343": 4, "027521": 4, "005052": 4}
    vols = {c: 0.20 for c in CODES}
    holdings = {"001480": 6000.0, "025343": 3000.0, "027521": 1000.0, "005052": 5000.0}
    account = AccountState(total_value=total, cash_value=9000.0, peak_value=total,
                           net_contributed=total, peak_profit_rate=0.0)
    d = {x.code: x for x in build_decisions("neutral", scores, vols, navs, holdings,
                                            account)}["001480"]
    assert d.action == "SELL" and d.reason_code == "S2"
    assert d.amount == pytest.approx(4500.0, abs=1)


def test_example_c_profit_lock():
    """峰值 22400、净投入 20000 → 至少锁定 1200 元，现金 ≥40%。"""
    from quant_core.config import PROFIT_LOCK_12
    peak, contributed = 22400.0, 20000.0
    profit_rate = (peak - contributed) / contributed
    assert profit_rate == pytest.approx(0.12)
    assert profit_rate >= PROFIT_LOCK_12
    lock = 0.5 * max(0.0, peak - contributed)
    assert lock == pytest.approx(1200.0)
```

- [ ] **Step 2: 跑测试确认通过**

Run: `uv run --directory packages/quant-core pytest tests/test_golden_examples.py -v`
Expected: 3 passed

- [ ] **Step 3: 全量回归**

Run: `uv run --directory packages/quant-core pytest -v`
Expected: 全部通过（约 40 个用例）

- [ ] **Step 4: Commit**

```bash
git add packages/quant-core
git commit -m "test(quant-core): PDF 算例 A/B/C 黄金测试"
```

---

### Task 11: quant-api 骨架 + DB + 交易账本 API

**Files:**
- Create: `services/quant-api/pyproject.toml`
- Create: `services/quant-api/app/__init__.py`（空文件）
- Create: `services/quant-api/app/db.py`
- Create: `services/quant-api/app/models.py`
- Create: `services/quant-api/app/schemas.py`
- Create: `services/quant-api/app/ledger.py`
- Create: `services/quant-api/app/routers/__init__.py`（空文件）
- Create: `services/quant-api/app/routers/trades.py`
- Create: `services/quant-api/app/main.py`
- Test: `services/quant-api/tests/test_trades_api.py`

**Interfaces:**
- Produces:
  - `POST /api/trades`（body `TradeIn`）→ 创建账本记录；`GET /api/trades` → 列表
  - `ledger.cash_balance(db) -> float`；`ledger.net_contributed(db) -> float`；`ledger.shares_by_fund(db) -> dict[str, float]`；`ledger.latest_navs(db) -> dict[str, tuple[date, float]]`；`ledger.holdings_value(db) -> dict[str, float]`；`ledger.open_lots(db, code) -> list[dict]`
  - 账本方向：`buy / sell / deposit / withdraw`；现金 = 入金 - 出金 - 买入 + 卖出；净投入 = 入金 - 出金

- [ ] **Step 1: 写 pyproject 与 DB/模型层**

```toml
# services/quant-api/pyproject.toml
[project]
name = "quant-api"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115",
    "uvicorn>=0.30",
    "sqlalchemy>=2.0",
    "pydantic>=2.7",
    "pandas>=2.2",
    "akshare>=1.14",
    "quant-core",
]

[dependency-groups]
dev = ["pytest>=8.0", "httpx>=0.27"]

[tool.uv]
package = false

[tool.uv.sources]
quant-core = { path = "../../packages/quant-core", editable = true }
```

```python
# app/models.py
from datetime import date

from sqlalchemy import Float, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Fund(Base):
    __tablename__ = "funds"
    code: Mapped[str] = mapped_column(String(8), primary_key=True)
    name: Mapped[str] = mapped_column(String(64))
    bucket: Mapped[str] = mapped_column(String(16))
    role: Mapped[str] = mapped_column(String(16))
    cap: Mapped[float] = mapped_column(Float)
    proxy_code: Mapped[str | None] = mapped_column(String(8), nullable=True)


class NavHistory(Base):
    __tablename__ = "nav_history"
    __table_args__ = (UniqueConstraint("fund_code", "date"),)
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    fund_code: Mapped[str] = mapped_column(String(8), index=True)
    date: Mapped[date]
    nav: Mapped[float] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(8), default="auto")


class Trade(Base):
    __tablename__ = "trades"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    date: Mapped[date]
    fund_code: Mapped[str | None] = mapped_column(String(8), nullable=True)
    direction: Mapped[str] = mapped_column(String(8))  # buy/sell/deposit/withdraw
    amount: Mapped[float] = mapped_column(Float)
    shares: Mapped[float | None] = mapped_column(Float, nullable=True)
    nav: Mapped[float | None] = mapped_column(Float, nullable=True)
    reason_code: Mapped[str | None] = mapped_column(String(4), nullable=True)
    fee_estimate: Mapped[float | None] = mapped_column(Float, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)


class WeeklySignal(Base):
    __tablename__ = "weekly_signals"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    as_of: Mapped[date]
    report_json: Mapped[str] = mapped_column(Text)
    total_value: Mapped[float] = mapped_column(Float)
    net_contributed: Mapped[float] = mapped_column(Float)
```

```python
# app/db.py
import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .models import Base

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = Path(os.environ.get("QUANT_API_DB", str(DATA_DIR / "investment.db")))

engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    Base.metadata.create_all(engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 2: 写账本推导与 schemas**

```python
# app/ledger.py
"""从 trades 账本推导现金/份额/持仓/净投入。账本即真相，无冗余状态表。"""
from __future__ import annotations

from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from .models import NavHistory, Trade, WeeklySignal


def _sums_by_direction(db: Session) -> dict[str, float]:
    rows = db.query(Trade.direction, func.sum(Trade.amount)).group_by(Trade.direction).all()
    return {d: float(s or 0.0) for d, s in rows}


def cash_balance(db: Session) -> float:
    s = _sums_by_direction(db)
    return s.get("deposit", 0.0) - s.get("withdraw", 0.0) - s.get("buy", 0.0) + s.get("sell", 0.0)


def net_contributed(db: Session) -> float:
    s = _sums_by_direction(db)
    return s.get("deposit", 0.0) - s.get("withdraw", 0.0)


def shares_by_fund(db: Session) -> dict[str, float]:
    out: dict[str, float] = {}
    rows = (
        db.query(Trade.fund_code, Trade.direction, func.sum(Trade.shares))
        .filter(Trade.fund_code.isnot(None))
        .group_by(Trade.fund_code, Trade.direction)
        .all()
    )
    for code, direction, total in rows:
        out.setdefault(code, 0.0)
        out[code] += float(total or 0.0) * (1 if direction == "buy" else -1)
    return out


def latest_navs(db: Session) -> dict[str, tuple[date, float]]:
    out: dict[str, tuple[date, float]] = {}
    codes = [r[0] for r in db.query(NavHistory.fund_code).distinct().all()]
    for code in codes:
        row = (
            db.query(NavHistory)
            .filter(NavHistory.fund_code == code)
            .order_by(NavHistory.date.desc())
            .first()
        )
        if row:
            out[code] = (row.date, row.nav)
    return out


def holdings_value(db: Session) -> dict[str, float]:
    shares = shares_by_fund(db)
    navs = latest_navs(db)
    return {c: sh * navs[c][1] for c, sh in shares.items() if c in navs and sh > 0}


def account_snapshot(db: Session) -> dict:
    """当前账户状态 + 历史峰值（峰值取自 weekly_signals 快照与当前值的较大者）。"""
    cash = cash_balance(db)
    contributed = net_contributed(db)
    holdings = holdings_value(db)
    total = cash + sum(holdings.values())
    peaks = [
        (s.total_value, s.net_contributed)
        for s in db.query(WeeklySignal).all()
    ] + [(total, contributed)]
    peak_value = max(p for p, _ in peaks if p > 0) if any(p > 0 for p, _ in peaks) else total
    profit_rates = [
        (p - c) / c for p, c in peaks if c > 0
    ]
    return {
        "cash": cash,
        "net_contributed": contributed,
        "holdings": holdings,
        "total_value": total,
        "peak_value": peak_value,
        "portfolio_dd": 1 - total / peak_value if peak_value > 0 else 0.0,
        "peak_profit_rate": max(profit_rates) if profit_rates else 0.0,
    }


def open_lots(db: Session, code: str, as_of: date) -> list[dict]:
    """FIFO 批次：买入为批次，卖出按先进先出冲销。用于持有天数与赎回费窗口。"""
    from quant_core.fees import redemption_fee_rate

    trades = (
        db.query(Trade)
        .filter(Trade.fund_code == code, Trade.direction.in_(["buy", "sell"]))
        .order_by(Trade.date, Trade.id)
        .all()
    )
    lots: list[dict] = []
    for t in trades:
        if t.direction == "buy":
            lots.append({"date": t.date, "shares": float(t.shares or 0.0)})
        else:
            remaining = float(t.shares or 0.0)
            while remaining > 1e-9 and lots:
                take = min(lots[0]["shares"], remaining)
                lots[0]["shares"] -= take
                remaining -= take
                if lots[0]["shares"] <= 1e-9:
                    lots.pop(0)
    return [
        {
            "buy_date": lot["date"].isoformat(),
            "shares": round(lot["shares"], 2),
            "holding_days": (as_of - lot["date"]).days,
            "fee_rate": redemption_fee_rate(code, (as_of - lot["date"]).days),
        }
        for lot in lots
    ]
```

```python
# app/schemas.py
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, model_validator

REASON_CODES = {"B1", "B2", "B3", "B4", "S1", "S2", "S3", "S4", "P1", "P2", "N0"}


class TradeIn(BaseModel):
    date: date
    direction: Literal["buy", "sell", "deposit", "withdraw"]
    fund_code: str | None = None
    amount: float = Field(gt=0)
    shares: float | None = None
    nav: float | None = None
    reason_code: str | None = None
    fee_estimate: float | None = None
    note: str | None = None

    @model_validator(mode="after")
    def check_fields(self):
        if self.direction in ("buy", "sell"):
            if not self.fund_code or self.shares is None or self.nav is None:
                raise ValueError("buy/sell 必须提供 fund_code、shares、nav")
            if self.reason_code is not None and self.reason_code not in REASON_CODES:
                raise ValueError(f"非法理由代码: {self.reason_code}")
        else:
            if self.fund_code is not None:
                raise ValueError("deposit/withdraw 不应带 fund_code")
        return self


class TradeOut(TradeIn):
    id: int

    model_config = {"from_attributes": True}
```

- [ ] **Step 3: 写 trades 路由与 main**

```python
# app/routers/trades.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Trade
from ..schemas import TradeIn, TradeOut

router = APIRouter(prefix="/api/trades", tags=["trades"])


@router.get("", response_model=list[TradeOut])
def list_trades(db: Session = Depends(get_db)):
    return db.query(Trade).order_by(Trade.date.desc(), Trade.id.desc()).all()


@router.post("", response_model=TradeOut, status_code=201)
def create_trade(payload: TradeIn, db: Session = Depends(get_db)):
    trade = Trade(**payload.model_dump())
    db.add(trade)
    db.commit()
    db.refresh(trade)
    return trade
```

```python
# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import init_db
from .routers import trades

app = FastAPI(title="quant-api", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


app.include_router(trades.router)
```

- [ ] **Step 4: 写失败测试**

```python
# tests/test_trades_api.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import get_db
from app.main import app
from app.models import Base


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_deposit_then_buy_flow(client):
    r = client.post("/api/trades", json={
        "date": "2026-08-01", "direction": "deposit", "amount": 19044.07,
    })
    assert r.status_code == 201, r.text
    r = client.post("/api/trades", json={
        "date": "2026-08-03", "direction": "buy", "fund_code": "001480",
        "amount": 2107.85, "shares": 1500.0, "nav": 1.4052, "reason_code": "B1",
    })
    assert r.status_code == 201, r.text
    trades = client.get("/api/trades").json()
    assert len(trades) == 2


def test_buy_requires_fund_fields(client):
    r = client.post("/api/trades", json={
        "date": "2026-08-03", "direction": "buy", "amount": 1000.0,
    })
    assert r.status_code == 422


def test_invalid_reason_code_rejected(client):
    r = client.post("/api/trades", json={
        "date": "2026-08-03", "direction": "buy", "fund_code": "001480",
        "amount": 1000.0, "shares": 700.0, "nav": 1.43, "reason_code": "X9",
    })
    assert r.status_code == 422
```

- [ ] **Step 5: 跑测试确认通过**

Run: `uv run --directory services/quant-api pytest tests/test_trades_api.py -v`
Expected: 3 passed

- [ ] **Step 6: 启动冒烟**

Run: `uv run --directory services/quant-api uvicorn app.main:app --port 8000` 后访问 `http://localhost:8000/api/health`
Expected: `{"status": "ok"}`（Ctrl+C 停止）

- [ ] **Step 7: Commit**

```bash
git add services/quant-api
git commit -m "feat(quant-api): FastAPI 骨架 + 交易账本 API"
```

---

### Task 12: 数据管道 —— akshare 抓取 + 手动导入 + stale 标记

**Files:**
- Create: `services/quant-api/app/fetcher.py`
- Create: `services/quant-api/app/routers/nav.py`
- Create: `services/quant-api/app/seed.py`
- Modify: `services/quant-api/app/main.py`（注册 nav 路由 + 启动时 seed funds）
- Test: `services/quant-api/tests/test_nav_api.py`

**Interfaces:**
- Consumes: Task 11 的 models/db
- Produces:
  - `fetcher.fetch_fund_nav(code: str) -> pd.Series`（天天基金单位净值）；`fetcher.fetch_etf_nav(code: str) -> pd.Series`（ETF 收盘价，供 589210 代理）
  - `POST /api/nav/refresh` → `{results: [{code, status, added, error?}]}`（含代理 589210；单基金失败不影响其他）
  - `POST /api/nav/import`（body `{fund_code, rows: [{date, nav}]}`，source=manual）→ `{added}`
  - `GET /api/nav/{code}?days=120` → `{code, stale, rows: [{date, nav, source}]}`；stale = 最新净值距今 >7 天
  - `seed.seed_funds(db)`：从 `quant_core.config.FUNDS` 写入 funds 表（幂等）

- [ ] **Step 1: 写 fetcher 与 seed**

```python
# app/fetcher.py
"""akshare 抓取。天天基金/东财接口变动的唯一定位点——解析只许改这里。"""
from __future__ import annotations

import akshare as ak
import pandas as pd


def fetch_fund_nav(code: str) -> pd.Series:
    """场外基金单位净值，index=date，升序。"""
    df = ak.fund_open_fund_info_em(symbol=code, indicator="单位净值走势")
    s = pd.Series(
        df["单位净值"].astype(float).to_numpy(),
        index=pd.to_datetime(df["净值日期"]).date,
    )
    return s.sort_index()


def fetch_etf_nav(code: str) -> pd.Series:
    """ETF 日收盘价（供 589210 信号代理），index=date，升序。"""
    df = ak.fund_etf_hist_em(symbol=code, period="daily", adjust="")
    s = pd.Series(
        df["收盘"].astype(float).to_numpy(),
        index=pd.to_datetime(df["日期"]).date,
    )
    return s.sort_index()
```

```python
# app/seed.py
from sqlalchemy.orm import Session
from quant_core.config import FUNDS

from .models import Fund


def seed_funds(db: Session) -> None:
    for f in FUNDS.values():
        if db.get(Fund, f.code) is None:
            db.add(Fund(code=f.code, name=f.name, bucket=f.bucket,
                        role=f.role, cap=f.cap, proxy_code=f.proxy_code))
    db.commit()
```

- [ ] **Step 2: 写 nav 路由**

```python
# app/routers/nav.py
from datetime import date, timedelta

import pandas as pd
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from quant_core.config import FUNDS

from ..db import get_db
from ..fetcher import fetch_etf_nav, fetch_fund_nav
from ..models import NavHistory

router = APIRouter(prefix="/api/nav", tags=["nav"])

STALE_DAYS = 7


def _upsert_navs(db: Session, code: str, series: pd.Series, source: str) -> int:
    existing = {
        r[0] for r in db.query(NavHistory.date)
        .filter(NavHistory.fund_code == code).all()
    }
    added = 0
    for d, v in series.items():
        if d not in existing:
            db.add(NavHistory(fund_code=code, date=d, nav=float(v), source=source))
            added += 1
    db.commit()
    return added


@router.post("/refresh")
def refresh(db: Session = Depends(get_db)):
    results = []
    targets = {c: fetch_fund_nav for c in FUNDS}
    targets["589210"] = fetch_etf_nav  # 广发联接 C 的信号代理
    for code, fn in targets.items():
        try:
            added = _upsert_navs(db, code, fn(code), "auto")
            results.append({"code": code, "status": "ok", "added": added})
        except Exception as exc:  # 单基金失败不影响其他
            results.append({"code": code, "status": "error", "added": 0,
                            "error": str(exc)[:200]})
    return {"results": results}


class NavRow(BaseModel):
    date: date
    nav: float


class NavImportIn(BaseModel):
    fund_code: str
    rows: list[NavRow]


@router.post("/import")
def import_navs(payload: NavImportIn, db: Session = Depends(get_db)):
    series = pd.Series({r.date: r.nav for r in payload.rows}).sort_index()
    return {"added": _upsert_navs(db, payload.fund_code, series, "manual")}


@router.get("/{code}")
def get_navs(code: str, days: int = 120, db: Session = Depends(get_db)):
    rows = (
        db.query(NavHistory)
        .filter(NavHistory.fund_code == code)
        .order_by(NavHistory.date.desc())
        .limit(days)
        .all()
    )
    rows.reverse()
    latest = rows[-1].date if rows else None
    stale = latest is None or (date.today() - latest) > timedelta(days=STALE_DAYS)
    return {
        "code": code,
        "stale": stale,
        "rows": [{"date": r.date.isoformat(), "nav": r.nav, "source": r.source}
                 for r in rows],
    }
```

- [ ] **Step 3: 注册路由 + 启动 seed**

Modify `app/main.py`：在 `startup()` 中追加 seed 并注册路由：

```python
from .db import SessionLocal, init_db
from .routers import nav, trades
from .seed import seed_funds

# startup() 内：
    init_db()
    db = SessionLocal()
    try:
        seed_funds(db)
    finally:
        db.close()

# 文件尾部：
app.include_router(trades.router)
app.include_router(nav.router)
```

- [ ] **Step 4: 写测试（mock fetcher，不打真实网络）**

```python
# tests/test_nav_api.py
from datetime import date, timedelta

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import get_db
from app.main import app
from app.models import Base


@pytest.fixture()
def client():
    engine = create_engine("sqlite:///:memory:",
                           connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_import_and_get(client):
    today = date.today()
    rows = [{"date": (today - timedelta(days=i)).isoformat(), "nav": 1.0 + i * 0.001}
            for i in range(5)]
    r = client.post("/api/nav/import", json={"fund_code": "001480", "rows": rows})
    assert r.status_code == 201 or r.status_code == 200
    assert r.json()["added"] == 5
    # 重复导入幂等
    assert client.post("/api/nav/import",
                       json={"fund_code": "001480", "rows": rows}).json()["added"] == 0
    data = client.get("/api/nav/001480").json()
    assert data["stale"] is False
    assert len(data["rows"]) == 5
    assert all(row["source"] == "manual" for row in data["rows"])


def test_stale_flag(client):
    old = (date.today() - timedelta(days=30)).isoformat()
    client.post("/api/nav/import",
                json={"fund_code": "005052", "rows": [{"date": old, "nav": 1.0}]})
    assert client.get("/api/nav/005052").json()["stale"] is True


def test_refresh_partial_failure(client, monkeypatch):
    import app.routers.nav as nav_router

    def ok(code):
        return pd.Series({date.today(): 1.5})

    def boom(code):
        raise RuntimeError("network down")

    monkeypatch.setattr(nav_router, "fetch_fund_nav", ok)
    monkeypatch.setattr(nav_router, "fetch_etf_nav", boom)
    r = client.post("/api/nav/refresh")
    assert r.status_code == 200
    results = {x["code"]: x for x in r.json()["results"]}
    assert results["001480"]["status"] == "ok"
    assert results["589210"]["status"] == "error"
```

- [ ] **Step 5: 跑测试确认通过**

Run: `uv run --directory services/quant-api pytest tests/test_nav_api.py -v`
Expected: 3 passed

- [ ] **Step 6: Commit**

```bash
git add services/quant-api
git commit -m "feat(quant-api): akshare 数据管道 + 手动导入 + stale 标记"
```

---

### Task 13: 信号计算 + 持仓组合 API

**Files:**
- Create: `services/quant-api/app/routers/signals.py`
- Create: `services/quant-api/app/routers/portfolio.py`
- Modify: `services/quant-api/app/main.py`（注册路由）
- Test: `services/quant-api/tests/test_signals_api.py`

**Interfaces:**
- Consumes: `quant_core.engine.build_signal_report / AccountState`，`ledger`，nav 表
- Produces:
  - `POST /api/signals/compute` → SignalReport JSON（并持久化快照到 weekly_signals）
  - `GET /api/signals/latest` → 最近快照（无则 404）
  - `GET /api/portfolio` → `{funds: [{code, name, shares, nav, nav_date, value, weight, lots: [...]}], account: {cash, net_contributed, total_value, peak_value, portfolio_dd, peak_profit_rate}}`
  - `GET /api/rebalance` → 基于最近快照的 `{deviations: [{code, current_weight, target_weight, diff_pp, structural: bool}]}`（structural = |diff| ≥5pp，PDF 月度复核阈值）
- 代理规则：027521 自身净值点 <61 时用 589210 序列计算评分/指标，报告 notes 标注"信号来自代理 ETF"

- [ ] **Step 1: 写 signals 路由**

```python
# app/routers/signals.py
import json
from dataclasses import asdict
from datetime import date

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from quant_core.config import FUNDS
from quant_core.engine import AccountState, build_signal_report

from ..db import get_db
from ..ledger import account_snapshot
from ..models import NavHistory, WeeklySignal

router = APIRouter(prefix="/api/signals", tags=["signals"])

MIN_POINTS = 61  # MA60 至少需要 61 个点（60 日收益）


def _load_series(db: Session, code: str) -> pd.Series:
    rows = (
        db.query(NavHistory)
        .filter(NavHistory.fund_code == code)
        .order_by(NavHistory.date)
        .all()
    )
    return pd.Series({r.date: r.nav for r in rows}).sort_index()


def _navs_with_proxy(db: Session) -> tuple[dict[str, pd.Series], list[str]]:
    navs, notes = {}, []
    for code, fund in FUNDS.items():
        s = _load_series(db, code)
        if len(s) < MIN_POINTS and fund.proxy_code:
            s = _load_series(db, fund.proxy_code)
            notes.append(f"{code} 历史不足 {MIN_POINTS} 点，信号来自代理 ETF {fund.proxy_code}")
        navs[code] = s
    return navs, notes


@router.post("/compute")
def compute(db: Session = Depends(get_db)):
    navs, notes = _navs_with_proxy(db)
    short = [c for c, s in navs.items() if len(s) < MIN_POINTS]
    if short:
        raise HTTPException(422, detail={"error": "净值数据不足", "funds": short})
    snap = account_snapshot(db)
    account = AccountState(
        total_value=snap["total_value"], cash_value=snap["cash"],
        peak_value=snap["peak_value"], net_contributed=snap["net_contributed"],
        peak_profit_rate=snap["peak_profit_rate"],
    )
    last = db.query(WeeklySignal).order_by(WeeklySignal.id.desc()).first()
    prev_scores = None
    if last:
        prev = json.loads(last.report_json)
        prev_scores = {d["code"]: d["score"] for d in prev["decisions"]}
    report = build_signal_report(navs, snap["holdings"], account,
                                 prev_scores=prev_scores)
    for note in notes:
        for d in report.decisions:
            if d.code in note:
                d.notes.append(note)
    payload = asdict(report)
    db.add(WeeklySignal(
        as_of=date.today(), report_json=json.dumps(payload, ensure_ascii=False),
        total_value=account.total_value, net_contributed=account.net_contributed,
    ))
    db.commit()
    return payload


@router.get("/latest")
def latest(db: Session = Depends(get_db)):
    row = db.query(WeeklySignal).order_by(WeeklySignal.id.desc()).first()
    if row is None:
        raise HTTPException(404, detail="尚无信号快照，请先 POST /api/signals/compute")
    return json.loads(row.report_json)
```

- [ ] **Step 2: 写 portfolio 路由**

```python
# app/routers/portfolio.py
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from quant_core.config import FUNDS

from ..db import get_db
from ..ledger import (
    account_snapshot, latest_navs, open_lots, shares_by_fund,
)
from ..models import WeeklySignal

import json

router = APIRouter(prefix="/api", tags=["portfolio"])


@router.get("/portfolio")
def portfolio(db: Session = Depends(get_db)):
    snap = account_snapshot(db)
    shares = shares_by_fund(db)
    navs = latest_navs(db)
    funds = []
    for code, fund in FUNDS.items():
        value = snap["holdings"].get(code, 0.0)
        nav_date, nav_val = navs.get(code, (None, None))
        funds.append({
            "code": code,
            "name": fund.name,
            "shares": round(shares.get(code, 0.0), 2),
            "nav": nav_val,
            "nav_date": nav_date.isoformat() if nav_date else None,
            "value": round(value, 2),
            "weight": round(value / snap["total_value"], 4) if snap["total_value"] else 0.0,
            "lots": open_lots(db, code, date.today()),
        })
    return {"funds": funds, "account": snap}


@router.get("/rebalance")
def rebalance(db: Session = Depends(get_db)):
    row = db.query(WeeklySignal).order_by(WeeklySignal.id.desc()).first()
    if row is None:
        return {"deviations": []}
    report = json.loads(row.report_json)
    total = report["total_value"]
    deviations = []
    for d in report["decisions"]:
        current_w = d["current_value"] / total if total else 0.0
        diff = d["target_weight"] - current_w
        deviations.append({
            "code": d["code"],
            "current_weight": round(current_w, 4),
            "target_weight": round(d["target_weight"], 4),
            "diff_pp": round(diff * 100, 2),
            "structural": abs(diff) >= 0.05,  # PDF 月度复核：≥5pp 才结构性调仓
        })
    return {"deviations": deviations}
```

- [ ] **Step 3: 注册路由**

Modify `app/main.py`：`from .routers import nav, portfolio, signals, trades` 并追加
`app.include_router(signals.router)` 与 `app.include_router(portfolio.router)`。

- [ ] **Step 4: 写测试**

```python
# tests/test_signals_api.py
from datetime import date, timedelta

import numpy as np
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import get_db
from app.main import app
from app.models import Base, NavHistory

CODES = ("001480", "025343", "027521", "005052", "589210")


@pytest.fixture()
def client():
    engine = create_engine("sqlite:///:memory:",
                           connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def seed_navs(client):
    # 直接走 DB：为每只基金插入 80 个交易日的温和上行净值
    from app.db import get_db as _  # noqa
    override = app.dependency_overrides[get_db]
    db = next(iter([s for s in override()]))
    start = date.today() - timedelta(days=120)
    days = [start + timedelta(days=i) for i in range(80)]
    for code in CODES:
        for i, d in enumerate(days):
            db.add(NavHistory(fund_code=code, date=d,
                              nav=float(100 * 1.002 ** i), source="manual"))
    db.commit()
    db.close()


def test_compute_and_latest(client):
    seed_navs(client)
    client.post("/api/trades", json={
        "date": "2026-08-01", "direction": "deposit", "amount": 19044.07})
    client.post("/api/trades", json={
        "date": "2026-08-03", "direction": "buy", "fund_code": "001480",
        "amount": 2107.85, "shares": 1500.0, "nav": 1.4052, "reason_code": "B1"})
    r = client.post("/api/signals/compute")
    assert r.status_code == 200, r.text
    report = r.json()
    assert report["regime"] in ("offensive", "neutral", "protect", "defensive")
    assert len(report["decisions"]) == 4
    assert all(d["reason_code"] in
               {"B1", "B2", "B3", "B4", "S1", "S2", "S3", "S4", "P1", "P2", "N0"}
               for d in report["decisions"])
    latest = client.get("/api/signals/latest")
    assert latest.status_code == 200
    assert latest.json()["as_of"] == report["as_of"]
    pf = client.get("/api/portfolio").json()
    assert pf["account"]["net_contributed"] == pytest.approx(19044.07)
    ct = next(f for f in pf["funds"] if f["code"] == "001480")
    assert ct["shares"] == pytest.approx(1500.0)
    assert len(ct["lots"]) == 1
    rb = client.get("/api/rebalance").json()
    assert len(rb["deviations"]) == 4


def test_compute_without_data_returns_422(client):
    r = client.post("/api/signals/compute")
    assert r.status_code == 422


def test_latest_404_before_first_compute(client):
    assert client.get("/api/signals/latest").status_code == 404
```

注意：`seed_navs` 里从 override 取 session 的写法若嫌绕，可直接在 fixture 里把 `TestingSession` 挂到 `client.testing_session` 属性上供 seed 使用——实现时任选其一，但测试断言不得变。

- [ ] **Step 5: 跑测试确认通过**

Run: `uv run --directory services/quant-api pytest -v`
Expected: 全部通过（含 trades/nav 共 9+ 个用例）

- [ ] **Step 6: Commit**

```bash
git add services/quant-api
git commit -m "feat(quant-api): 信号计算/持仓/再平衡 API"
```

---

### Task 14: web 脚手架 + BFF 代理 + API 客户端

**Files:**
- Create: `apps/web/`（create-next-app 生成）
- Create: `apps/web/app/api/[...path]/route.ts`
- Create: `apps/web/lib/types.ts`
- Create: `apps/web/lib/api.ts`
- Create: `apps/web/vitest.config.ts`
- Create: `apps/web/vitest.setup.ts`
- Modify: `apps/web/package.json`（加 test 脚本）

**Interfaces:**
- Produces:
  - BFF：前端 `/api/*` 全部代理到 `QUANT_API_URL`（默认 `http://localhost:8000`）
  - `lib/api.ts` 的 `api` 对象：`latestSignals / computeSignals / refreshNav / portfolio / trades / createTrade`
  - `lib/types.ts`：`SignalReport / FundDecision / Portfolio / PortfolioFund / AccountInfo / Trade / Lot`
  - 页面组件消费方式：客户端组件 `"use client"` + `useEffect` 调 `api.*`

- [ ] **Step 1: create-next-app + shadcn 初始化**

```bash
pnpm create next-app@latest apps/web --typescript --tailwind --eslint --app --no-src-dir --import-alias "@/*" --use-pnpm --turbopack
pnpm --dir apps/web dlx shadcn@latest init -y -d
pnpm --dir apps/web dlx shadcn@latest add card button badge
pnpm --dir apps/web add recharts
pnpm --dir apps/web add -D vitest @vitejs/plugin-react @testing-library/react @testing-library/jest-dom jsdom
```

- [ ] **Step 2: 写 BFF 代理**

```typescript
// apps/web/app/api/[...path]/route.ts
const BACKEND = process.env.QUANT_API_URL ?? "http://localhost:8000";

async function proxy(req: Request, ctx: { params: Promise<{ path: string[] }> }) {
  const { path } = await ctx.params;
  const search = new URL(req.url).search;
  const url = `${BACKEND}/api/${path.join("/")}${search}`;
  const init: RequestInit = {
    method: req.method,
    headers: { "content-type": req.headers.get("content-type") ?? "application/json" },
    cache: "no-store",
  };
  if (req.method !== "GET" && req.method !== "HEAD") init.body = await req.text();
  try {
    const res = await fetch(url, init);
    const body = await res.text();
    return new Response(body, {
      status: res.status,
      headers: { "content-type": res.headers.get("content-type") ?? "application/json" },
    });
  } catch {
    return Response.json({ error: "quant-api 不可达，请先启动 dev:api" }, { status: 502 });
  }
}

export { proxy as GET, proxy as POST };
```

- [ ] **Step 3: 写类型与 API 客户端**

```typescript
// apps/web/lib/types.ts
export interface FundDecision {
  code: string;
  name: string;
  score: number;
  score_multiplier: number;
  vol20: number;
  vol_multiplier: number;
  regime_base_weight: number;
  target_weight: number;
  current_value: number;
  target_value: number;
  gap: number;
  action: "BUY" | "SELL" | "HOLD";
  reason_code: string;
  amount: number;
  units: number;
  gates: Record<string, boolean>;
  notes: string[];
}

export interface SignalReport {
  as_of: string;
  regime: string;
  total_value: number;
  portfolio_dd: number;
  peak_profit_rate: number;
  cash_value: number;
  cash_weight: number;
  decisions: FundDecision[];
  weekly_unit_budget: number;
  account_actions: string[];
}

export interface Lot {
  buy_date: string;
  shares: number;
  holding_days: number;
  fee_rate: number;
}

export interface PortfolioFund {
  code: string;
  name: string;
  shares: number;
  nav: number | null;
  nav_date: string | null;
  value: number;
  weight: number;
  lots: Lot[];
}

export interface AccountInfo {
  cash: number;
  net_contributed: number;
  holdings: Record<string, number>;
  total_value: number;
  peak_value: number;
  portfolio_dd: number;
  peak_profit_rate: number;
}

export interface Portfolio {
  funds: PortfolioFund[];
  account: AccountInfo;
}

export interface Trade {
  id: number;
  date: string;
  direction: "buy" | "sell" | "deposit" | "withdraw";
  fund_code: string | null;
  amount: number;
  shares: number | null;
  nav: number | null;
  reason_code: string | null;
  fee_estimate: number | null;
  note: string | null;
}

export const REGIME_LABELS: Record<string, string> = {
  offensive: "进攻", neutral: "中性", protect: "利润保护", defensive: "防守",
};

export const REASON_LABELS: Record<string, string> = {
  B1: "趋势建仓", B2: "回撤加仓", B3: "突破加仓", B4: "再平衡买入",
  S1: "MA20失效", S2: "MA60失效", S3: "单基金回撤", S4: "组合回撤",
  P1: "过热减仓", P2: "账户利润锁定", N0: "无交易",
};
```

```typescript
// apps/web/lib/api.ts
import type { Portfolio, SignalReport, Trade } from "./types";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, { cache: "no-store", ...init });
  if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
  return res.json() as Promise<T>;
}

export interface RefreshResult {
  results: { code: string; status: string; added: number; error?: string }[];
}

export const api = {
  latestSignals: () => req<SignalReport>("/signals/latest"),
  computeSignals: () => req<SignalReport>("/signals/compute", { method: "POST" }),
  refreshNav: () => req<RefreshResult>("/nav/refresh", { method: "POST" }),
  portfolio: () => req<Portfolio>("/portfolio"),
  trades: () => req<Trade[]>("/trades"),
  createTrade: (t: Omit<Trade, "id">) =>
    req<Trade>("/trades", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(t),
    }),
};
```

- [ ] **Step 4: 配 Vitest**

```typescript
// apps/web/vitest.config.ts
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: ["./vitest.setup.ts"],
    include: ["__tests__/**/*.test.tsx"],
  },
  resolve: { alias: { "@": new URL(".", import.meta.url).pathname } },
});
```

```typescript
// apps/web/vitest.setup.ts
import "@testing-library/jest-dom";
```

`apps/web/package.json` 的 scripts 加：`"test": "vitest run"`。

- [ ] **Step 5: 验证**

Run: `pnpm --dir apps/web build`
Expected: Next.js 构建成功（页面任务在后续 Task 添加）

- [ ] **Step 6: Commit**

```bash
git add apps/web pnpm-workspace.yaml pnpm-lock.yaml
git commit -m "feat(web): Next.js 脚手架 + BFF 代理 + API 客户端"
```

注：根目录需有 `pnpm-workspace.yaml`（内容 `packages: ["apps/*"]`），若 create-next-app 未自动生成则手动创建。

---

### Task 15: 仪表盘页面 `/`

**Files:**
- Create: `apps/web/components/StatCard.tsx`
- Create: `apps/web/components/WeightChart.tsx`
- Create: `apps/web/app/page.tsx`
- Modify: `apps/web/app/layout.tsx`（顶部导航：仪表盘/每周信号/交易日志/持仓与资金）
- Test: `apps/web/__tests__/dashboard.test.tsx`

**Interfaces:**
- Consumes: `api.portfolio()`, `api.latestSignals()`（404 时容忍，显示"尚未生成信号"）
- Produces: `StatCard({title, value, sub?})`；`WeightChart({decisions} | {funds, total})` 当前 vs 目标权重条形图

- [ ] **Step 1: 写失败测试**

```tsx
// apps/web/__tests__/dashboard.test.tsx
import { render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";
import Dashboard from "../app/page";

const portfolioPayload = {
  funds: [
    { code: "001480", name: "财通成长优选混合A", shares: 1500, nav: 1.4052,
      nav_date: "2026-08-04", value: 2107.85, weight: 0.11, lots: [] },
  ],
  account: { cash: 15000, net_contributed: 19044.07, holdings: { "001480": 2107.85 },
             total_value: 19044.07, peak_value: 19044.07, portfolio_dd: 0.02,
             peak_profit_rate: 0.011 },
};

function mockFetch() {
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
    const url = String(input);
    if (url.includes("/api/portfolio"))
      return Promise.resolve(new Response(JSON.stringify(portfolioPayload), { status: 200 }));
    if (url.includes("/api/signals/latest"))
      return Promise.resolve(new Response("not found", { status: 404 }));
    return Promise.resolve(new Response("{}", { status: 200 }));
  }));
}

test("仪表盘渲染账户概览", async () => {
  mockFetch();
  render(<Dashboard />);
  await waitFor(() => expect(screen.getByText("账户总资产")).toBeInTheDocument());
  expect(screen.getByText(/19,044/)).toBeInTheDocument();
  expect(screen.getByText("组合回撤")).toBeInTheDocument();
});
```

- [ ] **Step 2: 跑测试确认失败**

Run: `pnpm --dir apps/web test`
Expected: FAIL（组件不存在）

- [ ] **Step 3: 写实现**

```tsx
// apps/web/components/StatCard.tsx
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function StatCard({ title, value, sub }: { title: string; value: string; sub?: string }) {
  return (
    <Card>
      <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">{title}</CardTitle></CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        {sub && <div className="text-xs text-muted-foreground mt-1">{sub}</div>}
      </CardContent>
    </Card>
  );
}
```

```tsx
// apps/web/components/WeightChart.tsx
"use client";
import { Bar, BarChart, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export interface WeightPoint { name: string; current: number; target: number }

export function WeightChart({ data }: { data: WeightPoint[] }) {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={data}>
        <XAxis dataKey="name" fontSize={12} />
        <YAxis tickFormatter={(v) => `${v}%`} fontSize={12} />
        <Tooltip formatter={(v) => `${Number(v).toFixed(1)}%`} />
        <Legend />
        <Bar dataKey="current" name="当前权重" fill="#2563eb" />
        <Bar dataKey="target" name="目标权重" fill="#93c5fd" />
      </BarChart>
    </ResponsiveContainer>
  );
}
```

```tsx
// apps/web/app/page.tsx
"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Portfolio, SignalReport } from "@/lib/types";
import { REGIME_LABELS } from "@/lib/types";
import { StatCard } from "@/components/StatCard";
import { WeightChart, type WeightPoint } from "@/components/WeightChart";
import { Badge } from "@/components/ui/badge";

const fmt = (n: number) => n.toLocaleString("zh-CN", { maximumFractionDigits: 2 });
const pct = (n: number) => `${(n * 100).toFixed(1)}%`;

export default function Dashboard() {
  const [pf, setPf] = useState<Portfolio | null>(null);
  const [sig, setSig] = useState<SignalReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.portfolio().then(setPf).catch((e) => setError(String(e)));
    api.latestSignals().then(setSig).catch(() => setSig(null)); // 404 容忍
  }, []);

  if (error) return <main className="p-8 text-red-600">加载失败：{error}（quant-api 是否在运行？）</main>;
  if (!pf) return <main className="p-8">加载中…</main>;

  const a = pf.account;
  const weights: WeightPoint[] = sig
    ? sig.decisions.map((d) => ({
        name: d.name.slice(0, 4), current: +(d.current_value / sig.total_value * 100).toFixed(1),
        target: +(d.target_weight * 100).toFixed(1),
      }))
    : pf.funds.map((f) => ({ name: f.name.slice(0, 4), current: +(f.weight * 100).toFixed(1), target: 0 }));

  return (
    <main className="p-8 space-y-6">
      <div className="flex items-center gap-3">
        <h1 className="text-xl font-bold">仪表盘</h1>
        {sig && <Badge>{REGIME_LABELS[sig.regime] ?? sig.regime}模式 · {sig.as_of}</Badge>}
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard title="账户总资产" value={`¥${fmt(a.total_value)}`} sub={`净投入 ¥${fmt(a.net_contributed)}`} />
        <StatCard title="组合回撤" value={pct(a.portfolio_dd)} sub="回撤 ≥6% 停加科技，≥12% 防守" />
        <StatCard title="现金比例" value={pct(a.total_value ? a.cash / a.total_value : 0)} sub={`现金 ¥${fmt(a.cash)}`} />
        <StatCard title="峰值利润率" value={pct(a.peak_profit_rate)} sub="≥12% 锁定一半浮盈" />
      </div>
      <section>
        <h2 className="font-semibold mb-2">当前权重 vs 目标权重</h2>
        <WeightChart data={weights} />
        {!sig && <p className="text-sm text-muted-foreground">尚未生成信号快照——到"每周信号"页点"计算信号"。</p>}
      </section>
    </main>
  );
}
```

`app/layout.tsx`：在 `{children}` 上方加导航条：

```tsx
<nav className="flex gap-4 px-8 py-3 border-b text-sm">
  <a href="/">仪表盘</a>
  <a href="/signals">每周信号</a>
  <a href="/trades">交易日志</a>
  <a href="/portfolio">持仓与资金</a>
</nav>
```

- [ ] **Step 4: 跑测试确认通过**

Run: `pnpm --dir apps/web test`
Expected: 1 passed

- [ ] **Step 5: Commit**

```bash
git add apps/web
git commit -m "feat(web): 仪表盘页面"
```

---

### Task 16: 每周信号页 `/signals`

**Files:**
- Create: `apps/web/components/DecisionCard.tsx`
- Create: `apps/web/app/signals/page.tsx`

**Interfaces:**
- Consumes: `api.refreshNav()`, `api.computeSignals()`, `api.latestSignals()`，`types.SignalReport / REGIME_LABELS / REASON_LABELS`
- Produces: `DecisionCard({d: FundDecision})`：评分、四道闸门逐项 ✅/❌、动作徽标（BUY 绿 / SELL 红 / HOLD 灰）、金额、理由代码中文、notes 列表

- [ ] **Step 1: 写实现**

```tsx
// apps/web/components/DecisionCard.tsx
import type { FundDecision } from "@/lib/types";
import { REASON_LABELS } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const GATE_LABELS: Record<string, string> = {
  portfolio: "组合风险闸门", score: "趋势闸门", position: "追高闸门",
};
const ACTION_STYLE = { BUY: "bg-green-600", SELL: "bg-red-600", HOLD: "bg-gray-400" } as const;

export function DecisionCard({ d }: { d: FundDecision }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">{d.name} <span className="text-xs text-muted-foreground">{d.code}</span></CardTitle>
          <Badge className={ACTION_STYLE[d.action]}>
            {d.action === "HOLD" ? "不动" : `${d.action === "BUY" ? "买入" : "卖出"} ¥${d.amount.toLocaleString("zh-CN")}`}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="text-sm space-y-2">
        <div>趋势评分 <b>{d.score}/5</b> · 乘数 {d.score_multiplier} · 波动 {(d.vol20 * 100).toFixed(0)}% → ×{d.vol_multiplier}</div>
        <div>目标权重 {(d.target_weight * 100).toFixed(2)}%（¥{d.target_value.toFixed(0)}）· 当前 ¥{d.current_value.toFixed(0)} · 差额 ¥{d.gap.toFixed(0)}</div>
        <div className="flex gap-3">
          {Object.entries(d.gates).map(([k, ok]) => (
            <span key={k}>{ok ? "✅" : "❌"}{GATE_LABELS[k] ?? k}</span>
          ))}
        </div>
        <div>理由：<Badge variant="outline">{d.reason_code} {REASON_LABELS[d.reason_code]}</Badge></div>
        {d.notes.length > 0 && <ul className="text-amber-700 list-disc pl-5">{d.notes.map((n, i) => <li key={i}>{n}</li>)}</ul>}
      </CardContent>
    </Card>
  );
}
```

```tsx
// apps/web/app/signals/page.tsx
"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { SignalReport } from "@/lib/types";
import { REGIME_LABELS } from "@/lib/types";
import { DecisionCard } from "@/components/DecisionCard";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export default function SignalsPage() {
  const [report, setReport] = useState<SignalReport | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    api.latestSignals().then(setReport).catch(() => setReport(null));
  }, []);

  async function refreshNav() {
    setBusy("nav"); setMessage(null);
    try {
      const r = await api.refreshNav();
      const failed = r.results.filter((x) => x.status !== "ok");
      setMessage(failed.length
        ? `部分抓取失败：${failed.map((x) => x.code).join("、")}——可手动导入净值兜底`
        : `净值已更新（${r.results.map((x) => `${x.code}+${x.added}`).join("，")}）`);
    } catch (e) { setMessage(`抓取失败：${e}`); }
    setBusy(null);
  }

  async function compute() {
    setBusy("compute"); setMessage(null);
    try { setReport(await api.computeSignals()); }
    catch (e) { setMessage(`计算失败：${e}`); }
    setBusy(null);
  }

  return (
    <main className="p-8 space-y-6">
      <div className="flex items-center gap-3">
        <h1 className="text-xl font-bold">每周信号</h1>
        <Button onClick={refreshNav} disabled={busy !== null}>{busy === "nav" ? "抓取中…" : "1. 更新净值"}</Button>
        <Button onClick={compute} disabled={busy !== null} variant="secondary">{busy === "compute" ? "计算中…" : "2. 计算信号"}</Button>
        {report && <Badge>{REGIME_LABELS[report.regime]}模式 · {report.as_of}</Badge>}
      </div>
      {message && <p className="text-sm text-amber-700">{message}</p>}
      {report?.account_actions.map((a, i) => (
        <p key={i} className="text-sm font-medium text-red-700 border border-red-200 bg-red-50 rounded p-2">{a}</p>
      ))}
      {report ? (
        <>
          <p className="text-sm text-muted-foreground">
            组合回撤 {(report.portfolio_dd * 100).toFixed(1)}% · 现金 {(report.cash_weight * 100).toFixed(1)}%
            · 本周单元预算 {report.weekly_unit_budget} 个 · 成交净值以确认日为准（未知价原则）
          </p>
          <div className="grid md:grid-cols-2 gap-4">
            {report.decisions.map((d) => <DecisionCard key={d.code} d={d} />)}
          </div>
        </>
      ) : (
        <p className="text-muted-foreground">尚无信号。先"更新净值"，再"计算信号"。没有信号时持有现金是正确动作（N0）。</p>
      )}
    </main>
  );
}
```

- [ ] **Step 2: 验证**

Run: `pnpm --dir apps/web build && pnpm --dir apps/web test`
Expected: 构建成功，已有测试不回归

- [ ] **Step 3: Commit**

```bash
git add apps/web
git commit -m "feat(web): 每周信号页"
```

---

### Task 17: 交易日志页 `/trades`

**Files:**
- Create: `apps/web/app/trades/page.tsx`

**Interfaces:**
- Consumes: `api.trades()`, `api.createTrade()`，`types.Trade / REASON_LABELS`
- Produces: 录入表单（方向联动字段：buy/sell 显示基金/份额/净值/理由代码；deposit/withdraw 仅金额）+ 列表（按日期倒序）

- [ ] **Step 1: 写实现**

```tsx
// apps/web/app/trades/page.tsx
"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Trade } from "@/lib/types";
import { REASON_LABELS } from "@/lib/types";
import { Button } from "@/components/ui/button";

const FUNDS: [string, string][] = [
  ["001480", "财通成长优选混合A"], ["025343", "长盛上证科创板芯片指数C"],
  ["027521", "广发科创芯片设计ETF联接C"], ["005052", "摩根标普港股通低波红利指数C"],
];
const DIRECTION_LABELS: Record<string, string> = { buy: "买入", sell: "卖出", deposit: "入金", withdraw: "出金" };

const empty = {
  date: new Date().toISOString().slice(0, 10), direction: "buy", fund_code: "001480",
  amount: "", shares: "", nav: "", reason_code: "B1", fee_estimate: "", note: "",
};

export default function TradesPage() {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [form, setForm] = useState(empty);
  const [error, setError] = useState<string | null>(null);
  const isFundTrade = form.direction === "buy" || form.direction === "sell";

  const load = () => api.trades().then(setTrades).catch((e) => setError(String(e)));
  useEffect(() => { load(); }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault(); setError(null);
    try {
      await api.createTrade({
        date: form.date,
        direction: form.direction as Trade["direction"],
        fund_code: isFundTrade ? form.fund_code : null,
        amount: parseFloat(form.amount),
        shares: isFundTrade ? parseFloat(form.shares) : null,
        nav: isFundTrade ? parseFloat(form.nav) : null,
        reason_code: isFundTrade ? form.reason_code : null,
        fee_estimate: form.fee_estimate ? parseFloat(form.fee_estimate) : null,
        note: form.note || null,
      });
      setForm(empty);
      load();
    } catch (err) { setError(String(err)); }
  }

  const input = "border rounded px-2 py-1 text-sm";
  return (
    <main className="p-8 space-y-6">
      <h1 className="text-xl font-bold">交易日志</h1>
      <form onSubmit={submit} className="flex flex-wrap gap-2 items-end border rounded p-4">
        <label className="text-sm">日期<input type="date" className={input} value={form.date}
          onChange={(e) => setForm({ ...form, date: e.target.value })} /></label>
        <label className="text-sm">方向
          <select className={input} value={form.direction}
            onChange={(e) => setForm({ ...form, direction: e.target.value })}>
            {Object.entries(DIRECTION_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select></label>
        {isFundTrade && <>
          <label className="text-sm">基金
            <select className={input} value={form.fund_code}
              onChange={(e) => setForm({ ...form, fund_code: e.target.value })}>
              {FUNDS.map(([c, n]) => <option key={c} value={c}>{n}</option>)}
            </select></label>
          <label className="text-sm">份额<input className={`${input} w-24`} value={form.shares}
            onChange={(e) => setForm({ ...form, shares: e.target.value })} /></label>
          <label className="text-sm">确认净值<input className={`${input} w-24`} value={form.nav}
            onChange={(e) => setForm({ ...form, nav: e.target.value })} /></label>
          <label className="text-sm">理由代码
            <select className={input} value={form.reason_code}
              onChange={(e) => setForm({ ...form, reason_code: e.target.value })}>
              {Object.entries(REASON_LABELS).filter(([c]) => c !== "N0").map(([c, l]) =>
                <option key={c} value={c}>{c} {l}</option>)}
            </select></label>
          <label className="text-sm">费用估计<input className={`${input} w-20`} value={form.fee_estimate}
            onChange={(e) => setForm({ ...form, fee_estimate: e.target.value })} /></label>
        </>}
        <label className="text-sm">金额<input required className={`${input} w-28`} value={form.amount}
          onChange={(e) => setForm({ ...form, amount: e.target.value })} /></label>
        <label className="text-sm">备注<input className={`${input} w-40`} value={form.note}
          onChange={(e) => setForm({ ...form, note: e.target.value })} /></label>
        <Button type="submit">记录</Button>
      </form>
      {error && <p className="text-sm text-red-600">{error}</p>}
      <table className="w-full text-sm border">
        <thead><tr className="bg-muted text-left">
          {["日期", "方向", "基金", "金额", "份额", "净值", "理由", "费用", "备注"].map((h) =>
            <th key={h} className="p-2">{h}</th>)}
        </tr></thead>
        <tbody>
          {trades.map((t) => (
            <tr key={t.id} className="border-t">
              <td className="p-2">{t.date}</td>
              <td className="p-2">{DIRECTION_LABELS[t.direction]}</td>
              <td className="p-2">{t.fund_code ?? "—"}</td>
              <td className="p-2">{t.amount.toLocaleString("zh-CN")}</td>
              <td className="p-2">{t.shares ?? "—"}</td>
              <td className="p-2">{t.nav ?? "—"}</td>
              <td className="p-2">{t.reason_code ?? "—"}</td>
              <td className="p-2">{t.fee_estimate ?? "—"}</td>
              <td className="p-2">{t.note ?? ""}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </main>
  );
}
```

- [ ] **Step 2: 验证**

Run: `pnpm --dir apps/web build && pnpm --dir apps/web test`
Expected: 构建成功，测试不回归

- [ ] **Step 3: Commit**

```bash
git add apps/web
git commit -m "feat(web): 交易日志页"
```

---

### Task 18: 持仓与资金页 `/portfolio`

**Files:**
- Create: `apps/web/app/portfolio/page.tsx`

**Interfaces:**
- Consumes: `api.portfolio()`（funds 含 FIFO lots：buy_date/shares/holding_days/fee_rate）
- Produces: 持仓表（份额/最新净值/市值/权重）+ 每基金批次费用窗口表（fee_rate>0 的批次红色提示"仍在赎回费窗口"）

- [ ] **Step 1: 写实现**

```tsx
// apps/web/app/portfolio/page.tsx
"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Portfolio } from "@/lib/types";

const fmt = (n: number) => n.toLocaleString("zh-CN", { maximumFractionDigits: 2 });

export default function PortfolioPage() {
  const [pf, setPf] = useState<Portfolio | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => { api.portfolio().then(setPf).catch((e) => setError(String(e))); }, []);

  if (error) return <main className="p-8 text-red-600">加载失败：{error}</main>;
  if (!pf) return <main className="p-8">加载中…</main>;

  return (
    <main className="p-8 space-y-6">
      <h1 className="text-xl font-bold">持仓与资金</h1>
      <p className="text-sm text-muted-foreground">
        现金 ¥{fmt(pf.account.cash)} · 净投入 ¥{fmt(pf.account.net_contributed)} · 总资产 ¥{fmt(pf.account.total_value)}
      </p>
      {pf.funds.map((f) => (
        <section key={f.code} className="border rounded p-4 space-y-2">
          <div className="flex justify-between items-center">
            <h2 className="font-semibold">{f.name} <span className="text-xs text-muted-foreground">{f.code}</span></h2>
            <div className="text-sm">
              {f.shares} 份 × {f.nav ?? "—"} = <b>¥{fmt(f.value)}</b>（{(f.weight * 100).toFixed(1)}%）
              {f.nav_date && <span className="text-muted-foreground"> · 净值日期 {f.nav_date}</span>}
            </div>
          </div>
          {f.lots.length > 0 ? (
            <table className="w-full text-sm">
              <thead><tr className="text-left text-muted-foreground">
                <th>买入日期</th><th>份额</th><th>持有天数</th><th>当前赎回费率</th>
              </tr></thead>
              <tbody>
                {f.lots.map((lot, i) => (
                  <tr key={i} className={lot.fee_rate > 0 ? "text-red-700" : ""}>
                    <td>{lot.buy_date}</td><td>{lot.shares}</td><td>{lot.holding_days} 天</td>
                    <td>{lot.fee_rate > 0 ? `${(lot.fee_rate * 100).toFixed(2)}%（费用窗口内）` : "0（免费）"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : <p className="text-sm text-muted-foreground">无持仓批次</p>}
        </section>
      ))}
      <p className="text-xs text-muted-foreground">赎回费以销售平台实际持有天数为准；本页费率由 FIFO 批次推算。</p>
    </main>
  );
}
```

- [ ] **Step 2: 全量验证**

Run: `pnpm --dir apps/web build && pnpm --dir apps/web test`
Expected: 构建成功，全部测试通过

- [ ] **Step 3: Commit**

```bash
git add apps/web
git commit -m "feat(web): 持仓与资金页"
```

---

### Task 19: 一键启动 + 文档 + 端到端总验收

**Files:**
- Create: `README.md`
- Create: `pnpm-workspace.yaml`（若 Task 14 未创建）
- Modify: `TESTING.md`
- Modify: `CHANGELOG.md`

**Interfaces:**
- Produces: `pnpm install && pnpm dev` 一条命令拉起 api(8000)+web(3000)；`pnpm test` 跑全部测试

- [ ] **Step 1: 写 README**

```markdown
# Professional-Investment

《四只基金规则化交易与动态仓位管理方案》（docs/product/）的本地执行平台：
每周信号计算（趋势评分/四道闸门/B-S 理由代码）+ 交易日志 + 持仓费用窗口。

## 快速开始

前置：Python ≥3.11 + [uv](https://docs.astral.sh/uv/)、Node ≥20 + pnpm。

\`\`\`bash
pnpm install        # 根依赖（concurrently）
pnpm dev            # 同时启动 quant-api(:8000) 与 web(:3000)
\`\`\`

首次使用：
1. 打开 http://localhost:3000/trades —— 录入一笔 `入金`（如 19044.07）和四只基金的初始 `买入`（份额/净值以销售平台为准）。
2. 打开 http://localhost:3000/signals —— 点"1. 更新净值"（akshare 抓取，含 589210 代理），再点"2. 计算信号"。
3. 每周五净值披露后重复第 2 步；有动作时在下一开放日 15:00 前到场外平台手动下单，随后回"交易日志"补录。

净值抓取失败时：天天基金 App 抄净值 → `POST /api/nav/import`（或找 agent 代为录入）。

## 测试

\`\`\`bash
pnpm test   # quant-core pytest（含 PDF 算例黄金测试）+ quant-api pytest + web vitest
\`\`\`

## 结构

- `packages/quant-core` —— 纯算法库（规则参数唯一来源，禁止 Web/DB 依赖）
- `services/quant-api` —— FastAPI + SQLite（`data/investment.db`，不入库）
- `apps/web` —— Next.js 15 仪表盘/信号/日志/持仓
```

- [ ] **Step 2: 更新 TESTING.md**

```markdown
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
```

- [ ] **Step 3: 更新 CHANGELOG.md**

在 `## [version]` 格式下追加：

```markdown
## [0.1.0] - 2026-08-05
### 功能
- 一期信号仪表盘 + 交易日志：quant-core 算法库（评分/凯利约束/模式/费用）、quant-api（akshare 管道 + 账本 + 信号 API）、web 四页面
### 设计原理
- 算法独立成纯函数包，为后续 agent 平台复用（docs/superpowers/specs/2026-08-05-signal-dashboard-design.md）
### 注意事项
- 一期无 Alembic（create_all）；峰值/利润率历史从首次信号快照开始累积
- P1 单基金移动止盈一期仅在批次层提示，自动判定列入二期
```

- [ ] **Step 4: 端到端验收（手动脚本）**

```bash
# 终端 1
pnpm dev
# 终端 2 依次验证：
curl http://localhost:8000/api/health                      # {"status":"ok"}
curl -X POST http://localhost:3000/api/trades -H "content-type: application/json" \
  -d '{"date":"2026-08-01","direction":"deposit","amount":19044.07}'
curl -X POST http://localhost:3000/api/nav/refresh         # 真实抓取（需网络）
curl -X POST http://localhost:3000/api/signals/compute     # 返回 SignalReport JSON
# 浏览器打开 http://localhost:3000 四个页面目视检查
```

Expected：四页面可打开；信号页给出含理由代码的建议或 N0。

- [ ] **Step 5: 全量测试 + Commit**

Run: `pnpm test`
Expected: 全绿

```bash
git add -A
git commit -m "docs: README/TESTING/CHANGELOG + 一期端到端验收"
git push
```

---

## Self-Review 记录

- **Spec 覆盖**：spec §1 成功标准 1-5 → Task 9/13/16（信号页）、Task 10（黄金测试）、Task 17（日志+持有天数+费用）、Task 12（stale+手动导入）、Task 19（一键启动）。spec §3-8 → Task 2-9（quant-core 模块）、Task 11-13（数据模型/API）、Task 15-18（四页面）、Task 12（错误处理/代理规则）、Task 10+19（测试策略）、Task 2 config dataclass + File Structure（agent 演化预留）。spec §9 非目标未引入任何实现。
- **有意偏差（已披露）**：不用 Alembic（create_all）；trades 表兼任出入金账本；P1 单基金移动止盈一期仅在批次层展示费率窗口，自动判定列入二期（PDF 允许手动核对）。
- **类型一致性**：`FundDecision`/`SignalReport` 字段名在 engine.py（Task 9）、signals router（Task 13 asdict 序列化）、web types.ts（Task 14）三处一致；`account_snapshot` 返回键与 signals/portfolio 路由消费一致。
- **已知风险**：`test_b2_pullback` 的构造序列接受 B1 或 B2（序列同时满足两个条件，实现按 B2 优先）；`seed_navs` 测试辅助函数的 session 获取方式给了两种实现选择（断言不变）。

## 口径披露（Task 19 追记）

- 算例 A 执行合计由 PDF 演示值 2,208 元更正为 1,544 元（长盛 B2 477 + 摩根 B4 1,067）。
- 财通 B4 顺延：每周 2 单元买入预算为 PDF 8.4 的规范性约束，优先于算例的演示算术。
- 广发不动：买入侧死区为 300 元/1.5% 总资产（PDF 8.3）；3pp 死区仅适用于卖出。
- spec §7 测试策略的算例 A 括号口径已同步更正。
