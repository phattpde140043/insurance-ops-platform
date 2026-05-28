import asyncio

from app.core.database import AsyncSessionLocal
from app.seed_data import seed_demo_data


async def main() -> None:
    async with AsyncSessionLocal() as session:
        await seed_demo_data(session)


if __name__ == "__main__":
    asyncio.run(main())

