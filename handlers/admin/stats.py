"""
handlers/admin/stats.py

Работа со статистикой административной панели.

Содержит:

- меню выбора периодов статистики;
- статистику пользователей за период;
- отображение топ-запросов;
- расширенную общую статистику проекта.
"""

import logging

from telegram import Update
from telegram.ext import ContextTypes

from config import buttons as btn
from config.admin_keyboards import (
    get_admin_keyboard,
    get_stats_keyboard,
    get_top_requests_keyboard,
)
from database import (
    get_detailed_stats,
    get_top_requests,
)


# ==========================================================
# Логгер модуля.
# ==========================================================

logger = logging.getLogger(__name__)


# ==========================================================
# Меню выбора периодов.
# ==========================================================

async def show_top_requests_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """
    Показывает меню выбора периода 
    для анализа популярных запросов.
    """

    await update.message.reply_text(
        "📊 Выберите период для анализа популярных запросов:",
        reply_markup=get_top_requests_keyboard(),
    )


async def show_stats_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """
    Показывает меню выбора периода 
    для просмотра статистики проекта.
    """

    await update.message.reply_text(
        "📈 Выберите период статистики:",
        reply_markup=get_stats_keyboard(),
    )


# ==========================================================
# Топ популярных обращений.
# ==========================================================

async def handle_top_requests_period(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    period_text: str,
) -> None:
    """
    Показывает самые популярные
    обращения пользователей
    за выбранный период.
    """

    del context

    period_map = {
        btn.BTN_PERIOD_7_DAYS: 7,
        btn.BTN_PERIOD_30_DAYS: 30,
        btn.BTN_PERIOD_HALF_YEAR: 180,
        btn.BTN_PERIOD_YEAR: 365,
    }

    days = period_map.get(
        period_text,
        7,
    )

    logger.info(
        f"[TOP REQUESTS] "
        f"period={period_text}, days={days}"
    )

    top_requests = get_top_requests(
        days=days,
    )

    if not top_requests:

        await update.message.reply_text(
            f"📭 Нет данных за {period_text}.",
            reply_markup=get_admin_keyboard(),
        )

        return

    total = sum(
        count
        for _, count in top_requests
    )

    report = (
        f"📊 Топ запросов "
        f"за {period_text}:\n\n"
    )

    emojis = [
        "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣",
        "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟",
    ]

    for index, (topic, count) in enumerate(
        top_requests
    ):

        emoji = (
            emojis[index]
            if index < len(emojis)
            else "•"
        )

        percent = (
            round(count / total * 100, 1)
            if total
            else 0
        )

        report += (
            f"{emoji} {topic}: "
            f"{count} ({percent}%)\n"
        )

    report += (
        f"\nВсего обращений: {total}"
    )

    await update.message.reply_text(
        report,
        reply_markup=get_admin_keyboard(),
    )


# ==========================================================
# Статистика пользователей за выбранный период.
# ==========================================================

async def handle_stats_period(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    period_text: str,
) -> None:
    """
    Показывает статистику пользователей
    за выбранный период.
    """

    del context

    # TODO: В текущей реализации database.get_detailed_stats() 
    # не поддерживает фильтрацию по дням (аргумент days).
    # Сейчас всегда отдается общая статистика.
    # Чтобы работало по периодам, нужно доработать функцию в БД.
    stats = get_detailed_stats()

    report = (
        f"📊 <b>Статистика за период: {period_text}</b>\n\n"
        f"👥 <b>Всего пользователей:</b> {stats['total_users']}\n"
        f"📱 <b>С телефоном:</b> {stats['with_phone']} ({stats['phone_conversion']}%)\n"
        f"🚫 <b>Заблокировали бота:</b> {stats['blocked_count']}\n"
        f"💬 <b>Активные чаты:</b> {stats['active_chats_24h']}\n\n"
        f"🆕 <b>Новых пользователей:</b> {stats['new_today']}\n"
        f"📅 <b>Активных пользователей:</b> {stats['active_last_30_days']}"
    )

    await update.message.reply_text(
        report,
        parse_mode="HTML",
        reply_markup=get_admin_keyboard(),
    )


# ==========================================================
# Общая статистика проекта.
# ==========================================================

async def show_stats(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """
    Показывает расширенную статистику проекта
    за все время.
    """

    del context

    try:

        stats = get_detailed_stats()

        if not stats:

            await update.message.reply_text(
                "❌ Не удалось загрузить статистику"
            )

            return

        report = (
            "📊 <b>Расширенная статистика</b>\n\n"
            f"👥 <b>Всего пользователей:</b> {stats['total_users']}\n"
            f"📱 <b>С телефоном:</b> {stats['with_phone']} ({stats['phone_conversion']}%)\n"
            f"🚫 <b>Заблокировали бота:</b> {stats['blocked_count']}\n"
            f"💬 <b>Активные чаты (24ч):</b> {stats['active_chats_24h']}\n\n"
            f"🆕 <b>Новых за сегодня:</b> {stats['new_today']}\n"
            f"🗓 <b>Новых за неделю:</b> {stats['new_last_7_days']}\n"
            f"📅 <b>Активных за 30 дней:</b> {stats['active_last_30_days']}"
        )

        await update.message.reply_text(
            report,
            parse_mode="HTML",
        )

    except Exception as error:

        logger.exception(
            f"Ошибка статистики: {error}"
        )

        await update.message.reply_text(
            "❌ Ошибка при загрузке данных"
        )