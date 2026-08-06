"""AI 信号解读：LLM 只解释报告已有内容，输出不参与任何计算、不落库。"""
import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import WeeklySignal
from ..settings import get_settings

router = APIRouter(prefix="/api/interpret", tags=["interpret"])

SYSTEM_PROMPT = (
    "你是规则化交易系统的解读员。只解释信号报告中已有的内容，不得给出报告之外的买卖建议。"
    "输出三段：【本周结论】【逐只基金解释】【风险提示】。"
    "用通俗中文；必须使用的术语先解释（如 B2=回撤加仓、闸门=买入前置检查、单元=每周加仓预算单位）。"
)


@router.post("")
def interpret(db: Session = Depends(get_db)):
    row = db.query(WeeklySignal).order_by(WeeklySignal.id.desc()).first()
    if row is None:
        raise HTTPException(404, "尚无信号快照，请先在信号页计算信号")
    cfg = get_settings(db)
    if not cfg["llm_api_key"]:
        raise HTTPException(503, "未配置 API Key，请到设置页填写")
    try:
        resp = httpx.post(
            f"{cfg['llm_base_url'].rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {cfg['llm_api_key']}"},
            json={
                "model": cfg["llm_model"],
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": row.report_json},
                ],
                "temperature": 0.3,
            },
            timeout=60.0,
        )
        resp.raise_for_status()
        text = resp.json()["choices"][0]["message"]["content"]
    except Exception as exc:
        raise HTTPException(502, f"LLM 调用失败: {str(exc)[:200]}")
    return {"text": text, "model": cfg["llm_model"], "as_of": row.as_of.isoformat()}
