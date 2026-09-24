from sqlalchemy.orm import Session

from . import models


NEW_VEHICLE_MILESTONES = [300, *range(1000, 24000, 1000)]


def ensure_maintenance_schedule(db: Session, vehicle):
    if not vehicle or not vehicle.is_new_vehicle:
        return

    db.flush()
    is_member_vehicle = isinstance(vehicle, models.Motor)
    query = db.query(models.NewVehicleMaintenanceRecord)
    if is_member_vehicle:
        existing = query.filter(
            models.NewVehicleMaintenanceRecord.motor_id == vehicle.id
        ).all()
    else:
        existing = query.filter(
            models.NewVehicleMaintenanceRecord.guest_motor_id == vehicle.id
        ).all()

    existing_mileages = {record.target_mileage for record in existing}
    for target_mileage in NEW_VEHICLE_MILESTONES:
        if target_mileage in existing_mileages:
            continue
        db.add(models.NewVehicleMaintenanceRecord(
            motor_id=vehicle.id if is_member_vehicle else None,
            guest_motor_id=None if is_member_vehicle else vehicle.id,
            target_mileage=target_mileage,
        ))


def transfer_guest_schedule(db: Session, guest_motor, member_motor):
    if not guest_motor or not member_motor:
        return

    if guest_motor.is_new_vehicle:
        member_motor.is_new_vehicle = True
        member_motor.purchase_date = member_motor.purchase_date or guest_motor.purchase_date

    existing_mileages = {
        record.target_mileage
        for record in member_motor.new_vehicle_maintenance_records
    }
    for record in list(guest_motor.new_vehicle_maintenance_records):
        if record.target_mileage in existing_mileages:
            continue
        record.motor_id = member_motor.id
        record.guest_motor_id = None
        existing_mileages.add(record.target_mileage)

    ensure_maintenance_schedule(db, member_motor)
