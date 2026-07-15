import asyncio
import logging

from django.core.management.base import BaseCommand

from bot.handlers import setup_bot

__all__ = ["Command"]

logger = logging.getLogger("bot")


class Command(BaseCommand):
    help = "Запуск Telegram бота"

    def handle(self, *args, **options):
        self.stdout.write("Запуск Telegram бота...")
        asyncio.run(self._run())

    async def _run(self):
        bot, dp = await setup_bot()
        if not bot:
            self.stderr.write("Ошибка: TELEGRAM_BOT_TOKEN " "не задан")
            return

        try:
            await bot.delete_webhook(drop_pending_updates=True)
            await dp.start_polling(
                bot,
                allowed_updates=["message", "callback_query"],
                drop_pending_updates=True,
            )
        finally:
            await bot.session.close()
