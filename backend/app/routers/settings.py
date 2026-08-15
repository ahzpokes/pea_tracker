from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from .. import models, schemas

router = APIRouter(tags=["Settings"])

MASK_KEYS = {"GEMINI_API_KEY", "NVIDIA_API_KEY"}


def _mask(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 4:
        return "••••"
    return "••••" + value[-4:]


@router.get("/settings", response_model=List[schemas.SettingResponse])
def get_settings(db: Session = Depends(get_db)):
    settings = db.query(models.Setting).order_by(models.Setting.setting_key).all()
    result = []
    for s in settings:
        val = s.setting_value
        if s.setting_key in MASK_KEYS and val:
            val = _mask(val)
        result.append({
            "setting_key": s.setting_key,
            "setting_value": val,
            "updated_at": s.updated_at
        })
    return result


@router.patch("/settings", response_model=List[schemas.SettingResponse])
def update_settings(
    payload: List[schemas.SettingUpdate],
    db: Session = Depends(get_db)
):
    updated = []
    for item in payload:
        setting = db.query(models.Setting).filter(
            models.Setting.setting_key == item.setting_key
        ).first()
        if setting:
            setting.setting_value = item.setting_value
        else:
            setting = models.Setting(
                setting_key=item.setting_key,
                setting_value=item.setting_value
            )
            db.add(setting)
        updated.append(setting)
    db.commit()
    for s in updated:
        db.refresh(s)
    return updated