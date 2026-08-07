from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.dependencies.admin_auth import require_admin, require_super_admin
from db import accounting as accounting_service
from db import models
from db.database import get_db
from schemas import accounting as accounting_schema

router = APIRouter()


@router.get("/receipts", response_model=List[accounting_schema.PaymentRecord])
def read_receipts(
    skip: int = 0,
    limit: int = 200,
    admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    return accounting_service.get_receipts(db, skip=skip, limit=limit)


@router.get("/refunds", response_model=List[accounting_schema.RefundRecord])
def read_refunds(
    skip: int = 0,
    limit: int = 200,
    admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    return accounting_service.get_refunds(db, skip=skip, limit=limit)


@router.get("/shop-receivables", response_model=List[accounting_schema.ShopReceivable])
def read_shop_receivables(
    skip: int = 0,
    limit: int = 200,
    admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    return accounting_service.get_shop_receivables(db, skip=skip, limit=limit)


@router.post("/refunds", response_model=accounting_schema.RefundRecord, status_code=status.HTTP_201_CREATED)
def create_refund(
    refund: accounting_schema.RefundCreate,
    db: Session = Depends(get_db),
    admin=Depends(require_super_admin),
):
    if not refund.actor:
        refund.actor = admin["username"] or admin["role"]
    try:
        record = accounting_service.create_refund(db, refund)
        db.commit()
        db.refresh(record)
        return record
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/payables", response_model=List[accounting_schema.Payable])
def read_payables(
    skip: int = 0,
    limit: int = 200,
    admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    return accounting_service.get_payables(db, skip=skip, limit=limit)


@router.post("/payables", response_model=accounting_schema.Payable, status_code=status.HTTP_201_CREATED)
def create_payable(
    payable: accounting_schema.PayableCreate,
    admin=Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    try:
        db_payable = accounting_service.create_payable(db, payable)
        db.commit()
        db.refresh(db_payable)
        return db_payable
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/payables/{payable_id}/payments", response_model=accounting_schema.Payable)
def create_payable_payment(
    payable_id: int,
    payment: accounting_schema.PayablePaymentCreate,
    admin=Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    db_payable = db.query(models.Payable).filter(models.Payable.id == payable_id).first()
    if not db_payable:
        raise HTTPException(status_code=404, detail="Payable not found.")
    try:
        accounting_service.add_payable_payment(db, db_payable, payment)
        db.commit()
        db.refresh(db_payable)
        return db_payable
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
