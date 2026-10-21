from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from api.dependencies.admin_auth import require_admin
from db.database import get_db
from db.models import AccidentEstimate
from schemas.accident_estimate import AccidentEstimate as EstimateResponse, AccidentEstimateInput


router = APIRouter(dependencies=[Depends(require_admin)])


def find_estimate(db: Session, estimate_id: int):
    estimate = db.get(AccidentEstimate, estimate_id)
    if estimate is None:
        raise HTTPException(404, "找不到車禍估價單")
    return estimate


@router.get("/", response_model=list[EstimateResponse])
def list_estimates(q: str = "", skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db)):
    query = db.query(AccidentEstimate)
    if q.strip():
        term = q.strip()
        query = query.filter(or_(
            AccidentEstimate.customer_name.contains(term, autoescape=True),
            AccidentEstimate.license_plate.contains(term, autoescape=True),
            AccidentEstimate.phone.contains(term, autoescape=True),
        ))
    return query.order_by(AccidentEstimate.id.desc()).offset(skip).limit(limit).all()


@router.get("/{estimate_id}", response_model=EstimateResponse)
def read_estimate(estimate_id: int, db: Session = Depends(get_db)):
    return find_estimate(db, estimate_id)


@router.post("/", response_model=EstimateResponse, status_code=201)
def create_estimate(data: AccidentEstimateInput, db: Session = Depends(get_db)):
    # Computed subtotals/totals are never trusted or persisted from the client.
    estimate = AccidentEstimate(**data.model_dump(exclude_computed_fields=True))
    db.add(estimate)
    db.commit()
    db.refresh(estimate)
    return estimate


@router.put("/{estimate_id}", response_model=EstimateResponse)
def update_estimate(estimate_id: int, data: AccidentEstimateInput, db: Session = Depends(get_db)):
    estimate = find_estimate(db, estimate_id)
    for key, value in data.model_dump(exclude_computed_fields=True).items():
        setattr(estimate, key, value)
    db.commit()
    db.refresh(estimate)
    return estimate
