from sqlalchemy.orm import Session, joinedload

from db import inventory as inventory_service
from db import models


OPEN_REQUEST_STATUSES = [
    models.PurchaseRequestStatus.PENDING_ORDER,
    models.PurchaseRequestStatus.ORDERED,
    models.PurchaseRequestStatus.PARTIAL_ARRIVED,
    models.PurchaseRequestStatus.ARRIVED_PENDING_ASSIGNMENT,
]


def purchase_request_options():
    return [
        joinedload(models.PurchaseRequest.product),
        joinedload(models.PurchaseRequest.work_order),
        joinedload(models.PurchaseRequest.work_order_line_item),
        joinedload(models.PurchaseRequest.receipts),
        joinedload(models.PurchaseRequest.assignments),
    ]


def get_purchase_requests(db: Session, status: str = None, skip: int = 0, limit: int = 200):
    query = db.query(models.PurchaseRequest).options(*purchase_request_options())
    statuses = _status_filter(status)
    if statuses:
        query = query.filter(models.PurchaseRequest.status.in_(statuses))
    return (
        query
        .order_by(
            models.PurchaseRequest.expected_arrival_date.asc(),
            models.PurchaseRequest.created_at.asc(),
            models.PurchaseRequest.id.asc(),
        )
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_purchase_request(db: Session, purchase_request_id: int):
    return (
        db.query(models.PurchaseRequest)
        .options(*purchase_request_options())
        .filter(models.PurchaseRequest.id == purchase_request_id)
        .first()
    )


def _status_filter(status: str):
    if not status:
        return None
    aliases = {
        "pending-order": [models.PurchaseRequestStatus.PENDING_ORDER],
        "awaiting-arrival": [
            models.PurchaseRequestStatus.ORDERED,
            models.PurchaseRequestStatus.PARTIAL_ARRIVED,
        ],
        "partial-arrived": [models.PurchaseRequestStatus.PARTIAL_ARRIVED],
        "pending-assignment": [models.PurchaseRequestStatus.ARRIVED_PENDING_ASSIGNMENT],
        "assigned": [models.PurchaseRequestStatus.ASSIGNED_TO_WORK_ORDER],
        "canceled": [models.PurchaseRequestStatus.CANCELED],
    }
    if status in aliases:
        return aliases[status]
    try:
        return [models.PurchaseRequestStatus(status)]
    except ValueError:
        raise ValueError("Invalid purchase request status.")


def _open_request_for_line_item(db: Session, line_item):
    return (
        db.query(models.PurchaseRequest)
        .filter(
            models.PurchaseRequest.work_order_line_item_id == line_item.id,
            models.PurchaseRequest.product_id == line_item.product_id,
            models.PurchaseRequest.status.in_(OPEN_REQUEST_STATUSES),
        )
        .order_by(models.PurchaseRequest.id.desc())
        .first()
    )


def _sync_status(request):
    if request.status == models.PurchaseRequestStatus.CANCELED:
        return request.status
    if (request.assigned_quantity or 0) >= (request.requested_quantity or 0):
        request.status = models.PurchaseRequestStatus.ASSIGNED_TO_WORK_ORDER
    elif request.unassigned_arrived_quantity > 0:
        request.status = models.PurchaseRequestStatus.ARRIVED_PENDING_ASSIGNMENT
    elif (request.arrived_quantity or 0) > 0:
        request.status = models.PurchaseRequestStatus.PARTIAL_ARRIVED
    elif (request.ordered_quantity or 0) > 0:
        request.status = models.PurchaseRequestStatus.ORDERED
    else:
        request.status = models.PurchaseRequestStatus.PENDING_ORDER
    return request.status


def _remaining_needed(line_item):
    return max(
        0,
        (line_item.quantity or 0)
        - (line_item.inventory_consumed_quantity or 0)
        - inventory_service.work_order_line_item_reserved_quantity(line_item_session(line_item), line_item),
    )


def line_item_session(line_item):
    from sqlalchemy.orm import object_session

    session = object_session(line_item)
    if session is None:
        raise ValueError("Line item is not attached to a database session.")
    return session


def sync_line_item_supply(db: Session, line_item, actor: str = None):
    if line_item.type != models.WorkOrderLineItemType.PART:
        return 0
    if not line_item.product_id or not line_item.product:
        return 0
    if not line_item.is_confirmed:
        return 0

    db.flush()
    consumed = line_item.inventory_consumed_quantity or 0
    required_remaining = max(0, (line_item.quantity or 0) - consumed)
    current_reserved = inventory_service.work_order_line_item_reserved_quantity(db, line_item)

    if current_reserved > required_remaining:
        inventory_service.reserve_work_order_line_item(db, line_item, required_remaining, actor=actor)
        current_reserved = required_remaining

    missing_before_purchase = max(0, required_remaining - current_reserved)
    if missing_before_purchase > 0:
        available = inventory_service.available_stock(db, line_item.product)
        reserve_quantity = min(available, missing_before_purchase)
        if reserve_quantity > 0:
            inventory_service.reserve_work_order_line_item(
                db,
                line_item,
                current_reserved + reserve_quantity,
                actor=actor,
            )
            current_reserved += reserve_quantity

    line_item.inventory_reserved_quantity = current_reserved
    shortage_quantity = max(0, required_remaining - current_reserved)
    _sync_line_item_purchase_request(db, line_item, shortage_quantity)
    return shortage_quantity


def _sync_line_item_purchase_request(db: Session, line_item, shortage_quantity: int):
    request = _open_request_for_line_item(db, line_item)
    if shortage_quantity <= 0:
        if request and not any([request.ordered_quantity, request.arrived_quantity, request.assigned_quantity]):
            request.status = models.PurchaseRequestStatus.CANCELED
        return request

    target_requested = shortage_quantity
    if request:
        target_requested += request.assigned_quantity or 0
        target_requested = max(
            target_requested,
            request.ordered_quantity or 0,
            request.arrived_quantity or 0,
            request.assigned_quantity or 0,
        )
        request.requested_quantity = target_requested
        request.item_name = line_item.name
        request.customer_name = line_item.work_order.customer_name if line_item.work_order else request.customer_name
        request.customer_phone = line_item.work_order.customer_phone if line_item.work_order else request.customer_phone
        request.vehicle_license_plate = (
            line_item.work_order.vehicle_license_plate if line_item.work_order else request.vehicle_license_plate
        )
        _sync_status(request)
        return request

    work_order = line_item.work_order
    request = models.PurchaseRequest(
        product_id=line_item.product_id,
        work_order_id=line_item.work_order_id,
        work_order_line_item_id=line_item.id,
        item_name=line_item.name,
        customer_name=work_order.customer_name if work_order else None,
        customer_phone=work_order.customer_phone if work_order else None,
        vehicle_license_plate=work_order.vehicle_license_plate if work_order else None,
        requested_quantity=shortage_quantity,
        responsible_staff=work_order.responsible_staff if work_order else None,
    )
    db.add(request)
    return request


def consume_ready_line_item_supply(db: Session, line_item, actor: str = None):
    sync_line_item_supply(db, line_item, actor=actor)
    return inventory_service.consume_work_order_line_item(db, line_item, actor=actor)


def order_purchase_request(db: Session, request, update):
    if request.status == models.PurchaseRequestStatus.CANCELED:
        raise ValueError("Canceled purchase request cannot be ordered.")
    if update.supplier_name is not None:
        request.supplier_name = update.supplier_name
    if update.expected_arrival_date is not None:
        request.expected_arrival_date = update.expected_arrival_date
    if update.responsible_staff is not None:
        request.responsible_staff = update.responsible_staff
    if update.note is not None:
        request.note = update.note
    request.ordered_quantity = update.ordered_quantity or request.requested_quantity
    _sync_status(request)
    return request


def receive_purchase_request(db: Session, request, receipt):
    if request.status == models.PurchaseRequestStatus.CANCELED:
        raise ValueError("Canceled purchase request cannot receive items.")
    product = request.product
    if not product:
        raise ValueError("Purchase request product not found.")

    inventory_service.receive_inventory(
        db,
        product,
        receipt.quantity,
        inventory_service.SOURCE_PURCHASE_REQUEST,
        request.id,
        actor=receipt.actor,
        reason=f"Purchase request #{request.id} received",
    )
    db_receipt = models.PurchaseReceipt(
        purchase_request_id=request.id,
        quantity=receipt.quantity,
        actor=receipt.actor,
        note=receipt.note,
    )
    db.add(db_receipt)
    request.arrived_quantity = (request.arrived_quantity or 0) + receipt.quantity

    auto_assign_quantity = min(receipt.quantity, max(0, (request.requested_quantity or 0) - (request.assigned_quantity or 0)))
    line_item = request.work_order_line_item
    if auto_assign_quantity > 0 and _can_assign_to_line_item(request, line_item):
        assign_arrived_quantity(
            db,
            request,
            line_item.work_order,
            line_item,
            auto_assign_quantity,
            actor=receipt.actor,
            note="Auto assigned to source work order",
        )

    _sync_status(request)
    return request


def _can_assign_to_line_item(request, line_item):
    if not line_item:
        return False
    if line_item.product_id != request.product_id:
        return False
    if not line_item.work_order:
        return False
    if line_item.work_order.status == models.WorkOrderStatus.CANCELED:
        return False
    return True


def assign_arrived_quantity(db: Session, request, work_order, line_item, quantity: int, actor: str = None, note: str = None):
    if request.status == models.PurchaseRequestStatus.CANCELED:
        raise ValueError("Canceled purchase request cannot be assigned.")
    if quantity <= 0:
        raise ValueError("Assigned quantity must be greater than 0.")
    if quantity > request.unassigned_arrived_quantity:
        raise ValueError("Assigned quantity exceeds unassigned arrived quantity.")
    if line_item.work_order_id != work_order.id:
        raise ValueError("Line item does not belong to target work order.")
    if line_item.product_id != request.product_id:
        raise ValueError("Target line item product does not match purchase request product.")
    if work_order.status == models.WorkOrderStatus.CANCELED:
        raise ValueError("Canceled work order cannot receive assigned items.")

    current_reserved = inventory_service.work_order_line_item_reserved_quantity(db, line_item)
    consumed = line_item.inventory_consumed_quantity or 0
    remaining_need = max(0, (line_item.quantity or 0) - consumed - current_reserved)
    assign_quantity = min(quantity, remaining_need)
    if assign_quantity <= 0:
        raise ValueError("Target line item does not need more inventory.")

    inventory_service.reserve_work_order_line_item(
        db,
        line_item,
        current_reserved + assign_quantity,
        actor=actor,
    )

    request.assigned_quantity = (request.assigned_quantity or 0) + assign_quantity
    db.add(models.PurchaseAssignment(
        purchase_request_id=request.id,
        work_order_id=work_order.id,
        work_order_line_item_id=line_item.id,
        quantity=assign_quantity,
        actor=actor,
        note=note,
    ))
    _sync_status(request)
    return request


def cancel_purchase_request(db: Session, request, cancel):
    if request.assigned_quantity:
        raise ValueError("Purchase request with assigned items cannot be canceled.")
    if request.unassigned_arrived_quantity:
        raise ValueError("Arrived items must be assigned before canceling the purchase request.")
    request.status = models.PurchaseRequestStatus.CANCELED
    if cancel.note:
        request.note = cancel.note
    return request
