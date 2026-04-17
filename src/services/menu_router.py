"""Menu selection routing service."""
from typing import Optional, Tuple
import logging

from src.models.conversation_state import ConversationStateEnum

logger = logging.getLogger(__name__)


class MenuRouter:
    """Route menu selections to appropriate handlers."""

    # Spanish responses for menu options
    MENU_MESSAGE = """Bienvenido 👋

Selecciona una opción:
1️⃣ Solicitar turno
2️⃣ Hablar con secretaria
3️⃣ Cancelar turno"""

    APPOINTMENT_SELECTED_MESSAGE = """Entendido. Solicitar turno 📅

Por favor, espera mientras te conectamos..."""

    SECRETARY_SELECTED_MESSAGE = """Conectando con secretaria 📞

Un momento por favor..."""

    INVALID_SELECTION_MESSAGE = """No entiendo esa opción.

Selecciona una opción:
1️⃣ Solicitar turno
2️⃣ Hablar con secretaria
3️⃣ Cancelar turno"""

    @staticmethod
    def get_menu_message() -> str:
        """Get the main menu message."""
        return MenuRouter.MENU_MESSAGE

    @staticmethod
    def route_selection(selection: Optional[str]) -> Tuple[Optional[ConversationStateEnum], str]:
        """
        Route a menu selection to appropriate handler.

        Args:
            selection: Menu selection ("1" or "2", or None if invalid)

        Returns:
            Tuple of (new_state, response_message)
            - If selection is "1": (APPOINTMENT_SELECTED, appointment message)
            - If selection is "2": (SECRETARY_SELECTED, secretary message)
            - If selection is None or invalid: (None, invalid message)
        """
        if selection == "1":
            logger.info("Routing to appointment handler")
            return ConversationStateEnum.APPOINTMENT_SELECTED, MenuRouter.APPOINTMENT_SELECTED_MESSAGE

        elif selection == "2":
            logger.info("Routing to secretary handler")
            return ConversationStateEnum.SECRETARY_SELECTED, MenuRouter.SECRETARY_SELECTED_MESSAGE

        else:
            logger.info(f"Invalid selection: {selection}")
            return None, MenuRouter.INVALID_SELECTION_MESSAGE

    @staticmethod
    def get_secretary_contact_info() -> str:
        """
        Get secretary contact information.

        Returns:
            Contact information message
        """
        # Placeholder for secretary contact info
        # In production, this would be fetched from a configuration or database
        contact_info = """📞 Contacto de secretaría:
Teléfono: +34 XXX XXX XXX
Horario: Lunes a Viernes, 9:00 - 17:00

Estamos aquí para ayudarte."""

        return contact_info
