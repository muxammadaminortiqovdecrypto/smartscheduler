import asyncio
import logging
import sys
import os
from pathlib import Path

# Project root ni qo'shish
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from django.conf import settings

# Django sozlamalarini yuklash
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smartscheduler.settings')

# Django ORM ni asinxron rejimda ishlashi uchun
import django
django.setup()

from bot.handlers import router as handlers_router
from bot.callback_handlers import router as callback_router

# Logging sozlamalari
logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)


async def main():
    """Botni ishga tushirish"""
    bot_token = settings.TELEGRAM_BOT_TOKEN
    
    if not bot_token:
        print("❌ TELEGRAM_BOT_TOKEN muhit o'zgaruvchisi topilmadi!")
        print("Iltimos, .env faylida yoki muhit o'zgaruvchilarida tokenni belgilang.")
        return
    
    # Bot yaratish
    bot = Bot(
        token=bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
    )
    
    # Dispatcher yaratish
    dp = Dispatcher()
    
    # Routers ulash
    dp.include_router(handlers_router)
    dp.include_router(callback_router)
    
    # Botni ishga tushirish
    print("🤖 Bot ishga tushmoqda...")
    await dp.start_polling(bot)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Bot to'xtatildi.")
    except Exception as e:
        print(f"❌ Xatolik yuz berdi: {e}")
