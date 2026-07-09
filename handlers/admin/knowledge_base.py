"""
handlers/admin/knowledge_base.py

Управление базой знаний административной панели.

Модуль отвечает за:

- изменение сайта-источника знаний;
- изменение лимита обхода страниц;
- запуск сборки новой базы знаний;
- активацию новой базы знаний;
- восстановление резервной копии;
- просмотр состояния базы знаний;
- сохранение настроек парсера.
"""

# ==========================================================
# Стандартная библиотека Python
# ==========================================================

import asyncio
import json
import logging
import os
import shutil
from pathlib import Path

# ==========================================================
# Telegram Bot API
# ==========================================================

from telegram import (
    ReplyKeyboardMarkup,
    Update,
)

from telegram.ext import (
    ContextTypes,
    ConversationHandler,
)

# ==========================================================
# Конфигурация проекта
# ==========================================================

from config import buttons as btn

from config.admin_keyboards import (
    get_knowledge_base_keyboard,
)

from config.keyboards import (
    get_cancel_keyboard,
)

from handlers.admin.constants import (
    AWAITING_BUILD_CONFIRMATION,
    AWAITING_CRAWL_LIMIT,
    AWAITING_RAG_SOURCE_URL,
    AWAITING_ACTIVATE_CONFIRMATION,
    AWAITING_RESTORE_CONFIRMATION,
)

from handlers.admin.panel import (
    show_knowledge_base_menu,
)

# ==========================================================
# Сервисы проекта (вынесены из локальных импортов)
# ==========================================================

from services.knowledge_base_manager import (
    activate_new_base,
    get_knowledge_base_status,
    rollback_to_backup,
)

from services.rag_service import (
    reload_rag_index,
)

# ==========================================================
# Логгер
# ==========================================================

logger = logging.getLogger(__name__)

# ==========================================================
# Значения по умолчанию
# ==========================================================

DEFAULT_CRAWL_LIMIT = 4

DEFAULT_RAG_SOURCE = "https://professional24.ru"

# ==========================================================
# Вспомогательные функции
# ==========================================================


def get_parser_settings_path() -> Path:
    """
    Возвращает путь к файлу settings.json.

    Используется всеми функциями модуля,
    чтобы путь был определён только
    в одном месте.
    """

    return (
        Path(__file__).resolve().parent.parent.parent
        / "parser"
        / "app"
        / "config"
        / "settings.json"
    )


def read_parser_settings() -> dict:
    """
    Загружает настройки parser.

    Если файл отсутствует
    или повреждён,
    возвращается пустой словарь.
    """

    try:

        with open(
            get_parser_settings_path(),
            "r",
            encoding="utf-8",
        ) as file:

            return json.load(file)

    except Exception as e:

        logger.error(
            f"Ошибка чтения settings.json: {e}"
        )

        return {}


def save_parser_settings(
    settings: dict,
):
    """
    Сохраняет настройки parser.

    Все изменения settings.json
    должны выполняться только
    через эту функцию.
    """

    with open(
        get_parser_settings_path(),
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            settings,
            file,
            ensure_ascii=False,
            indent=4,
        )


# ==========================================================
# Изменение сайта-источника знаний
# ==========================================================


