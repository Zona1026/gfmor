from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session, joinedload

from api.dependencies.admin_auth import require_manager_admin
from db import crud, models
from db.database import get_db
from db.points import get_user_point_summary
from schemas import customer as customer_schema
from schemas import guest_customer as guest_schema

router = APIRouter()


def _enum_value(value):
    return getattr(value, "value", value)


def _service_sort_time(work_order):
    return work_order.completed_at or work_order.scheduled_at or work_order.created_at or datetime.min


def _member_vehicles(user):
    return [
        customer_schema.CustomerVehicle(
            id=motor.id,
            customer_type="member",
            license_plate=motor.license_plate,
            brand=motor.brand,
            model_name=motor.model_name,
            vin=motor.vin,
            mileage=motor.mileage,
            status=motor.status,
        )
        for motor in (user.motors or [])
        if motor.status is None
    ]


def _guest_vehicles(guest):
    return [
        customer_schema.CustomerVehicle(
            id=motor.id,
            customer_type="guest",
            license_plate=motor.license_plate,
            brand=motor.brand,
            model_name=motor.model_name,
            vin=motor.vin,
            mileage=motor.mileage,
            status=motor.status,
        )
        for motor in (guest.motors or [])
        if motor.status is None
    ]


def _work_orders_for_customer(db: Session, customer_type: str, customer_id):
    query = db.query(models.WorkOrder).options(
        joinedload(models.WorkOrder.payments),
        joinedload(models.WorkOrder.guest_motor),
        joinedload(models.WorkOrder.motor),
    )
    if customer_type == "member":
        query = query.filter(models.WorkOrder.google_id == str(customer_id))
    else:
        query = query.filter(models.WorkOrder.guest_customer_id == int(customer_id))
    return query.order_by(models.WorkOrder.created_at.desc()).all()


def _orders_for_customer(db: Session, customer_type: str, customer_id):
    query = db.query(models.Order).options(joinedload(models.Order.items))
    if customer_type == "member":
        query = query.filter(models.Order.google_id == str(customer_id))
    else:
        query = query.filter(models.Order.guest_customer_id == int(customer_id))
    return query.order_by(models.Order.created_at.desc()).all()


def _service_records(work_orders):
    records = []
    for work_order in sorted(work_orders, key=_service_sort_time, reverse=True):
        records.append(customer_schema.CustomerServiceRecord(
            id=work_order.id,
            work_order_id=work_order.id,
            service_type=work_order.service_type,
            status=work_order.status,
            payment_status=work_order.payment_status,
            vehicle_license_plate=work_order.vehicle_license_plate,
            vehicle_model=work_order.vehicle_model,
            responsible_staff=work_order.responsible_staff,
            total_amount=work_order.total_amount or 0,
            scheduled_at=work_order.scheduled_at,
            created_at=work_order.created_at,
            completed_at=work_order.completed_at,
        ))
    return records


def _spending_records(orders, work_orders):
    records = []
    for order in orders:
        records.append(customer_schema.CustomerSpendingRecord(
            id=f"order-{order.id}",
            source="order",
            source_id=order.id,
            source_label=f"商城訂單 #{order.id}",
            amount=order.total_amount or 0,
            status=_enum_value(order.status),
            method=None,
            paid_at=None,
            created_at=order.created_at,
        ))

    for work_order in work_orders:
        for payment in sorted(work_order.payments or [], key=lambda item: item.paid_at or datetime.min, reverse=True):
            records.append(customer_schema.CustomerSpendingRecord(
                id=f"work-order-payment-{payment.id}",
                source="work_order_payment",
                source_id=work_order.id,
                source_label=f"工單 #{work_order.id}",
                amount=payment.amount or 0,
                status=_enum_value(work_order.payment_status),
                method=payment.method,
                paid_at=payment.paid_at,
                created_at=payment.paid_at,
            ))

    return sorted(records, key=lambda item: item.paid_at or item.created_at or datetime.min, reverse=True)


def _cumulative_spending(orders, work_orders):
    paid_order_total = sum(
        order.total_amount or 0
        for order in orders
        if order.status in [models.OrderStatus.COMPLETED, models.OrderStatus.FULL_PAID]
    )
    work_order_payment_total = sum(
        payment.amount or 0
        for work_order in work_orders
        for payment in (work_order.payments or [])
    )
    return paid_order_total + work_order_payment_total


def _latest_service_at(work_orders):
    if not work_orders:
        return None
    return max(_service_sort_time(work_order) for work_order in work_orders)


def _vehicle_label(vehicles):
    if not vehicles:
        return None
    first = vehicles[0]
    if len(vehicles) == 1:
        return first.license_plate
    return f"{first.license_plate} 等 {len(vehicles)} 台"


def _member_summary(db: Session, user, include_detail: bool = False):
    vehicles = _member_vehicles(user)
    work_orders = _work_orders_for_customer(db, "member", user.google_id)
    orders = _orders_for_customer(db, "member", user.google_id)
    points = get_user_point_summary(db, user.google_id)
    base = {
        "customer_type": "member",
        "customer_id": user.google_id,
        "name": user.name,
        "phone": user.phone,
        "email": user.email,
        "joined_at": user.join_time,
        "vehicle_count": len(vehicles),
        "vehicle_label": _vehicle_label(vehicles),
        "latest_service_at": _latest_service_at(work_orders),
        "cumulative_spending": _cumulative_spending(orders, work_orders),
        "current_points": points["current_points"],
        "expiring_soon_points": points["expiring_soon_points"],
        "has_notes": bool(user.admin_notes),
    }
    if not include_detail:
        return customer_schema.CustomerSummary(**base)
    return customer_schema.CustomerDetail(
        **base,
        notes=user.admin_notes,
        vehicles=vehicles,
        service_records=_service_records(work_orders),
        spending_records=_spending_records(orders, work_orders),
    )


