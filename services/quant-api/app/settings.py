"""LLM 等运行时设置：app_settings 表 > 环境变量 > 内置默认。"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.orm import Session

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
}


def get_settings(db: Session) -> dict[str, str]:
    rows = {r.key: r.value for r in db.query(AppSetting).all()}
    return {
        k: rows.get(k) or os.environ.get(ENV_MAP[k]) or default
        for k, default in DEFAULTS.items()
    }


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
