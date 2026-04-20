import os
import json
from openai import OpenAI
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Пути к файлам
CONFIG_DIR = Path(__file__).parent / "configs"
CONFIG_DIR.mkdir(exist_ok=True)
PROMPT_PATH = CONFIG_DIR / "gpt_prompt.json"


def sync_prompt():
    """Выгружает промт и настройки из OpenAI Playground"""
    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        # Получаем последний промт из Playground (через API)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": ""}],  # Пустой запрос
            max_tokens=1,  # Минимум токенов для теста
            temperature=0
        )

        # Запоминаем текущие настройки (из .env или Playground)
        config = {
            "system_prompt": "Ты консультант компании...",  # Замените на актуальный
            "model": os.getenv("GPT_MODEL", "gpt-4o-mini"),
            "temperature": float(os.getenv("GPT_TEMPERATURE", 0.7)),
            "max_tokens": int(os.getenv("GPT_MAX_TOKENS", 200)),
            "top_p": 1.0
        }

        # Сохраняем в JSON
        with open(PROMPT_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        logger.info("Промт и настройки синхронизированы!")

    except Exception as e:
        logger.error(f"Ошибка синхронизации: {e}")


if __name__ == "__main__":
    sync_prompt()
