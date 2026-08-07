"""Baseline current schema.

This migration replaces the historical startup-time schema patching in main.py.
It is intentionally defensive: it creates missing tables from the current ORM
metadata, then applies idempotent fixups for databases that were created before
the current schema existed.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text

from db.models import Base


revision = "20260707_0001"
down_revision = None
branch_labels = None
depends_on = None


def _inspector(conn):
    return inspect(conn)


def _tables(conn):
    return set(_inspector(conn).get_table_names())


def _columns(conn, table_name):
    if table_name not in _tables(conn):
        return {}
    return {column["name"]: column for column in _inspector(conn).get_columns(table_name)}


def _has_column(conn, table_name, column_name):
    return column_name in _columns(conn, table_name)


def _dialect(conn):
    return conn.dialect.name


def _execute(conn, sql, params=None):
    conn.execute(text(sql), params or {})


def _add_column(conn, table_name, column_name, ddl):
    if table_name in _tables(conn) and not _has_column(conn, table_name, column_name):
        _execute(conn, f"ALTER TABLE {table_name} ADD COLUMN {ddl}")
        return True
    return False


def _quote(name):
    return f"`{name}`"


def _sync_legacy_portfolio_table(conn):
    if "portfolio_items" not in _tables(conn):
        return
    columns = _columns(conn, "portfolio_items")
    if "title" in columns and "標題" not in columns:
        return

    # This mirrors the old startup behavior. The legacy table used incompatible
    # Chinese column names and no stable mapping for the current API contract.
    _execute(conn, "DROP TABLE IF EXISTS portfolio_items")


def _create_missing_tables(conn):
    _sync_legacy_portfolio_table(conn)
    Base.metadata.create_all(bind=conn)


def _migrate_guest_orders(conn):
    if "orders" not in _tables(conn):
        return

    _add_column(conn, "orders", "guest_customer_id", "guest_customer_id INTEGER NULL")

    columns = _columns(conn, "orders")
    google_id_col = columns.get("google_id")
    if google_id_col and google_id_col.get("nullable", True):
        return

    if _dialect(conn) in ("mysql", "mariadb"):
        _execute(conn, "ALTER TABLE orders MODIFY google_id VARCHAR(255) NULL")
    elif _dialect(conn) == "sqlite":
        with op.batch_alter_table("orders") as batch_op:
            batch_op.alter_column(
                "google_id",
                existing_type=sa.String(length=255),
                nullable=True,
            )


def _migrate_order_item_status(conn):
    if "order_items" not in _tables(conn) or _has_column(conn, "order_items", "status"):
        return

    if _dialect(conn) in ("mysql", "mariadb"):
        _execute(conn, """
            ALTER TABLE order_items
            ADD COLUMN status ENUM(
                'NOT_ORDERED',
                'ORDERED',
                'ARRIVED_NEED_NOTIFY',
                'NOTIFIED',
                'COMPLETED'
            ) NOT NULL DEFAULT 'NOT_ORDERED'
        """)
    else:
        _execute(conn, "ALTER TABLE order_items ADD COLUMN status VARCHAR(30) NOT NULL DEFAULT 'NOT_ORDERED'")


def _migrate_booking_status_enum(conn):
    if _dialect(conn) not in ("mysql", "mariadb") or "bookings" not in _tables(conn):
        return

    columns = _columns(conn, "bookings")
    status_column = "狀態" if "狀態" in columns else "status" if "status" in columns else None
    if not status_column:
        return

    required_statuses = [
        "PENDING",
        "CONFIRMED",
        "ARRIVED",
        "CONVERTED_TO_WORK_ORDER",
        "CANCELED",
        "NO_SHOW",
        "TIMEOUT",
        "COMPLETED",
        "SYSTEM_OPEN",
        "SYSTEM_CLOSED",
    ]
    existing_type = str(columns[status_column].get("type", ""))
    if all(status in existing_type for status in required_statuses):
        return

    _execute(conn, f"""
        ALTER TABLE bookings
        MODIFY {_quote(status_column)} ENUM(
            {", ".join(repr(status) for status in required_statuses)}
        ) NOT NULL
    """)


def _migrate_work_orders_core(conn):
    if "work_orders" not in _tables(conn):
        return

    required_statuses = [
        "PENDING",
        "INSPECTION_PENDING",
        "QUOTE_PENDING",
        "CUSTOMER_CONFIRMATION_PENDING",
        "SUPERVISOR_APPROVAL_PENDING",
        "IN_PROGRESS",
        "AWAITING_PAYMENT",
        "COMPLETED",
        "CANCELED",
    ]
    columns = _columns(conn, "work_orders")
    dialect = _dialect(conn)

    if dialect in ("mysql", "mariadb"):
        status_col = columns.get("status")
        if status_col and not all(item in str(status_col.get("type", "")) for item in required_statuses):
            _execute(conn, f"""
                ALTER TABLE work_orders
                MODIFY status ENUM({", ".join(repr(item) for item in required_statuses)})
                NOT NULL DEFAULT 'INSPECTION_PENDING'
            """)
        booking_col = columns.get("booking_id")
        if booking_col and not booking_col.get("nullable", True):
            _execute(conn, "ALTER TABLE work_orders MODIFY booking_id INTEGER NULL")
    elif dialect == "sqlite":
        booking_col = columns.get("booking_id")
        if booking_col and not booking_col.get("nullable", True):
            with op.batch_alter_table("work_orders") as batch_op:
                batch_op.alter_column(
                    "booking_id",
                    existing_type=sa.Integer(),
                    nullable=True,
                )

    enum_type = "ENUM('REPAIR','MAINTENANCE','MODIFICATION')" if dialect in ("mysql", "mariadb") else "VARCHAR(20)"
    payment_type = "ENUM('UNPAID','PARTIALLY_PAID','PAID','REFUNDED')" if dialect in ("mysql", "mariadb") else "VARCHAR(20)"
    column_ddls = [
        ("google_id", "google_id VARCHAR(255) NULL"),
        ("guest_customer_id", "guest_customer_id INTEGER NULL"),
        ("guest_motor_id", "guest_motor_id INTEGER NULL"),
        ("motor_id", "motor_id INTEGER NULL"),
        ("customer_name", "customer_name VARCHAR(50) NULL"),
        ("customer_phone", "customer_phone VARCHAR(20) NULL"),
        ("vehicle_license_plate", "vehicle_license_plate VARCHAR(45) NULL"),
        ("vehicle_brand", "vehicle_brand VARCHAR(45) NULL"),
        ("vehicle_model", "vehicle_model VARCHAR(45) NULL"),
        ("vehicle_vin", "vehicle_vin VARCHAR(45) NULL"),
        ("vehicle_mileage", "vehicle_mileage INTEGER NULL"),
        ("service_type", f"service_type {enum_type} NOT NULL DEFAULT 'MAINTENANCE'"),
        ("problem_description", "problem_description TEXT NULL"),
        ("inspection_result", "inspection_result TEXT NULL"),
        ("payment_status", f"payment_status {payment_type} NOT NULL DEFAULT 'UNPAID'"),
        ("responsible_staff", "responsible_staff VARCHAR(50) NULL"),
        ("scheduled_at", "scheduled_at DATETIME NULL"),
        ("deleted_at", "deleted_at DATETIME NULL"),
        ("deleted_by", "deleted_by VARCHAR(50) NULL"),
        ("delete_reason", "delete_reason TEXT NULL"),
    ]
    for name, ddl in column_ddls:
        _add_column(conn, "work_orders", name, ddl)

    if _has_column(conn, "work_orders", "status"):
        _execute(conn, """
            UPDATE work_orders
            SET status = 'INSPECTION_PENDING'
            WHERE status = 'PENDING'
        """)


def _backfill_guest_motors(conn):
    if "guest_motors" not in _tables(conn) or "work_orders" not in _tables(conn):
        return
    work_order_columns = _columns(conn, "work_orders")
    if "guest_motor_id" not in work_order_columns:
        return

    rows = conn.execute(text("""
        SELECT id, guest_customer_id, vehicle_license_plate, vehicle_brand, vehicle_model, vehicle_vin, vehicle_mileage
        FROM work_orders
        WHERE guest_customer_id IS NOT NULL
          AND vehicle_license_plate IS NOT NULL
          AND vehicle_license_plate != ''
          AND guest_motor_id IS NULL
    """)).mappings().all()

    for row in rows:
        existing = conn.execute(text("""
            SELECT id FROM guest_motors
            WHERE guest_customer_id = :guest_customer_id
              AND license_plate = :license_plate
              AND status IS NULL
            LIMIT 1
        """), {
            "guest_customer_id": row["guest_customer_id"],
            "license_plate": row["vehicle_license_plate"],
        }).mappings().first()

        if existing:
            guest_motor_id = existing["id"]
        else:
            result = conn.execute(text("""
                INSERT INTO guest_motors (
                    guest_customer_id, license_plate, brand, model_name, vin, mileage
                )
                VALUES (
                    :guest_customer_id, :license_plate, :brand, :model_name, :vin, :mileage
                )
            """), {
                "guest_customer_id": row["guest_customer_id"],
                "license_plate": row["vehicle_license_plate"],
                "brand": row["vehicle_brand"],
                "model_name": row["vehicle_model"],
                "vin": row["vehicle_vin"],
                "mileage": row["vehicle_mileage"],
            })
            guest_motor_id = result.lastrowid

        conn.execute(text("""
            UPDATE work_orders
            SET guest_motor_id = :guest_motor_id
            WHERE id = :work_order_id
        """), {
            "guest_motor_id": guest_motor_id,
            "work_order_id": row["id"],
        })


def _migrate_product_categories(conn):
    if "products" not in _tables(conn) or "product_categories" not in _tables(conn):
        return

    _add_column(conn, "products", "category_id", "category_id INTEGER NULL")
    if not _has_column(conn, "products", "category"):
        return

    rows = conn.execute(text("""
        SELECT DISTINCT category
        FROM products
        WHERE category IS NOT NULL
          AND TRIM(category) != ''
    """)).mappings().all()

    for index, row in enumerate(rows, start=1):
        name = row["category"].strip()
        existing = conn.execute(text("""
            SELECT id FROM product_categories
            WHERE name = :name
            LIMIT 1
        """), {"name": name}).mappings().first()

        if existing:
            category_id = existing["id"]
        else:
            result = conn.execute(text("""
                INSERT INTO product_categories (name, sort_order, is_active)
                VALUES (:name, :sort_order, 1)
            """), {"name": name, "sort_order": index})
            category_id = result.lastrowid
            if not category_id:
                created = conn.execute(text("""
                    SELECT id FROM product_categories
                    WHERE name = :name
                    LIMIT 1
                """), {"name": name}).mappings().first()
                category_id = created["id"]

        conn.execute(text("""
            UPDATE products
            SET category_id = :category_id
            WHERE category = :name
              AND category_id IS NULL
        """), {"category_id": category_id, "name": name})


def _migrate_inventory_core(conn):
    if "products" not in _tables(conn):
        return

    _add_column(conn, "products", "inventory_type", "inventory_type VARCHAR(20) NOT NULL DEFAULT 'BOTH'")
    _add_column(conn, "products", "low_stock_threshold", "low_stock_threshold INTEGER NOT NULL DEFAULT 5")
    if _has_column(conn, "products", "inventory_type"):
        _execute(conn, """
            UPDATE products
            SET inventory_type = 'BOTH'
            WHERE inventory_type IS NULL OR inventory_type = ''
        """)
    if _has_column(conn, "products", "low_stock_threshold"):
        _execute(conn, """
            UPDATE products
            SET low_stock_threshold = 5
            WHERE low_stock_threshold IS NULL
        """)


def _migrate_purchase_core(conn):
    if "work_order_line_items" in _tables(conn):
        _add_column(conn, "work_order_line_items", "inventory_reserved_quantity", "inventory_reserved_quantity INTEGER NOT NULL DEFAULT 0")
        _add_column(conn, "work_order_line_items", "inventory_consumed_quantity", "inventory_consumed_quantity INTEGER NOT NULL DEFAULT 0")

        if _has_column(conn, "work_order_line_items", "inventory_deducted"):
            _execute(conn, """
                UPDATE work_order_line_items
                SET inventory_consumed_quantity = quantity
                WHERE inventory_deducted = 1
                  AND COALESCE(inventory_consumed_quantity, 0) = 0
            """)
        _execute(conn, """
            UPDATE work_order_line_items
            SET inventory_reserved_quantity = 0
            WHERE inventory_reserved_quantity IS NULL
        """)
        _execute(conn, """
            UPDATE work_order_line_items
            SET inventory_consumed_quantity = 0
            WHERE inventory_consumed_quantity IS NULL
        """)

    if _dialect(conn) in ("mysql", "mariadb") and "inventory_movements" in _tables(conn):
        movement_column = _columns(conn, "inventory_movements").get("movement_type")
        if movement_column and not all(item in str(movement_column.get("type", "")) for item in ["PURCHASE_RECEIPT", "SCRAP_OUT"]):
            _execute(conn, """
                ALTER TABLE inventory_movements
                MODIFY movement_type ENUM(
                    'MANUAL_ADJUST',
                    'SHOP_ORDER_CONSUME',
                    'WORK_ORDER_CONSUME',
                    'INSTORE_SALE',
                    'CANCEL_RESTORE',
                    'PURCHASE_RECEIPT',
                    'SCRAP_OUT'
                ) NOT NULL
            """)


def _migrate_work_order_approval_core(conn):
    if _dialect(conn) not in ("mysql", "mariadb") or "work_order_approvals" not in _tables(conn):
        return
    approval_column = _columns(conn, "work_order_approvals").get("type")
    required_types = [
        "DISCOUNT",
        "HIGH_QUOTE",
        "STATUS_CHANGE",
        "INVENTORY_RESERVATION",
        "INVENTORY_CONSUMPTION",
    ]
    if approval_column and not all(item in str(approval_column.get("type", "")) for item in required_types):
        _execute(conn, f"""
            ALTER TABLE work_order_approvals
            MODIFY type ENUM({", ".join(repr(item) for item in required_types)})
            NOT NULL
        """)


def _migrate_accounting_core(conn):
    if "orders" in _tables(conn):
        added_payment_status = _add_column(conn, "orders", "payment_status", "payment_status VARCHAR(30) NOT NULL DEFAULT 'PENDING'")
        if _has_column(conn, "orders", "payment_status"):
            where_clause = "" if added_payment_status else "WHERE payment_status IS NULL OR payment_status = ''"
            _execute(conn, f"""
                UPDATE orders
                SET payment_status = CASE
                    WHEN status = 'DEPOSIT_PAID' THEN 'VERIFYING'
                    WHEN status IN ('FULL_PAID', 'COMPLETED') THEN 'PAID'
                    WHEN status = 'CANCELED' THEN 'CANCELED'
                    ELSE 'PENDING'
                END
                {where_clause}
            """)

    tables = _tables(conn)
    if "payment_records" in tables and "work_order_payments" in tables and "work_orders" in tables:
        _execute(conn, """
            INSERT INTO payment_records (
                source_type,
                source_id,
                work_order_id,
                order_id,
                work_order_payment_id,
                customer_name,
                customer_phone,
                amount,
                method,
                actor,
                note,
                paid_at,
                created_at
            )
            SELECT
                'WORK_ORDER',
                p.work_order_id,
                p.work_order_id,
                NULL,
                p.id,
                w.customer_name,
                w.customer_phone,
                p.amount,
                p.method,
                NULL,
                p.note,
                p.paid_at,
                p.paid_at
            FROM work_order_payments p
            JOIN work_orders w ON w.id = p.work_order_id
            WHERE NOT EXISTS (
                SELECT 1
                FROM payment_records r
                WHERE r.work_order_payment_id = p.id
            )
        """)

        if "orders" in tables:
            _execute(conn, """
                INSERT INTO payment_records (
                    source_type,
                    source_id,
                    work_order_id,
                    order_id,
                    work_order_payment_id,
                    customer_name,
                    customer_phone,
                    amount,
                    method,
                    actor,
                    note,
                    paid_at,
                    created_at
                )
                SELECT
                    'SHOP_ORDER',
                    o.id,
                    NULL,
                    o.id,
                    NULL,
                    o.recipient_name,
                    o.recipient_phone,
                    o.total_amount,
                    NULL,
                    NULL,
                    'Backfilled from paid shop order',
                    o.updated_at,
                    o.updated_at
                FROM orders o
                WHERE o.source = 'online'
                  AND o.payment_status = 'PAID'
                  AND NOT EXISTS (
                      SELECT 1
                      FROM payment_records r
                      WHERE r.source_type = 'SHOP_ORDER'
                        AND r.order_id = o.id
                  )
            """)


def upgrade():
    conn = op.get_bind()
    _create_missing_tables(conn)
    _migrate_guest_orders(conn)
    _migrate_order_item_status(conn)
    _migrate_booking_status_enum(conn)
    _migrate_work_orders_core(conn)
    _backfill_guest_motors(conn)
    _migrate_product_categories(conn)
    _migrate_inventory_core(conn)
    _migrate_purchase_core(conn)
    _migrate_work_order_approval_core(conn)
    _migrate_accounting_core(conn)


def downgrade():
    # Baseline migrations must be non-destructive for existing production data.
    pass
