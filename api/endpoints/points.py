from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.dependencies.admin_auth import require_self_or_admin
from db import models
from db.database import get_db
from db.points import get_user_point_summary
from schemas.points import PointSummary

router = APIRouter()


@router.get("/user/{google_id}/summary", response_model=PointSummary, summary="查詢會員點數摘要")
def read_user_point_summary(
    google_id: str,
    auth=Depends(require_self_or_admin),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.google_id == google_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="找不到該會員")

    summary = get_user_point_summary(db, google_id)
    db.commit()
    return summary
