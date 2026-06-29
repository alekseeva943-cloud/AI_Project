"""
handlers.py

Telegram-слой:

Что делает:
1. Обрабатывает кнопки
2. Запускает pipeline
3. Показывает живой прогресс
4. Делает поиск + GPT ответ
5. Отправляет файлы базы
"""

import asyncio
import os
from pathlib import Path  # ✅ ДОБАВИЛИ

from telegram import Update
from telegram.ext import ContextTypes

from app.bot.keyboards import get_main_keyboard
from app.bot.messages import start_message, stats_message

from app.config.settings import BASE_URL
from app.pipeline.pipeline import run_pipeline

from app.rag.search import SearchEngine
from app.gpt.generator import GPTGenerator

from app.utils.cost_tracker import CostTracker


# =========================
# 🔧 Глобальные сервисы
# =========================
search_engine = None
gpt_generator = None
tracker = CostTracker()


# =========================
# 📄 ЗАГРУЗКА "О ПРОЕКТЕ"
# =========================
def load_about_text():
    """
    Загружает текст описания проекта из файла.
    """
    try:
        path = Path("app/prompts/About_project.txt")
        return path.read_text(encoding="utf-8")
    except Exception:
        return "⚠️ Не удалось загрузить информацию о проекте"


# =========================
# 🚀 /start
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        start_message(),
        reply_markup=get_main_keyboard()
    )


# =========================
# 🚀 Построение базы
# =========================
async def build_base(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global search_engine, gpt_generator

    progress_msg = await update.message.reply_text("🚀 Запуск...")

    loop = asyncio.get_running_loop()

    last_text = {"value": ""}

    def progress_callback(text):
        try:
            if "Парсинг страницы" in text or "Спарсено страниц" in text:

                if text == last_text["value"]:
                    return

                last_text["value"] = text

                future = asyncio.run_coroutine_threadsafe(
                    progress_msg.edit_text(text),
                    loop
                )

            else:
                future = asyncio.run_coroutine_threadsafe(
                    update.message.reply_text(text),
                    loop
                )

            future.result()

        except Exception as e:
            print("Ошибка прогресса:", e)

    stats = await asyncio.to_thread(
        run_pipeline,
        progress_callback
    )

    search_engine = SearchEngine()
    gpt_generator = GPTGenerator()

    final_text = f"""
✅ База построена!

🌍 Сайт: {BASE_URL}

📊 Результаты:
📄 Страниц: {stats['pages']}
🧱 Блоков: {stats['blocks']}
📦 Чанков: {stats['chunks']}

💰 Стоимость:
🧠 Токены: {stats['tokens']}
💵 USD: {round(stats['usd'], 4)}
💰 RUB: {round(stats['rub'], 2)}

🚀 Система готова к вопросам!
"""

    await update.message.reply_text(final_text)

    await send_files(update)


# =========================
# 📂 ОТПРАВКА ФАЙЛОВ
# =========================
async def send_files(update: Update):
    await update.message.reply_text("📂 Отправляю файлы базы...")

    files = [
        ("📦 Чанки", "data/chunks_final.json"),
        ("🧠 Метаданные", "data/metadata.json"),
        ("🔍 FAISS индекс", "data/faiss.index"),
        ("📄 Текст базы", "data/raw_text.txt"),
    ]

    sent_any = False

    for title, path in files:
        try:
            if not os.path.exists(path):
                print(f"⚠️ Файл не найден: {path}")
                continue

            with open(path, "rb") as f:
                await update.message.reply_document(
                    document=f,
                    filename=os.path.basename(path),
                    caption=title
                )

            sent_any = True

        except Exception as e:
            print(f"❌ Ошибка отправки {path}: {e}")

    if not sent_any:
        await update.message.reply_text(
            "⚠️ Файлы базы не найдены. Сначала построй базу."
        )


# =========================
# 🔍 Кнопка "Задать вопрос"
# =========================
async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["awaiting_question"] = True
    await update.message.reply_text("✍️ Напишите ваш вопрос")


# =========================
# 📊 Статистика (оставили, но не используем)
# =========================
async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stats = tracker.get_stats()
    await update.message.reply_text(stats_message(stats))


# =========================
# 🧠 Ответ на вопрос
# =========================
async def handle_user_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global search_engine, gpt_generator

    if not search_engine:
        await update.message.reply_text("⚠️ Сначала построй базу")
        return

    query = update.message.text

    msg = await update.message.reply_text("🔍 Ищу информацию...")

    context_text = search_engine.get_context(query)

    await msg.edit_text("🤖 Формирую ответ...")

    answer = gpt_generator.generate(query, context_text)

    await msg.edit_text(answer)


# =========================
# 🧠 Обработка сообщений
# =========================
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "🚀 Построить базу":
        await build_base(update, context)

    elif text == "🔍 Задать вопрос":
        await ask_question(update, context)

    # ✅ НОВАЯ КНОПКА
    elif text == "📌 О проекте":
        about_text = load_about_text()
        await update.message.reply_text(
            about_text,
            parse_mode="HTML",
            disable_web_page_preview=True
        )

    elif context.user_data.get("awaiting_question"):
        context.user_data["awaiting_question"] = False
        await handle_user_question(update, context)

    else:
        await update.message.reply_text("🤔 Используйте кнопки ниже")
