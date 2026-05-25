import argparse
import sys

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository


def create_superadmin(username: str | None = None, password: str | None = None) -> None:
    settings = get_settings()
    username = username or settings.INITIAL_SUPERADMIN_USERNAME
    password = password or settings.INITIAL_SUPERADMIN_PASSWORD

    db = SessionLocal()
    try:
        repo = UserRepository(db)
        existing = repo.get_by_username(username)
        if existing:
            print(f"User '{username}' already exists.")
            return
        user = repo.create(
            username=username,
            password_hash=get_password_hash(password),
            full_name="Super Administrator",
            role=UserRole.SUPERADMIN,
        )
        db.commit()
        print(f"Superadmin '{user.username}' created (id={user.id}).")
    finally:
        db.close()


def create_user(
    username: str,
    password: str,
    full_name: str,
    role: UserRole,
    device_id: str | None = None,
) -> None:
    db = SessionLocal()
    try:
        repo = UserRepository(db)
        if repo.get_by_username(username):
            print(f"User '{username}' already exists.")
            return
        user = repo.create(
            username=username,
            password_hash=get_password_hash(password),
            full_name=full_name,
            role=role,
        )
        if device_id and role == UserRole.MOBILE_USER:
            repo.create_device(device_id=device_id, user_id=user.id, platform="android")
        db.commit()
        print(f"User '{username}' ({role.value}) created.")
    finally:
        db.close()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="app.cli")
    sub = parser.add_subparsers(dest="command", required=True)

    sa = sub.add_parser("create-superadmin", help="Create initial superadmin user")
    sa.add_argument("--username", default=None)
    sa.add_argument("--password", default=None)

    cu = sub.add_parser("create-user", help="Create admin or mobile user")
    cu.add_argument("--username", required=True)
    cu.add_argument("--password", required=True)
    cu.add_argument("--full-name", required=True)
    cu.add_argument("--role", required=True, choices=[r.value for r in UserRole])
    cu.add_argument("--device-id", default=None)

    args = parser.parse_args(argv)
    if args.command == "create-superadmin":
        create_superadmin(args.username, args.password)
    elif args.command == "create-user":
        create_user(
            args.username,
            args.password,
            args.full_name,
            UserRole(args.role),
            args.device_id,
        )
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
