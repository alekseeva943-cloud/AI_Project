# handlers/utilities/__init__.py

"""
Модуль служебных обработчиков.

Экспортирует функции меню,
контактов, услуг и регистрации
обработчиков.
"""

from .contacts import (
    handle_contact,
    show_id,
)

from .handlers import (
    get_utility_handlers,
)

from .menu import (
    cancel_current_action,
    go_back,
    show_help_menu,
    show_main_menu,
)

from .services import (
    handle_help_choice,
    handle_services,
    show_auto_help_details,
    show_auto_help_submenu,
    show_contacts,
    show_service_details,
)

__all__ = [
    "cancel_current_action",
    "get_utility_handlers",
    "go_back",
    "handle_contact",
    "handle_help_choice",
    "handle_services",
    "show_auto_help_details",
    "show_auto_help_submenu",
    "show_contacts",
    "show_help_menu",
    "show_id",
    "show_main_menu",
    "show_service_details",
]