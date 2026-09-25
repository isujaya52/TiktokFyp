from config import app
from clogging import logger,tg_handler
from BOT.cmd import check_tiktok_updates
import asyncio


async def auto_check_loop():
    """Loop 10 menit (600 detik)."""
    while True:
        await asyncio.sleep(60)
        await check_tiktok_updates()

async def main():
    await app.start()
    logger.info("Bot YoiTikTok Aktif!")
    asyncio.create_task(tg_handler.start_worker())
    asyncio.create_task(auto_check_loop())
    await asyncio.Event().wait()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    while True:
        try:
            loop.run_until_complete(main())
        except Exception as e:
            logger.error(f"Bot crash dengan error: {e}. Merestart dalam 5 detik...")
            asyncio.run(asyncio.sleep(5))