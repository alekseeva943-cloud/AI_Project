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
    print("Запуск сборки базы знаний...\n")

    stats = run_pipeline()

    from datetime import datetime

    stats["created_at"] = datetime.now().strftime(
        "%d.%m.%Y %H:%M:%S"
    )

    import json

    with open(
        "output/build_stats.json",
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            stats,
            f,
            ensure_ascii=False,
            indent=2
        )

    print("\nСборка успешно завершена")
    print(f"Страниц: {stats['pages']}")
    print(f"Блоков: {stats['blocks']}")
    print(f"Чанков: {stats['chunks']}")
    print(f"Токенов: {stats['tokens']}")
    print(f"Стоимость USD: ${stats['usd']:.4f}")
    print(f"Стоимость RUB: {stats['rub']:.2f} RUB")


if __name__ == "__main__":
    main()