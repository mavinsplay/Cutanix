import logging

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    MenuButtonWebApp,
    Message,
    WebAppInfo,
)
from django.conf import settings

__all__ = ["setup_bot"]

logger = logging.getLogger("bot")
router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    bot = message.bot
    user_id = message.from_user.id
    channel_id = settings.TELEGRAM_CHANNEL_ID

    if channel_id:
        try:
            member = await bot.get_chat_member(
                chat_id=channel_id,
                user_id=user_id,
            )
            if member.status in (
                "left",
                "kicked",
            ):
                kb = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text=(
                                    "📢 "
                                    "Подписаться"
                                ),
                                url=(
                                    f"https://t.me/"
                                    f"{channel_id.lstrip('@')}"
                                ),
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                text=(
                                    "✅ "
                                    "Я подписался"
                                ),
                                callback_data=(
                                    "check_subscription"
                                ),
                            )
                        ],
                    ]
                )
                await message.answer(
                    (
                        "Для использования Cutanix "
                        "необходимо подписаться "
                        "на наш канал!"
                    ),
                    reply_markup=kb,
                )
                return
        except Exception as exc:
            logger.warning(
                "Channel check failed: %s", exc
            )

    await send_welcome(bot, message.chat.id)


async def send_welcome(bot, chat_id):
    site_url = settings.SITE_URL
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔬 Открыть Cutanix",
                    web_app=WebAppInfo(
                        url=site_url
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="🚩 Поддержка",
                    url="https://t.me/S112OS",
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
        (
            "🔬 <b>Cutanix</b> — ваш персональный "
            "аналитик состава косметики\n\n"
            "Загрузите фото этикетки или вставьте "
            "состав текстом — мы проверим "
            "безопасность вашего средства.\n\n"
            "Нажмите кнопку ниже, чтобы начать 👇"
        ),
        parse_mode="HTML",
        reply_markup=kb,
    )


@router.callback_query(
    F.data == "check_subscription"
)
async def check_subscription(callback):
    bot = callback.bot
    user_id = callback.from_user.id
    channel_id = settings.TELEGRAM_CHANNEL_ID

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
            "Не удалось проверить подписку. "
            "Попробуйте позже.",
            show_alert=True,
        )
        return

    await callback.message.delete()
    await send_welcome(bot, callback.message.chat.id)


async def setup_bot():
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        logger.error(
            "TELEGRAM_BOT_TOKEN not set"
        )
        return None, None

    bot = Bot(token=token)
    dp = Dispatcher()
    dp.include_router(router)
    return bot, dp
