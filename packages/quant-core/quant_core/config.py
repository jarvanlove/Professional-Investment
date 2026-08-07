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
        proxy_code="025343",
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
# 买入侧死区（PDF 8.3）：Buy 结果 <300 元或 <总资金 1.5% 不交易；
# 3pp 死区只属于卖出侧（PDF 9.1）与 B4 触发条件（PDF 8.2）
DEADBAND_BUY_TOTAL_PCT = 0.015
MAX_UNITS_PER_WEEK = 2

# 专业量化增强默认参数（用户可在设置页覆盖）
DEFAULT_BASE_WEIGHTS = {"001480": 0.08, "025343": 0.04, "027521": 0.0, "005052": 0.10}
MAX_WEEKLY_SELL_RATIO = 0.30
BUFFER_WEIGHT_DIFF = 0.02
FEE_AVERSION_THRESHOLD = 0.005
CONFIDENCE_FACTORS = {"high": 1.0, "medium": 0.7, "low": 0.4}
DCA_HORIZON_DAYS = 14

# 每个风险子单元的单基金金额上限（PDF 07 章）
UNIT_LIMITS = {
    "15k": {"001480": 663.0, "025343": 477.0, "027521": 352.0, "005052": 1067.0},
    "20k": {"001480": 976.0, "025343": 664.0, "027521": 477.0, "005052": 1380.0},
}
