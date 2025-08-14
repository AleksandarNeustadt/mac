# =============================================================================
# File:       system/managers/event_manager.py
# Purpose:    CRUD sloj iznad EventHandler-a za modularni event sistem
# Author:     Aleksandar Popović
# Created:    2025-08-07
# Updated:    2025-08-07
# =============================================================================

from system.handlers.event_handler import EventHandler

class EventManager:
    @staticmethod
    def initialize():
        EventHandler.clear_all()

    @staticmethod
    def create(event_name: str, callback: callable):
        """Registruje novi listener za događaj."""
        EventHandler.register(event_name, callback)

    @staticmethod
    def read(event_name: str = None):
        """Vraća sve ili konkretne event listenere."""
        return EventHandler.get_listeners(event_name)

    @staticmethod
    def update(event_name: str, index: int, new_callback: callable):
        """Zamenjuje postojeći listener novim (po indeksu)."""
        listeners = EventHandler.get_listeners(event_name)
        if (
            event_name in EventHandler._listeners and
            0 <= index < len(listeners)
        ):
            EventHandler._listeners[event_name][index] = new_callback

    @staticmethod
    def delete(event_name: str = None, index: int = None):
        """Briše sve evente, sve listenere za događaj, ili jedan listener po indeksu."""
        if event_name is None:
            EventHandler.clear_all()
        elif index is None:
            EventHandler.clear_event(event_name)
        else:
            EventHandler.remove_listener(event_name, index)

    @staticmethod
    def emit(event_name: str, data=None):
        """Emitovanje događaja sa opcionim podacima."""
        EventHandler.emit(event_name, data)

    @staticmethod
    def on(event_name: str, callback: callable):
        """Alias za create() — kraći API za registraciju događaja."""
        EventManager.create(event_name, callback)
