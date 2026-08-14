import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiohttp import web
from bot.config import BOT_TOKEN, WEBAPP_URL, PORT
from bot.database import init_db
from bot.handlers import router
from bot.webapp_server import setup_webapp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def on_startup(bot: Bot):
    await init_db()
    await bot.set_my_commands([
        ('start', 'Запустить бота'),
        ('menu', 'Главное меню'),
        ('profile', 'Мой профиль'),
        ('add', 'Добавить еду'),
        ('stats', 'Статистика')
    ])
    logger.info('Bot started!')

async def main():
    bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
    dp = Dispatcher()
    dp.include_router(router)
    dp.startup.register(on_startup)
    web_app = web.Application()
    setup_webapp(web_app)
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    logger.info(f'WebApp running on port {PORT}')
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
