import asyncio
import logging
import time

from aiogram import BaseMiddleware, Bot, Dispatcher, F, Router
from aiogram.exceptions import TelegramAPIError, TelegramRetryAfter
from aiogram.filters import CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    MenuButtonWebApp,
    Message,
    Update,
    WebAppInfo,
)
from django.conf import settings

__all__ = ["setup_bot"]

logger = logging.getLogger("bot")
router = Router()


class AntiFloodMiddleware(BaseMiddleware):
    """Ограничивает число апдейтов от одного пользователя (скользящее окно)."""

    def __init__(self, limit: int = 15, window: int = 60):
        self.limit = limit
        self.window = window
        self.hits: dict[int, list[float]] = {}

    async def __call__(self, handler, event, data):
        user_id = self._user_id(event)
        if user_id is None:
            return await handler(event, data)

        now = time.monotonic()
        times = self.hits.setdefault(user_id, [])
        times[:] = [t for t in times if now - t < self.window]

        if len(times) >= self.limit:
            logger.warning(
                "Anti-flood: user %s превысил лимит (%s/%ss)",
                user_id,
                self.limit,
                self.window,
            )
            if isinstance(event, (Message, CallbackQuery)):
                try:
                    await event.answer(
                        "Слишком много запросов. "
                        "Пожалуйста, подождите минуту.",
                        show_alert=isinstance(event, CallbackQuery),
                    )
                except Exception:
                    pass
            return

        times.append(now)
        return await handler(event, data)

    @staticmethod
    def _user_id(event):
        if isinstance(event, (Message, CallbackQuery)):
            user = event.from_user
            if user is None or user.is_bot:
                return None
            return user.id
        return None


class ConcurrencyMiddleware(BaseMiddleware):
    """Ограничивает число одновременно обрабатываемых апдейтов,
    чтобы бот нельзя было «положить» лавиной запросов."""

    def __init__(self, limit: int = 25):
        self.semaphore = asyncio.Semaphore(limit)

    async def __call__(self, handler, event, data):
        async with self.semaphore:
            return await handler(event, data)


class PrivateOnlyMiddleware(BaseMiddleware):
    """Игнорирует всё, кроме личных сообщений — группы/каналы не могут
    использоваться для флуда бота."""

    async def __call__(self, handler, event, data):
        if isinstance(event, Message):
            chat = event.chat
            if chat is None or chat.type != "private":
                return
        elif isinstance(event, CallbackQuery):
            chat = event.message.chat if event.message else None
            if chat is None or chat.type != "private":
                return
        return await handler(event, data)


def channel_link() -> str:
    """Публичная ссылка на канал вида https://t.me/<username>."""
    username = settings.TELEGRAM_CHANNEL_USERNAME
    if not username:
        return ""
    return f"https://t.me/{username.lstrip('@')}"


def channel_api_id() -> str:
    """Идентификатор канала для вызовов Telegram API (get_chat_member).
    Числовой ID надёжнее всего (работает и для приватных каналов);
    если он не задан — используем username с префиксом @."""
    if settings.TELEGRAM_CHANNEL_ID:
        return settings.TELEGRAM_CHANNEL_ID
    if settings.TELEGRAM_CHANNEL_USERNAME:
        return "@" + settings.TELEGRAM_CHANNEL_USERNAME.lstrip("@")
    return ""


async def validate_channel(bot: Bot) -> None:
    """Проверяет, что бот может работать с каналом (должен быть админом)."""
    ref = channel_api_id()
    if not ref:
        return
    try:
        await bot.get_chat(ref)
    except Exception as exc:
        logger.error(
            "Бот не может получить доступ к каналу '%s': %s. "
            "Убедитесь, что TELEGRAM_CHANNEL_ID (числовой ID канала) "
            "указан верно и бот добавлен в канал администратором.",
            ref,
            exc,
        )
        return
    try:
        member = await bot.get_chat_member(chat_id=ref, user_id=bot.id)
        if member.status not in ("administrator", "creator"):
            logger.error(
                "Бот добавлен в канал %s, но НЕ является его "
                "администратором — проверка подписки работать "
                "не будет.",
                ref,
            )
    except Exception as exc:
        logger.warning(
            "Не удалось получить статус бота в канале %s: %s",
            ref,
            exc,
        )


