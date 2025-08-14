# =============================================================================
# File:       system/handlers/event_handler.py
# Purpose:    Nizak sloj za upravljanje eventovima i njihovim slušaocima
# Author:     Aleksandar Popović
# Created:    2025-08-07
# Updated:    2025-08-07
# =============================================================================

class EventHandler:
    _listeners = {}

    @staticmethod
    def register(event_name: str, callback: callable):
        """Dodaje novi callback za određeni događaj."""
        if event_name not in EventHandler._listeners:
            EventHandler._listeners[event_name] = []
        EventHandler._listeners[event_name].append(callback)

    @staticmethod
    def emit(event_name: str, data=None):
        """Pokreće sve callbackove registrovane za dati događaj."""
        for callback in EventHandler._listeners.get(event_name, []):
            try:
                callback(data)
            except Exception as e:
                print(f"❌ Greška u event '{event_name}': {e}")

    @staticmethod
    def clear_all():
        """Briše sve događaje i njihove callbackove."""
        EventHandler._listeners.clear()

    @staticmethod
    def clear_event(event_name: str):
        """Briše sve callbackove vezane za određeni događaj."""
        EventHandler._listeners.pop(event_name, None)

    @staticmethod
    def remove_listener(event_name: str, index: int):
        """Briše određeni callback iz liste događaja po indeksu."""
        if (
            event_name in EventHandler._listeners and
            0 <= index < len(EventHandler._listeners[event_name])
        ):
            EventHandler._listeners[event_name].pop(index)

    @staticmethod
    def get_listeners(event_name: str = None):
        """Vraća sve registrovane događaje i callbackove."""
        if event_name:
            return EventHandler._listeners.get(event_name, [])
        return EventHandler._listeners
