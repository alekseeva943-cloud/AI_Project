"""
cost_tracker.py

Отвечает за подсчёт токенов и стоимости.
"""

from app.config.settings import PRICE_PER_1K_TOKENS, USD_TO_RUB


class CostTracker:
    def __init__(self):
        self.total_tokens = 0

    def add_tokens(self, tokens: int):
        self.total_tokens += tokens

    def get_cost_usd(self):
        return (self.total_tokens / 1000) * PRICE_PER_1K_TOKENS

    def get_cost_rub(self):
        return self.get_cost_usd() * USD_TO_RUB

    def get_stats(self):
        return {
            "tokens": self.total_tokens,
            "usd": round(self.get_cost_usd(), 4),
            "rub": round(self.get_cost_rub(), 2),
        }
