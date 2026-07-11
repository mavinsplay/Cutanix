import asyncio
import logging

from django.core.management.base import BaseCommand

from bot.handlers import setup_bot

__all__ = ["Command"]

logger = logging.getLogger("bot")


class Command(BaseCommand):
    help = "Запуск Telegram бота"

    def handle(self, *args, **options):
        self.stdout.write(
            "Запуск Telegram бота..."
        )
        asyncio.run(self._run())

    async def _run(self):
        bot, dp = await setup_bot()
        if not bot:
            self.stderr.write(
                "Ошибка: TELEGRAM_BOT_TOKEN "
                "не задан"
            )
            return

        try:
            await dp.start_polling(bot)
        finally:
            await bot.session.close()
