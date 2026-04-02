import argparse
import asyncio

from app.db import connect_mongo
from app.security import hash_password
from app.settings import settings


async def seed_admin(email: str, password: str, active: bool) -> None:
    client, db = await connect_mongo()
    try:
        collection = db[settings.mongodb_admin_collection]
        await collection.update_one(
            {"email": email},
            {
                "$set": {
                    "email": email,
                    "password_hash": hash_password(password),
                    "active": active,
                }
            },
            upsert=True,
        )
    finally:
        client.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed an admin user in MongoDB.")
    parser.add_argument("--email", required=True, help="Admin email")
    parser.add_argument("--password", required=True, help="Admin password")
    parser.add_argument("--inactive", action="store_true", help="Seed as inactive admin")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    asyncio.run(seed_admin(args.email, args.password, active=not args.inactive))


if __name__ == "__main__":
    main()

