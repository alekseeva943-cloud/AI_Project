"""
handlers/admin/broadcast.py

Массовая рассылка сообщений пользователям.

Модуль отвечает за:

- запуск мастера рассылки;
- выбор типа рассылки;
- ввод текста сообщения;
- подтверждение отправки;
- выполнение массовой рассылки;
- формирование отчёта о результатах.
"""

import asyncio
import logging

from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
)

from config import buttons as btn

from config.admin_keyboards import (
    get_admin_keyboard,
    get_broadcast_confirm_keyboard,
    get_broadcast_type_keyboard,
)

from config.keyboards import (
    get_cancel_keyboard,
)

from database import (
    get_all_active_user_ids,
    get_users_with_phone,
    mark_user_blocked,
)

from handlers.admin.constants import (
    AWAITING_BROADCAST_CONFIRM,
    AWAITING_BROADCAST_TEXT,
    AWAITING_BROADCAST_TYPE,
)

# ==========================================================
# Логгер модуля.
# ==========================================================

logger = logging.getLogger(__name__)

# Маппинг кнопок выбора типа рассылки на параметры базы данных
BROADCAST_TYPES = {
    btn.BTN_BROADCAST_ALL: "all",
    btn.BTN_BROADCAST_PHONE: "with_phone"
}


# ==========================================================
# Мастер рассылки.
# ==========================================================

async def start_broadcast(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    """
    Запускает мастер создания рассылки.
    Показывает клавиатуру с выбором типа получателей.

    Returns:
        int: Состояние AWAITING_BROADCAST_TYPE.
    """

    await update.message.reply_text(
        "📤 Выберите тип рассылки:",
        reply_markup=get_broadcast_type_keyboard()
    )

    return AWAITING_BROADCAST_TYPE


async def handle_broadcast_type(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    """
    Обрабатывает выбор типа рассылки (Всем / Только с телефоном).
    Сохраняет выбор в контекст и запрашивает текст.

    Returns:
        int: Состояние AWAITING_BROADCAST_TEXT или конец диалога.
    """

    text = update.message.text.strip()
    
    if text == btn.BTN_CANCEL:
        await update.message.reply_text(
            "Рассылка отменена.",
            reply_markup=get_admin_keyboard()
        )
        return ConversationHandler.END
        
    if text not in BROADCAST_TYPES:
        await update.message.reply_text("Неверный тип.")
        return AWAITING_BROADCAST_TYPE

    context.user_data['broadcast_type'] = BROADCAST_TYPES[text]
    
    await update.message.reply_text(
        "✏️ Введите текст рассылки:",
        reply_markup=get_cancel_keyboard()
    )
    
    return AWAITING_BROADCAST_TEXT


async def handle_broadcast_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    """
    Сохраняет текст рассылки, рассчитывает количество получателей
    и показывает экран подтверждения.

    Returns:
        int: Состояние AWAITING_BROADCAST_CONFIRM или конец диалога.
    """

    text = update.message.text.strip()
    
    if text == btn.BTN_CANCEL:
        await update.message.reply_text(
            "Рассылка отменена.",
            reply_markup=get_admin_keyboard()
        )
        return ConversationHandler.END
        
    if len(text) > 4096:
        await update.message.reply_text("Текст слишком длинный.")
        return AWAITING_BROADCAST_TEXT

    context.user_data['broadcast_text'] = text
    broadcast_type = context.user_data['broadcast_type']
    
    # Получаем список получателей в зависимости от типа
    recipients = (
        get_all_active_user_ids() 
        if broadcast_type == "all" 
        else get_users_with_phone()
    )
    context.user_data['recipient_count'] = len(recipients)

    await update.message.reply_text(
        f"📤 Подтверждение:\nТекст: {text}\nПолучателей: {len(recipients)}\n✅ Отправить | ❌ Отмена",
        reply_markup=get_broadcast_confirm_keyboard()
    )
    
    return AWAITING_BROADCAST_CONFIRM


# ==========================================================
# Выполнение рассылки.
# ==========================================================

async def perform_broadcast(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    """
    Выполняет массовую рассылку пользователям.
    Обрабатывает блокировки и ошибки, формирует итоговый отчёт.

    Returns:
        int: Конец диалога (ConversationHandler.END).
    """

    if update.message.text.strip() != btn.BTN_SEND:
        await update.message.reply_text(
            "Рассылка отменена.",
            reply_markup=get_admin_keyboard()
        )
        return ConversationHandler.END

    text = context.user_data['broadcast_text']
    broadcast_type = context.user_data['broadcast_type']

    # Повторно получаем список получателей
    if broadcast_type == "all":
        recipients = get_all_active_user_ids()
    else:
        recipients = get_users_with_phone()

    if not recipients:
        await update.message.reply_text(
            "Нет получателей для рассылки.",
            reply_markup=get_admin_keyboard()
        )
        return ConversationHandler.END

    await update.message.reply_text(
        f"🚀 Начинаю рассылку ({len(recipients)} получателей)...\n"
        "Это может занять несколько секунд.",
        reply_markup=get_admin_keyboard()
    )

    # Счётчики результатов
    success = 0
    blocked = 0
    errors = 0
    skipped = 0

    # Используем get_running_loop() вместо устаревшего get_event_loop()
    start_time = asyncio.get_running_loop().time()

    # Отправляем по одному с небольшой задержкой во избежание лимитов Telegram
    for user_id in recipients:
        try:
            await context.bot.send_message(chat_id=user_id, text=text)
            success += 1
        except Exception as e:
            error_msg = str(e)
            if "Forbidden: bot was blocked by the user" in error_msg:
                blocked += 1
                mark_user_blocked(user_id)
            elif "Forbidden: user is deactivated" in error_msg:
                blocked += 1
                mark_user_blocked(user_id)
            elif "chat not found" in error_msg:
                skipped += 1
                mark_user_blocked(user_id)
            else:
                errors += 1
                logger.error(f"Ошибка рассылки для {user_id}: {e}")

        await asyncio.sleep(0.04)

    end_time = asyncio.get_running_loop().time()
    duration = round(end_time - start_time, 1)

    # Формируем итоговый отчёт
    report = (
        f"📤 Рассылка завершена!\n\n"
        f"Тип: {'Всем клиентам' if broadcast_type == 'all' else 'Только с телефоном'}\n"
        f"Текст: «{text[:200]}{'...' if len(text) > 200 else ''}»\n\n"
        f"📈 Статистика:\n"
        f"• Всего получателей: {len(recipients)}\n"
        f"• Успешно отправлено: {success}\n"
        f"• Заблокировали бота: {blocked}\n"
        f"• Ошибок отправки: {errors}\n"
        f"• Пропущено: {skipped}\n\n"
        f"⏱ Затрачено времени: {duration} сек"
    )

    if errors == 0 and blocked == 0:
        report += "\n\n✅ Рассылка завершена без сбоев."
    elif blocked > 0:
        report += f"\n\n⚠️ {blocked} пользователей заблокировали бота — их можно удалить из базы."
    else:
        report += "\n\n❗ Возникли ошибки при отправке."

    await update.message.reply_text(report)
    
    return ConversationHandler.END