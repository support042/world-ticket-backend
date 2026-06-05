import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import engine
from app.repositories.admin_repository import AdminRepository


async def create_first_admin():
    email = settings.INITIAL_ADMIN_EMAIL
    password = settings.INITIAL_ADMIN_PASSWORD
    name = settings.INITIAL_ADMIN_NAME

    async with AsyncSession(engine) as db:
        repo = AdminRepository(db)

        existing = await repo.get_by_email(email)
        if existing:
            print(f"Admin with email {email} already exists!")
            return

        try:
            new_admin = await repo.create(
                email=email,
                hashed_password=hash_password(password),
                name=name,
                role="admin",
            )
            await db.commit()
            print(f"Successfully created admin: {email}")
        except Exception as e:
            await db.rollback()
            print(f"Failed to create admin: {e}")


if __name__ == "__main__":
    asyncio.run(create_first_admin())
