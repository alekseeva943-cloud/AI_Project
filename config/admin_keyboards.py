# ==========================================================
# Файл: admin_keyboards.py
# Путь: config/admin_keyboards.py
#
# Назначение:
# Файл содержит все клавиатуры административной панели.
# Используется для отделения UI админки от бизнес-логики.
#
# Здесь находятся:
# - главное меню администратора;
# - меню настроек;
# - управление администраторами;
# - меню рассылок;
# - выбор периода статистики;
# - выбор периода топ-запросов;
# - подтверждение рассылки.
# ==========================================================

from telegram import ReplyKeyboardMarkup

from config.buttons import (
    BTN_BACK,
    BTN_BACKUP,
    BTN_CRAWL_LIMIT,
    BTN_PREVIOUS,
    BTN_CANCEL,
    BTN_SEND,

    BTN_BROADCAST,
    BTN_CLIENT_SEARCH,
    BTN_STATS,
    BTN_TOP_REQUESTS,
    BTN_SETTINGS,
    BTN_USERS,
    BTN_ADMINS,

    BTN_ADD_ADMIN,
    BTN_REMOVE_ADMIN,

    BTN_BROADCAST_ALL,
    BTN_BROADCAST_PHONE,

    BTN_PERIOD_7_DAYS,
    BTN_PERIOD_30_DAYS,
    BTN_PERIOD_HALF_YEAR,
    BTN_PERIOD_YEAR,

    BTN_TODAY,
    BTN_WEEK,
    BTN_MONTH,
    BTN_STATS_YEAR,

    BTN_KNOWLEDGE_BASE,
    BTN_CHANGE_SITE,
    BTN_CHECK_CHANGES,
    BTN_BUILD_NEW_BASE,
    BTN_ACTIVATE_NEW_BASE,
    BTN_KNOWLEDGE_STATUS
    )

# ==========================================================
# Главное меню администратора.
# Используется при входе в админ-панель.
# ==========================================================

def get_admin_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [BTN_BROADCAST, BTN_CLIENT_SEARCH],
            [BTN_STATS, BTN_TOP_REQUESTS],
            [BTN_SETTINGS, BTN_USERS],
            [BTN_BACK]
        ],
        resize_keyboard=True
    )


# ==========================================================
# Меню настроек административной панели.
# ==========================================================

def get_settings_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [BTN_ADMINS],
            [BTN_KNOWLEDGE_BASE],
            [BTN_PREVIOUS]
        ],
        resize_keyboard=True
    )


# ==========================================================
# Меню управления администраторами.
# ==========================================================

def get_admins_management_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [BTN_ADD_ADMIN, BTN_REMOVE_ADMIN],
            [BTN_PREVIOUS]
        ],
        resize_keyboard=True
    )


# ==========================================================
# Выбор типа рассылки.
# Используется перед запуском рассылки сообщений.
# ==========================================================

def get_broadcast_type_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [BTN_BROADCAST_ALL, BTN_BROADCAST_PHONE],
            [BTN_CANCEL]
        ],
        resize_keyboard=True
    )


# ==========================================================
# Выбор периода отображения статистики.
# ==========================================================

def get_stats_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [BTN_PERIOD_7_DAYS, BTN_PERIOD_30_DAYS],
            [BTN_PERIOD_HALF_YEAR, BTN_PERIOD_YEAR],
            [BTN_PREVIOUS]
        ],
        resize_keyboard=True
    )


# ==========================================================
# Выбор периода отображения топ-запросов.
# ==========================================================

def get_top_requests_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [BTN_TODAY, BTN_WEEK],
            [BTN_MONTH, BTN_STATS_YEAR],
            [BTN_PREVIOUS]
        ],
        resize_keyboard=True
    )


# ==========================================================
# Подтверждение отправки рассылки.
# ==========================================================

def get_broadcast_confirm_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [BTN_SEND, BTN_CANCEL]
        ],
        resize_keyboard=True
    )

# ==========================================================
# КЛАВИАТУРА УПРАВЛЕНИЯ БАЗОЙ ЗНАНИЙ
#
# Используется:
# - handlers/admin.py
# - handlers/settings.py
#
# Позволяет полностью управлять RAG через Telegram.
# ==========================================================

def get_knowledge_base_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[

            # Основной рабочий цикл
            [BTN_CHECK_CHANGES, BTN_BUILD_NEW_BASE],
            [BTN_ACTIVATE_NEW_BASE, BTN_BACKUP],

            # Информация о состоянии
            [BTN_KNOWLEDGE_STATUS],

            # Настройки источника и парсинга
            [BTN_CHANGE_SITE, BTN_CRAWL_LIMIT],

            # Навигация
            [BTN_PREVIOUS]
        ],
        resize_keyboard=True
    )