async def handle_change_site(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    Запускает изменение сайта,
    который используется
    для построения базы знаний.
    """

    context.user_data["cancel_target"] = (
        show_knowledge_base_menu
    )

    settings = read_parser_settings()

    current_url = settings.get(
        "base_url",
        DEFAULT_RAG_SOURCE,
    )

    await update.message.reply_text(
        f"📚 {btn.BTN_KNOWLEDGE_BASE}\n\n"
        f"Текущий источник знаний:\n\n"
        f"{current_url}\n\n"
        f"Введите новый адрес сайта.\n\n"
        f"Для отмены нажмите кнопку:\n"
        f"{btn.BTN_CANCEL}",
        reply_markup=get_cancel_keyboard(),
    )

    return AWAITING_RAG_SOURCE_URL


# ==========================================================
# Изменение лимита страниц
# ==========================================================


async def handle_change_crawl_limit(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    Запускает изменение лимита
    страниц для парсинга сайта.
    """

    context.user_data["cancel_target"] = (
        show_knowledge_base_menu
    )

    settings = read_parser_settings()

    current_limit = settings.get(
        "crawl_limit",
        DEFAULT_CRAWL_LIMIT,
    )

    display_limit = (
        "Все страницы"
        if current_limit == 0
        else str(current_limit)
    )

    await update.message.reply_text(
        f"📄 Текущий лимит страниц:\n\n"
        f"{display_limit}\n\n"
        f"Введите новый лимит.\n\n"
        f"0 = весь сайт\n"
        f"10 = первые 10 страниц\n"
        f"100 = первые 100 страниц\n\n"
        f"Для отмены нажмите:\n"
        f"{btn.BTN_CANCEL}",
        reply_markup=get_cancel_keyboard(),
    )

    return AWAITING_CRAWL_LIMIT


# ==========================================================
# Подтверждение сборки новой базы знаний
# ==========================================================


async def handle_build_new_base(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    Показывает окно подтверждения
    перед запуском новой сборки базы.
    """

    context.user_data["cancel_target"] = (
        show_knowledge_base_menu
    )

    settings = read_parser_settings()

    current_site = settings.get(
        "base_url",
        DEFAULT_RAG_SOURCE,
    )

    current_limit = settings.get(
        "crawl_limit",
        DEFAULT_CRAWL_LIMIT,
    )

    display_limit = (
        "Все страницы"
        if current_limit == 0
        else str(current_limit)
    )

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [btn.BTN_CONFIRM_BUILD],
            [btn.BTN_CANCEL],
        ],
        resize_keyboard=True,
    )

    await update.message.reply_text(
        "⚠️ Вы собираетесь начать сборку новой базы знаний.\n\n"
        f"🌐 Сайт:\n{current_site}\n\n"
        f"📄 Лимит страниц:\n{display_limit}\n\n"
        "Процесс может занять длительное время "
        "и использовать токены OpenAI.\n\n"
        "Продолжить?",
        reply_markup=keyboard,
    )

    return AWAITING_BUILD_CONFIRMATION


# ==========================================================
# Подтверждение запуска сборки
# ==========================================================


async def confirm_build_new_base(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    Запускает сборку новой базы знаний
    после подтверждения администратора.
    """

    await start_build_new_base(
        update,
        context,
    )

    return ConversationHandler.END


# ==========================================================
# Проверка изменений между версиями базы знаний
# ==========================================================


async def handle_check_changes(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    Показывает сравнительную статистику:

    • активной базы;
    • новой базы;
    • резервной копии.
    """

    del context

    def load_stats(path: Path):

        try:

            with open(
                path,
                "r",
                encoding="utf-8",
            ) as file:

                return json.load(file)

        except Exception:

            return {}

    active = load_stats(
        Path("data/build_stats.json")
    )

    new = load_stats(
        Path("parser/output/build_stats.json")
    )

    backup = load_stats(
        Path("backup/build_stats.json")
    )

    def format_block(
        title: str,
        stats: dict,
    ) -> str:

        return (
            f"📦 {title}\n"
            f"📄 Страниц: {stats.get('pages', 0)}\n"
            f"🧱 Блоков: {stats.get('blocks', 0)}\n"
            f"📦 Чанков: {stats.get('chunks', 0)}\n"
            f"🧠 Токенов: {stats.get('tokens', 0)}\n"
            f"💰 USD: {stats.get('usd', 0):.4f}\n"
        )

    report = (
        "🔍 СРАВНЕНИЕ БАЗ ЗНАНИЙ\n\n"
        f"{format_block('Активная база', active)}\n"
        f"{format_block('Новая база', new)}\n"
        f"{format_block('Резервная копия', backup)}"
    )

    await update.message.reply_text(
        report
    )


# ==========================================================
# Сборка новой базы знаний
# ==========================================================


async def start_build_new_base(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    Запускает parser/build.py
    и отображает ход выполнения сборки.
    """

    progress_message = await update.message.reply_text(
        "🏗 Начинаю сборку новой базы знаний...\n\n"
        "⏳ Подготавливаю parser..."
    )

    try:

        parser_dir = (
            Path(__file__).resolve().parent.parent.parent
            / "parser"
        )

        output_dir = parser_dir / "output"

        progress_file = (
            output_dir / "progress.json"
        )

        stats_file = (
            output_dir / "build_stats.json"
        )

        if progress_file.exists():
            progress_file.unlink()

        if stats_file.exists():
            stats_file.unlink()

        current_url = context.bot_data.get(
            "rag_source_url",
            os.getenv(
                "RAG_SOURCE_URL",
                DEFAULT_RAG_SOURCE,
            ),
        )

        env = os.environ.copy()
        env["RAG_SOURCE_URL"] = current_url

        uv_path = shutil.which("uv")

        if uv_path is None:

            raise FileNotFoundError(
                "Не найден uv."
            )

        process = await asyncio.create_subprocess_exec(
            uv_path,
            "run",
            "build.py",
            cwd=str(parser_dir),
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        last_step = None

        while process.returncode is None:

            if progress_file.exists():

                try:

                    progress = json.loads(
                        progress_file.read_text(
                            encoding="utf-8"
                        )
                    )

                    if (
                        progress.get("step")
                        != last_step
                    ):

                        last_step = progress.get(
                            "step"
                        )

                        await progress_message.edit_text(
                            "🏗 Сборка базы знаний\n\n"
                            f"{progress.get('progress', 0)}%\n\n"
                            f"{progress.get('message', 'Работаю...')}"
                        )

                except Exception:

                    pass

            await asyncio.sleep(2)

        stdout, stderr = await process.communicate()

        if process.returncode != 0:

            raise RuntimeError(
                stderr.decode(errors="ignore")
            )

        stats = {}

        if stats_file.exists():

            stats = json.loads(
                stats_file.read_text(
                    encoding="utf-8"
                )
            )

        await progress_message.edit_text(
            "✅ Новая база успешно собрана.\n\n"
            f"📄 Страниц: {stats.get('pages', 0)}\n"
            f"🧱 Блоков: {stats.get('blocks', 0)}\n"
            f"📦 Чанков: {stats.get('chunks', 0)}\n"
            f"🧠 Токенов: {stats.get('tokens', 0)}\n\n"
            f"💵 USD: ${stats.get('usd', 0):.4f}\n"
            f"💵 RUB: {stats.get('rub', 0):.2f} ₽\n\n"
            "🟡 База собрана.\n"
            "Она ещё не активирована."
            "Для применения используйте:\n"
            "🔄 Активировать новую базу"
        )

        await show_knowledge_base_menu(
            update,
            context,
        )

    except Exception as e:

        logger.exception(e)

        await progress_message.edit_text(
            f"❌ Ошибка сборки.\n\n{e}"
        )


# ==========================================================
# Активация новой базы знаний
# ==========================================================


async def handle_activate_new_base(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    Запрашивает подтверждение перед активацией новой базы,
    чтобы случайно не заменить текущую рабочую версию.
    """

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [btn.BTN_CONFIRM_BUILD],
            [btn.BTN_CANCEL],
        ],
        resize_keyboard=True,
    )

    await update.message.reply_text(
        "⚠️ Вы уверены, что хотите активировать новую базу?\n\n"
        "Текущая активная база будет автоматически "
        "сохранена как резервная копия.",
        reply_markup=keyboard,
    )

    return AWAITING_ACTIVATE_CONFIRMATION


async def confirm_activate_new_base(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    Делает новую базу знаний активной после подтверждения.

    Вызывает сервисный слой для безопасного копирования
    (с созданием бэкапа текущей базы) и перезагружает
    RAG индекс в оперативной памяти бота.
    """

    await update.message.reply_text(
        "🔄 Начинаю активацию новой базы..."
    )

    success = activate_new_base()

    if success:

        reload_success = reload_rag_index()

        if reload_success:

            await update.message.reply_text(
                "✅ Новая база успешно активирована.\n\n"
                "♻️ RAG индекс успешно перезагружен.\n"
                "📦 Предыдущая версия сохранена в резервной копии."
            )

        else:

            await update.message.reply_text(
                "⚠️ Новая база скопирована на диск,\n"
                "но не удалось перезагрузить RAG индекс.\n\n"
                "Рекомендуется перезапустить бота "
                "или выполнить откат базы."
            )

    else:

        await update.message.reply_text(
            "❌ Ошибка активации базы."
        )

    # Возвращаем в меню базы знаний, чтобы обновить клавиатуру
    await show_knowledge_base_menu(
        update,
        context,
    )

    return ConversationHandler.END
# ==========================================================
# Восстановление резервной копии
# ==========================================================


async def handle_backup_restore(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    Запрашивает подтверждение перед откатом базы на бэкап,
    чтобы случайно не затереть текущую активную базу.
    """

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [btn.BTN_CONFIRM_BUILD],
            [btn.BTN_CANCEL],
        ],
        resize_keyboard=True,
    )

    await update.message.reply_text(
        "⚠️ Вы уверены, что хотите откатить базу знаний?\n\n"
        "Текущая активная база будет затерта резервной копией!",
        reply_markup=keyboard,
    )

    return AWAITING_RESTORE_CONFIRMATION


async def confirm_backup_restore(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    Выполняет откат активной базы знаний
    на предыдущую рабочую версию после подтверждения.

    После восстановления автоматически
    выполняется reload RAG индекса.
    """

    await update.message.reply_text(
        "⏪ Начинаю восстановление предыдущей базы..."
    )

    success = rollback_to_backup()

    if not success:

        await update.message.reply_text(
            "❌ Не удалось восстановить резервную копию.\n\n"
            "Проверьте логи сервера."
        )

        # Возвращаем в меню даже если произошла ошибка
        await show_knowledge_base_menu(
            update,
            context,
        )
        return ConversationHandler.END

    reload_success = reload_rag_index()

    if reload_success:

        await update.message.reply_text(
            "✅ Предыдущая версия базы успешно восстановлена.\n\n"
            "♻️ RAG индекс успешно перезагружен."
        )

    else:

        await update.message.reply_text(
            "⚠️ База восстановлена, "
            "но возникла ошибка перезагрузки RAG индекса.\n\n"
            "Рекомендуется перезапустить бота."
        )

    # Возвращаем в меню базы знаний, чтобы обновить клавиатуру
    await show_knowledge_base_menu(
        update,
        context,
    )

    return ConversationHandler.END
# ==========================================================
# Состояние базы знаний
# ==========================================================


async def handle_knowledge_status(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    Показывает текущие параметры и статистику
    активной, новой и резервной баз знаний.
    """

    del context

    status = get_knowledge_base_status()

    text = "📊 Статус базы знаний\n\n"

    if status.get("active"):

        active = status["active"]

        text += (
            "🟢 Активная база\n"
            f"📄 Страниц: {active.get('pages', 0)}\n"
            f"📦 Чанков: {active.get('chunks', 0)}\n"
            f"🧠 Токенов: {active.get('tokens', 0)}\n"
            f"🕒 Активирована: "
            f"{active.get('created_at', 'неизвестно')}\n\n"
        )

    else:

        text += (
            "🔴 Активная база отсутствует\n\n"
        )

    if status.get("new"):

        new = status["new"]

        text += (
            "🟡 Новая собранная база\n"
            f"📄 Страниц: {new.get('pages', 0)}\n"
            f"📦 Чанков: {new.get('chunks', 0)}\n"
            f"🧠 Токенов: {new.get('tokens', 0)}\n"
            f"🕒 Собрана: "
            f"{new.get('created_at', 'неизвестно')}\n"
            f"Статус: ожидает активации\n\n"
        )

    else:

        text += (
            "⚪ Новая база отсутствует\n\n"
        )

    if status.get("backup"):

        backup = status["backup"]

        text += (
            "💾 Резервная копия\n"
            f"📄 Страниц: {backup.get('pages', 0)}\n"
            f"📦 Чанков: {backup.get('chunks', 0)}\n"
            f"🧠 Токенов: {backup.get('tokens', 0)}\n"
            f"🕒 Создана: "
            f"{backup.get('created_at', 'неизвестно')}\n"
            f"Статус: готова к откату"
        )

    else:

        text += (
            "💾 Резервная копия отсутствует"
        )

    await update.message.reply_text(text)


# ==========================================================
# Сохранение нового адреса сайта
# ==========================================================


async def save_rag_source_url(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    Сохраняет новый URL сайта
    для последующей сборки базы.

    Добавляет https:// при отсутствии и сохраняет
    значение как в файл настроек, так и в оперативную
    память бота, чтобы сборщик сразу использовал его.
    """

    new_url = update.message.text.strip()

    if not new_url.startswith(("http://", "https://")):
        new_url = "https://" + new_url

    context.bot_data["rag_source_url"] = new_url

    settings = read_parser_settings()
    settings["base_url"] = new_url
    save_parser_settings(settings)

    await update.message.reply_text(
        f"✅ Новый источник знаний сохранён:\n\n"
        f"{new_url}",
        reply_markup=get_knowledge_base_keyboard(),
    )

    return ConversationHandler.END


# ==========================================================
# Сохранение нового лимита страниц
# ==========================================================


async def save_crawl_limit(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    Сохраняет новый лимит
    обхода страниц parser.

    Проверяет введенное значение на корректность
    и выводит понятное пользователю сообщение
    (например, 'Все страницы' при вводе 0).
    """

    try:

        value = int(
            update.message.text.strip()
        )

        if value < 0:

            raise ValueError

    except ValueError:

        await update.message.reply_text(
            "❌ Введите целое число больше "
            "или равное нулю."
        )

        return AWAITING_CRAWL_LIMIT

    settings = read_parser_settings()
    settings["crawl_limit"] = value
    save_parser_settings(settings)

    display_limit = (
        "Все страницы"
        if value == 0
        else str(value)
    )

    await update.message.reply_text(
        f"✅ Новый лимит страниц сохранён:\n\n"
        f"{display_limit}",
        reply_markup=get_knowledge_base_keyboard(),
    )

    return ConversationHandler.END
