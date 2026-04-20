PROFESSIONAL24/
├── __pycache__/
├── config/
│   ├── __pycache__/
│   ├── __init__.py
│   ├── config.py         # Конфигурационные параметры
│   └── gpt_prompt.json   # Промпты для GPT
├── data/
│   └── dialogs.db        # База данных диалогов
├── handlers/
│   ├── __pycache__/
│   ├── __init__.py
│   ├── admin.py          # Админ-команды
│   ├── gpt_chat.py       # Обработка GPT-чата
│   ├── start.py          # Стартовые команды
│   ├── utilities.py      # Вспомогательные функции
│   └── utils.py          # Доп. утилиты
├── venv/                 # Виртуальное окружение
├── .env                  # Переменные окружения
├── bot.py                # Основной файл бота
├── database.py           # Работа с БД
├── gpt_service.py        # Сервис работы с GPT
├── prompt_sync.py        # Синхронизация промптов
├── README.md
├── requirements.txt
└── test_config.py        # Тесты конфигурации

Разъяснения:
config.py - централизованное хранение настроек:

Токены и ключи

Параметры GPT

Шаблоны клавиатур

handlers/start.py - логика старта и работы с контактами:

start() - приветствие и главное меню

handle_contact() - обработка полученного номера телефона

handlers/gpt_chat.py - взаимодействие с GPT:

handle_message() - обработка вопросов пользователя

handlers/admin.py - административные функции:

admin_panel() - проверка прав и показ меню

admin_stats() - пример функции статистики

get_admin_handlers() - регистрация обработчиков

bot.py - ядро приложения:

Инициализация и запуск бота

Регистрация всех обработчиков

Как расширить функционал администратора:
Добавьте новые кнопки в Config.get_admin_keyboard()

Создайте соответствующие функции-обработчики в admin.py

Зарегистрируйте их в get_admin_handlers()

Например, для добавления рассылки:

python
# В config.py добавить кнопку
["📢 Рассылка"]

# В admin.py добавить обработчик
async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != Config.MANAGER_CHAT_ID:
        return
    
    await update.message.reply_text("Введите сообщение для рассылки:")
    # Дальше логика рассылки

# И зарегистрировать в get_admin_handlers()
MessageHandler(filters.Regex("^📢 Рассылка$"), admin_broadcast)