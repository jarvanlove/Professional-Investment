"""LLM 与策略运行时设置：app_settings 表 > 环境变量 > 内置默认。"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.orm import Session

from quant_core.config import FUNDS

from .models import AppSetting

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

DEFAULTS = {
    "llm_api_key": "",
    "llm_base_url": "https://api.deepseek.com",
    "llm_model": "deepseek-v4-pro",
    "llm_provider": "deepseek",
    "deepseek_api_key": "",
    "kimi_api_key": "",
    "minimax_api_key": "",
    "qwen_api_key": "",
    "glm_api_key": "",
    # 策略参数
    "strategy_base_weights": '{"001480":0.08,"025343":0.04,"027521":0.0,"005052":0.10}',
    "strategy_max_sell_ratio": "0.30",
    "strategy_max_buy_ratio": "1.00",
    "strategy_buffer_pp": "0.02",
    "strategy_fee_aversion": "0.005",
    "strategy_confidence_scaling": "1",
}

ENV_MAP = {
    "llm_api_key": "DEEPSEEK_API_KEY",
    "llm_base_url": "DEEPSEEK_BASE_URL",
    "llm_model": "DEEPSEEK_MODEL",
    "llm_provider": "LLM_PROVIDER",
    "deepseek_api_key": "DEEPSEEK_API_KEY",
    "kimi_api_key": "KIMI_API_KEY",
    "minimax_api_key": "MINIMAX_API_KEY",
    "qwen_api_key": "QWEN_API_KEY",
    "glm_api_key": "GLM_API_KEY",
    # 策略参数默认不读环境变量
    "strategy_base_weights": "STRATEGY_BASE_WEIGHTS",
    "strategy_max_sell_ratio": "STRATEGY_MAX_SELL_RATIO",
    "strategy_max_buy_ratio": "STRATEGY_MAX_BUY_RATIO",
    "strategy_buffer_pp": "STRATEGY_BUFFER_PP",
    "strategy_fee_aversion": "STRATEGY_FEE_AVERSION",
    "strategy_confidence_scaling": "STRATEGY_CONFIDENCE_SCALING",
}


@dataclass(frozen=True)
class StrategyConfig:
    base_weights: dict[str, float]
    max_sell_ratio: float
    max_buy_ratio: float
    buffer_pp: float
    fee_aversion: float
    confidence_scaling: bool


def _parse_base_weights(raw: str) -> dict[str, float]:
    try:
        parsed = json.loads(raw)
    except Exception:
        parsed = {}
    out = {}
    default = json.loads(DEFAULTS["strategy_base_weights"])
    for code in FUNDS:
        val = parsed.get(code, default.get(code, 0.0))
        try:
            val = float(val)
        except Exception:
            val = 0.0
        # 底仓不能超过基金 cap
        out[code] = min(max(val, 0.0), FUNDS[code].cap)
    return out


def _clamp_float(raw: str, default: str, lo: float, hi: float) -> float:
    try:
        val = float(raw)
    except Exception:
        val = float(default)
    return max(lo, min(hi, val))


def get_settings(db: Session) -> dict[str, str]:
    rows = {r.key: r.value for r in db.query(AppSetting).all()}
    return {
        k: rows.get(k) or os.environ.get(ENV_MAP[k]) or default
        for k, default in DEFAULTS.items()
    }


def get_strategy_config(db: Session) -> StrategyConfig:
    settings = get_settings(db)
    return StrategyConfig(
        base_weights=_parse_base_weights(settings.get("strategy_base_weights", "{}")),
        max_sell_ratio=_clamp_float(
            settings.get("strategy_max_sell_ratio", ""),
            DEFAULTS["strategy_max_sell_ratio"], 0.01, 1.0,
        ),
        max_buy_ratio=_clamp_float(
            settings.get("strategy_max_buy_ratio", ""),
            DEFAULTS["strategy_max_buy_ratio"], 0.01, 1.0,
        ),
        buffer_pp=_clamp_float(
            settings.get("strategy_buffer_pp", ""),
            DEFAULTS["strategy_buffer_pp"], 0.0, 0.10,
        ),
        fee_aversion=_clamp_float(
            settings.get("strategy_fee_aversion", ""),
            DEFAULTS["strategy_fee_aversion"], 0.0, 0.05,
        ),
        confidence_scaling=settings.get("strategy_confidence_scaling", "1") == "1",
    )


def update_settings(db: Session, updates: dict[str, str]) -> dict[str, str]:
    bad = sorted(set(updates) - set(DEFAULTS))
    if bad:
        raise ValueError(f"未知设置键: {bad}")
    for k, v in updates.items():
        row = db.get(AppSetting, k)
        if row is None:
            db.add(AppSetting(key=k, value=str(v)))
        else:
            row.value = str(v)
    db.commit()
    return get_settings(db)