@router.message(CommandStart())
async def cmd_start(message: Message):
    bot = message.bot
    user_id = message.from_user.id
    channel_id = channel_api_id()

    if channel_id:
        try:
            member = await bot.get_chat_member(
                chat_id=channel_id,
                user_id=user_id,
            )
            if member.status in ("left", "kicked"):
                invite = channel_link()
                kb_rows = []
                if invite:
                    kb_rows.append(
                        [
                            InlineKeyboardButton(
                                text="📢 Подписаться",
                                url=invite,
                            )
                        ]
                    )
                kb_rows.append(
                    [
                        InlineKeyboardButton(
                            text="✅ Я подписался",
                            callback_data="check_subscription",
                        )
                    ]
                )
                kb = InlineKeyboardMarkup(inline_keyboard=kb_rows)
                await message.answer(
                    "Для использования Cutanix "
                    "необходимо подписаться "
                    "на наш канал!",
                    reply_markup=kb,
                )
                return
        except Exception as exc:
            logger.warning(
                "Проверка подписки не удалась (бот должен быть "
                "администратором канала): %s",
                exc,
            )

    await send_welcome(bot, message.chat.id)


async def send_welcome(bot, chat_id):
    site_url = settings.SITE_URL
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔬 Открыть Cutanix",
                    web_app=WebAppInfo(url=site_url),
                )
            ],
            [
                InlineKeyboardButton(
                    text="🚩 Поддержка", url="https://t.me/S112OS"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📄 Пользовательское соглашение",
                    url="https://telegra.ph/Polzovatelskoe-soglashenie-04-01-19",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔒 Политика конфиденциальности",
                    url="https://telegra.ph/Politika-konfidencialnosti-06-21-31",
                )
            ],
        ]
    )

    await bot.set_chat_menu_button(
        chat_id=chat_id,
        menu_button=MenuButtonWebApp(
            text="🔬 Cutanix",
            web_app=WebAppInfo(url=site_url),
        ),
    )

    await bot.send_message(
        chat_id,
        "🔬 <b>Cutanix</b> — ваш персональный "
        "аналитик состава косметики\n\n"
        "Загрузите фото этикетки или вставьте "
        "состав текстом — мы проверим "
        "безопасность вашего средства.\n\n"
        "Нажмите кнопку ниже, чтобы начать 👇",
        parse_mode="HTML",
        reply_markup=kb,
    )


@router.callback_query(F.data == "check_subscription")
async def check_subscription(callback: CallbackQuery):
    bot = callback.bot
    user_id = callback.from_user.id
    channel_id = channel_api_id()

    try:
        member = await bot.get_chat_member(
            chat_id=channel_id,
            user_id=user_id,
        )
        if member.status in ("left", "kicked"):
            await callback.answer(
                "Вы ещё не подписались на канал!",
                show_alert=True,
            )
            return
    except Exception:
        await callback.answer(
            "Не удалось проверить подписку. " "Попробуйте позже.",
            show_alert=True,
        )
        return

    await callback.message.delete()
    await send_welcome(bot, callback.message.chat.id)


async def errors_handler(update: Update, exception: Exception):
    if isinstance(exception, TelegramRetryAfter):
        logger.warning(
            "Flood control: повтор через %ss", exception.retry_after
        )
        return True
    if isinstance(exception, TelegramAPIError):
        logger.error("Telegram API error: %s", exception)
        return True
    logger.exception("Необработанная ошибка в боте: %s", exception)
    return True


async def setup_bot():
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not set")
        return None, None

    bot = Bot(token=token)
    dp = Dispatcher()

    dp.update.outer_middleware(ConcurrencyMiddleware(limit=25))
    dp.update.middleware(AntiFloodMiddleware(limit=15, window=60))
    dp.update.middleware(PrivateOnlyMiddleware())

    dp.include_router(router)
    dp.errors()(errors_handler)

    try:
        await validate_channel(bot)
    except Exception as exc:
        logger.warning("Пропуск проверки канала: %s", exc)

    return bot, dp
