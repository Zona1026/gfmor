"""Emergency reset tool for shop admin passwords.

Run this on a trusted server or local machine that has access to the project's
DATABASE_URL. Passwords cannot be recovered, only replaced.
"""

from __future__ import annotations

import argparse
import getpass
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MIN_PASSWORD_LENGTH = 8


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reset or create a GFmoter shop admin password.",
    )
    parser.add_argument("username", help="Admin username to reset.")
    parser.add_argument(
        "--password",
        help="New password. Omit this to enter it securely without shell history.",
    )
    parser.add_argument(
        "--create-if-missing",
        action="store_true",
        help="Create the admin account when the username does not exist.",
    )
    parser.add_argument(
        "--role",
        default="最高級",
        help="Role to use when creating a missing admin. Default: 最高級.",
    )
    parser.add_argument(
        "--full-name",
        default=None,
        help="Optional full name to set when creating a missing admin.",
    )
    return parser.parse_args()


def read_password(password_arg: str | None) -> str:
    if password_arg is not None:
        return password_arg

    password = getpass.getpass("New admin password: ")
    confirm = getpass.getpass("Confirm new admin password: ")
    if password != confirm:
        raise ValueError("Passwords do not match.")
    return password


def validate(username: str, password: str) -> None:
    if not username.strip():
        raise ValueError("Username is required.")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")


def reset_admin_password(args: argparse.Namespace, password: str) -> str:
    os.chdir(PROJECT_ROOT)
    sys.path.insert(0, str(PROJECT_ROOT))

    from core.security import get_password_hash
    from db import models
    from db.database import SessionLocal

    db = SessionLocal()
    try:
        admin = db.query(models.Admin).filter(models.Admin.username == args.username).first()
        if admin is None:
            if not args.create_if_missing:
                raise LookupError(
                    f"Admin '{args.username}' does not exist. "
                    "Use --create-if-missing only when you intentionally need a new emergency admin."
                )
            admin = models.Admin(
                username=args.username,
                full_name=args.full_name,
                role=args.role,
                hashed_password=get_password_hash(password),
            )
            db.add(admin)
            action = "created"
        else:
            admin.hashed_password = get_password_hash(password)
            action = "updated"

        db.commit()
        return f"Admin '{args.username}' {action}. Role: {admin.role}"
    finally:
        db.close()


def main() -> int:
    args = parse_args()
    try:
        password = read_password(args.password)
        validate(args.username, password)
        message = reset_admin_password(args, password)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(message)
    print("Password reset complete. Sign in once and rotate the password if it was shared.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
