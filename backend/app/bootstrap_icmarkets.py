from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.db import SessionLocal
from app.models import Broker


async def bootstrap_ic_markets() -> None:
    async with SessionLocal() as db:
        broker = await db.scalar(select(Broker).where(Broker.slug == "ic-markets"))
        if broker is None:
            broker = Broker(slug="ic-markets", display_name="IC Markets", adapter_key="mt5", api_base_url=None, is_active=True)
            db.add(broker)
        else:
            broker.display_name = "IC Markets"
            broker.adapter_key = "mt5"
            broker.is_active = True
        await db.commit()
        print("IC Markets MT5 broker catalog: READY")


if __name__ == "__main__":
    asyncio.run(bootstrap_ic_markets())
