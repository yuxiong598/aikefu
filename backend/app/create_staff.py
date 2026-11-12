import argparse
from getpass import getpass
from pydantic import ValidationError

from .database import Base, SessionLocal, engine
from .schema.user import Credentials
from .service.auth import AccountConflict, create_account


def main() -> None:
    parser = argparse.ArgumentParser(description="创建本地客服账号")
    parser.add_argument("--username", required=True)
    args = parser.parse_args()
    password = getpass("请输入客服密码（8–128 个字符）: ")
    if password != getpass("请再次输入密码: "):
        parser.exit(1, "两次密码不一致。\n")
    try:
        credentials = Credentials(username=args.username, password=password)
    except ValidationError:
        parser.exit(1, "账号格式或密码长度不符合要求。\n")
    Base.metadata.create_all(engine)
    try:
        with SessionLocal() as session:
            user = create_account(session, credentials, role="staff")
    except AccountConflict as exc:
        parser.exit(1, str(exc) + "\n")
    print(f"已创建客服账号 {user.username}")


if __name__ == "__main__":
    main()
