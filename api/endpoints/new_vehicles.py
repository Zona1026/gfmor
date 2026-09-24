from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from api.dependencies.admin_auth import require_admin, require_manager_admin
from db import models
from db.database import get_db
from db.new_vehicle import ensure_maintenance_schedule
from schemas.new_vehicle import (
    NewVehicleMaintenanceRecord,
    NewVehicleMaintenanceRecordUpdate,
    NewVehicleProfile,
)


router = APIRouter()


def _member_profile(vehicle):
    return NewVehicleProfile(
        vehicle_type="member",
        vehicle_id=vehicle.id,
        customer_id=vehicle.google_id,
        customer_name=vehicle.owner.name,
        customer_phone=vehicle.owner.phone,
        license_plate=vehicle.license_plate,
        brand=vehicle.brand,
        model_name=vehicle.model_name,
        vin=vehicle.vin,
        purchase_date=vehicle.purchase_date,
        current_mileage=vehicle.mileage,
        records=vehicle.new_vehicle_maintenance_records,
    )


def _guest_profile(vehicle):
    return NewVehicleProfile(
        vehicle_type="guest",
        vehicle_id=vehicle.id,
        customer_id=str(vehicle.guest_customer_id),
        customer_name=vehicle.guest_customer.name,
        customer_phone=vehicle.guest_customer.phone,
        license_plate=vehicle.license_plate,
        brand=vehicle.brand,
        model_name=vehicle.model_name,
        vin=vehicle.vin,
        purchase_date=vehicle.purchase_date,
        current_mileage=vehicle.mileage,
        records=vehicle.new_vehicle_maintenance_records,
    )


@router.get("/", response_model=List[NewVehicleProfile], summary="讀取新車保養名冊")
def read_new_vehicle_profiles(
    q: Optional[str] = Query(None, max_length=100),
    admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    member_query = (
        db.query(models.Motor)
        .options(
            joinedload(models.Motor.owner),
            joinedload(models.Motor.new_vehicle_maintenance_records),
        )
        .filter(
            models.Motor.is_new_vehicle.is_(True),
            models.Motor.status.is_(None),
        )
    )
    guest_query = (
        db.query(models.GuestMotor)
        .options(
            joinedload(models.GuestMotor.guest_customer),
            joinedload(models.GuestMotor.new_vehicle_maintenance_records),
        )
        .filter(
            models.GuestMotor.is_new_vehicle.is_(True),
            models.GuestMotor.status.is_(None),
        )
    )

    keyword = (q or "").strip()
    if keyword:
        pattern = f"%{keyword}%"
        member_query = member_query.join(models.Motor.owner).filter(or_(
            models.Motor.license_plate.ilike(pattern),
            models.Motor.model_name.ilike(pattern),
            models.User.name.ilike(pattern),
            models.User.phone.ilike(pattern),
        ))
        guest_query = guest_query.join(models.GuestMotor.guest_customer).filter(or_(
            models.GuestMotor.license_plate.ilike(pattern),
            models.GuestMotor.model_name.ilike(pattern),
            models.GuestCustomer.name.ilike(pattern),
            models.GuestCustomer.phone.ilike(pattern),
        ))

    member_vehicles = member_query.all()
    guest_vehicles = guest_query.all()
    for vehicle in [*member_vehicles, *guest_vehicles]:
        ensure_maintenance_schedule(db, vehicle)
    db.commit()

    profiles = [*map(_member_profile, member_vehicles), *map(_guest_profile, guest_vehicles)]
    return sorted(profiles, key=lambda profile: (profile.customer_name, profile.license_plate))


@router.put(
    "/{vehicle_type}/{vehicle_id}/records/{record_id}",
    response_model=NewVehicleMaintenanceRecord,
    summary="更新新車保養紀錄",
)
def update_new_vehicle_maintenance_record(
    vehicle_type: str,
    vehicle_id: int,
    record_id: int,
    payload: NewVehicleMaintenanceRecordUpdate,
    admin=Depends(require_manager_admin),
    db: Session = Depends(get_db),
):
    record = db.query(models.NewVehicleMaintenanceRecord).filter(
        models.NewVehicleMaintenanceRecord.id == record_id
    ).first()
    expected_vehicle_id = record.motor_id if vehicle_type == "member" and record else (
        record.guest_motor_id if vehicle_type == "guest" and record else None
    )
    if vehicle_type not in {"member", "guest"} or not record or expected_vehicle_id != vehicle_id:
        raise HTTPException(status_code=404, detail="找不到該新車保養紀錄")

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(record, key, value)

    db.add(record)
    db.commit()
    db.refresh(record)
    return record
