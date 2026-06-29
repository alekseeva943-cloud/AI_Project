"""
messages.py

Модуль отвечает за формирование текстов сообщений.

Позволяет:
- централизовать текст
- легко менять формат
"""


def start_message():
    return (
        "🤖 SmartCrawler AI\n\n"
        "Я умею:\n"
        "• Парсить сайт\n"
        "• Строить векторную базу\n"
        "• Отвечать на вопросы\n\n"
        "Выберите действие 👇"
    )


def build_progress(stage: str, step: int = None):
    text = f"⚙️ {stage}"

    if step:
        text += f"\n\n📄 Обработано: {step}"

    return text


def stats_message(stats: dict):
    return (
        "📊 Статистика:\n\n"
        f"🧠 Токены: {stats['tokens']}\n"
        f"💵 USD: {stats['usd']}\n"
        f"💰 RUB: {stats['rub']}\n"
    )
