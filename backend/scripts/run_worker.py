import asyncio

from app.core.database import AsyncSessionLocal
from app.workers.background_worker import BackgroundWorker


async def main() -> None:
    async with AsyncSessionLocal() as session:
        await BackgroundWorker(session).run_forever()


if __name__ == "__main__":
    asyncio.run(main())