def _guest_summary(db: Session, guest, include_detail: bool = False):
    vehicles = _guest_vehicles(guest)
    work_orders = _work_orders_for_customer(db, "guest", guest.id)
    orders = _orders_for_customer(db, "guest", guest.id)
    base = {
        "customer_type": "guest",
        "customer_id": str(guest.id),
        "name": guest.name,
        "phone": guest.phone,
        "email": None,
        "joined_at": guest.created_at,
        "vehicle_count": len(vehicles),
        "vehicle_label": _vehicle_label(vehicles),
        "latest_service_at": _latest_service_at(work_orders),
        "cumulative_spending": _cumulative_spending(orders, work_orders),
        "current_points": 0,
        "expiring_soon_points": 0,
        "has_notes": bool(guest.notes),
    }
    if not include_detail:
        return customer_schema.CustomerSummary(**base)
    return customer_schema.CustomerDetail(
        **base,
        notes=guest.notes,
        vehicles=vehicles,
        service_records=_service_records(work_orders),
        spending_records=_spending_records(orders, work_orders),
    )


@router.get("/", response_model=List[customer_schema.CustomerSummary], summary="取得客戶 / 會員列表")
def read_customers(
    q: Optional[str] = None,
    customer_type: str = Query("all", alias="type"),
    skip: int = 0,
    limit: int = 200,
    admin=Depends(require_manager_admin),
    db: Session = Depends(get_db),
):
    if customer_type not in ["all", "member", "guest"]:
        raise HTTPException(status_code=400, detail="type 僅支援 all、member、guest")

    customers = []
    keyword = f"%{q.strip()}%" if q and q.strip() else None

    if customer_type in ["all", "member"]:
        member_query = (
            db.query(models.User)
            .options(joinedload(models.User.motors))
            .outerjoin(
                models.Motor,
                and_(models.User.google_id == models.Motor.google_id, models.Motor.status.is_(None)),
            )
            .filter(models.User.google_id != "system")
        )
        if keyword:
            member_query = member_query.filter(or_(
                models.User.name.ilike(keyword),
                models.User.phone.ilike(keyword),
                models.User.email.ilike(keyword),
                models.Motor.license_plate.ilike(keyword),
            ))
        for user in member_query.distinct().all():
            customers.append(_member_summary(db, user))

    if customer_type in ["all", "guest"]:
        guest_query = (
            db.query(models.GuestCustomer)
            .options(joinedload(models.GuestCustomer.motors))
            .outerjoin(
                models.GuestMotor,
                and_(models.GuestCustomer.id == models.GuestMotor.guest_customer_id, models.GuestMotor.status.is_(None)),
            )
        )
        if keyword:
            guest_query = guest_query.filter(or_(
                models.GuestCustomer.name.ilike(keyword),
                models.GuestCustomer.phone.ilike(keyword),
                models.GuestMotor.license_plate.ilike(keyword),
            ))
        for guest in guest_query.distinct().all():
            customers.append(_guest_summary(db, guest))

    customers.sort(key=lambda item: item.latest_service_at or item.joined_at or datetime.min, reverse=True)
    return customers[skip: skip + limit]


@router.get("/{customer_type}/{customer_id}", response_model=customer_schema.CustomerDetail, summary="取得客戶 / 會員詳情")
def read_customer_detail(
    customer_type: str,
    customer_id: str,
    admin=Depends(require_manager_admin),
    db: Session = Depends(get_db),
):
    if customer_type == "member":
        user = (
            db.query(models.User)
            .options(joinedload(models.User.motors))
            .filter(models.User.google_id == customer_id)
            .first()
        )
        if not user:
            raise HTTPException(status_code=404, detail="找不到該會員")
        return _member_summary(db, user, include_detail=True)

    if customer_type == "guest":
        try:
            guest_id = int(customer_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="散客 ID 格式錯誤")
        guest = (
            db.query(models.GuestCustomer)
            .options(joinedload(models.GuestCustomer.motors))
            .filter(models.GuestCustomer.id == guest_id)
            .first()
        )
        if not guest:
            raise HTTPException(status_code=404, detail="找不到該散客")
        return _guest_summary(db, guest, include_detail=True)

    raise HTTPException(status_code=400, detail="customer_type 僅支援 member 或 guest")


@router.post("/guest/{guest_id}/motors", response_model=guest_schema.GuestMotor, summary="新增散客車輛")
def create_guest_motor(
    guest_id: int,
    motor_in: guest_schema.GuestMotorCreate,
    admin=Depends(require_manager_admin),
    db: Session = Depends(get_db),
):
    try:
        db_motor = crud.create_guest_motor(db, guest_id=guest_id, motor_in=motor_in)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not db_motor:
        raise HTTPException(status_code=404, detail="找不到該散客")
    return db_motor


@router.put("/guest/{guest_id}/motors/{motor_id}", response_model=guest_schema.GuestMotor, summary="更新散客車輛")
def update_guest_motor(
    guest_id: int,
    motor_id: int,
    motor_in: guest_schema.GuestMotorUpdate,
    admin=Depends(require_manager_admin),
    db: Session = Depends(get_db),
):
    db_motor = crud.get_guest_motor(db, guest_motor_id=motor_id)
    if not db_motor or db_motor.guest_customer_id != guest_id:
        raise HTTPException(status_code=404, detail="找不到該散客車輛")
    updated_motor = crud.update_guest_motor(db, guest_motor_id=motor_id, motor_update=motor_in)
    return updated_motor
