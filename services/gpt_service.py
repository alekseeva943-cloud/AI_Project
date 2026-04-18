import asyncio
import logging
from openai import OpenAI

from config.config import (
    OPENAI_API_KEY,
    GPT_MODEL,
    GPT_TEMPERATURE,
    GPT_MAX_TOKENS,
    GPT_TIMEOUT
)

logger = logging.getLogger(__name__)

client = OpenAI(api_key=OPENAI_API_KEY)


async def ask_gpt(messages: list[dict]) -> str:
    """
    Универсальный вызов GPT.

    messages = [
        {"role": "system", "content": "..."},
        {"role": "user", "content": "..."}
    ]
    """

    try:
        response = await asyncio.wait_for(
            asyncio.to_thread(
                client.chat.completions.create,
                model=GPT_MODEL,
                messages=messages,
                temperature=GPT_TEMPERATURE,
                max_tokens=GPT_MAX_TOKENS
            ),
            timeout=GPT_TIMEOUT
        )

        content = response.choices[0].message.content

        if not content or not content.strip():
            logger.warning("GPT вернул пустой ответ")
            return "⚠️ Уточните, пожалуйста, вопрос"

        return content.strip()

    except asyncio.TimeoutError:
        logger.warning("Таймаут GPT")
        return "⚠️ Сервер перегружен, попробуйте ещё раз"

    except Exception as e:
        logger.error(f"Ошибка GPT: {type(e).__name__}", exc_info=True)
        return "🔧 Ошибка сервиса"
