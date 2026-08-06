from fastapi import APIRouter, Depends, HTTPException
import httpx
from sqlalchemy.orm import Session

from ..db import get_db
from ..settings import get_settings, update_settings

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("")
def read_settings(db: Session = Depends(get_db)):
    return get_settings(db)


@router.put("")
def put_settings(payload: dict[str, str], db: Session = Depends(get_db)):
    try:
        return update_settings(db, payload)
    except ValueError as exc:
        raise HTTPException(422, str(exc))


@router.get("/models")
def list_models(db: Session = Depends(get_db)):
    """根据已保存的 LLM 配置，从供应商 /models 接口实时获取可用模型列表。"""
    cfg = get_settings(db)
    if not cfg["llm_api_key"]:
        raise HTTPException(503, "未配置 API Key，请到设置页填写")
    try:
        resp = httpx.get(
            f"{cfg['llm_base_url'].rstrip('/')}/models",
            headers={"Authorization": f"Bearer {cfg['llm_api_key']}"},
            timeout=15.0,
        )
        resp.raise_for_status()
        data = resp.json()
        models = [m["id"] for m in data.get("data", []) if isinstance(m, dict) and "id" in m]
    except Exception as exc:
        raise HTTPException(502, f"获取模型列表失败: {str(exc)[:200]}")
    return {"models": models}
