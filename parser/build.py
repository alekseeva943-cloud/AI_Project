"""
build.py

Отдельная точка входа для сборки базы знаний.

Используется:

- для ручного запуска из консоли;
- для запуска из основного Telegram-бота;
- для запуска через subprocess;
- для будущего автоматического обновления базы.

Важно:
Этот файл НЕ запускает Telegram-бота parser-проекта.

Он запускает только pipeline построения базы знаний.
"""

from app.pipeline.pipeline import run_pipeline


def main():
    print("🚀 Запуск сборки базы знаний...\n")

    stats = run_pipeline()

    print("\n✅ Сборка успешно завершена")
    print(f"📄 Страниц: {stats['pages']}")
    print(f"🧱 Блоков: {stats['blocks']}")
    print(f"📦 Чанков: {stats['chunks']}")
    print(f"🧠 Токенов: {stats['tokens']}")
    print(f"💵 Стоимость: ${stats['usd']:.4f}")
    print(f"💰 Стоимость: {stats['rub']:.2f} ₽")


if __name__ == "__main__":
    main()