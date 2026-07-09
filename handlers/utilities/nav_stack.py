"""
handlers/utilities/nav_stack.py

Чистая логика работы со стеком навигации.
Вынесено в отдельный файл, чтобы избежать циклических импортов
между меню, навигацией и модулями админки.
"""

STACK_KEY = "nav_stack"


def push_state(
    context, 
    state_name: str
) -> None:
    """
    Сохраняет текущее состояние в стек перед переходом в подменю.
    """
    stack = context.user_data.get(STACK_KEY, [])
    stack.append(state_name)
    context.user_data[STACK_KEY] = stack


def pop_state(context) -> str | None:
    """
    Достаёт предыдущее состояние из стека (и удаляет его оттуда).
    Если стек пуст — возвращает None.
    """
    stack = context.user_data.get(STACK_KEY, [])
    if stack:
        return stack.pop()
    return None


def clear_stack(context) -> None:
    """
    Полностью очищает стек навигации.
    Вызывается при выходе в главное меню пользователя.
    """
    context.user_data[STACK_KEY] = []


def get_current_state(context) -> str | None:
    """
    Возвращает текущее состояние (верхушку стека) без его удаления.
    """
    stack = context.user_data.get(STACK_KEY, [])
    return stack[-1] if stack else None