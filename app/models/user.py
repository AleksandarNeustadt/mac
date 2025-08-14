import re
from system.db.model import Model

class User(Model):
    table = "users"
    __schema__ = {
        "fields": {
            "id": int,
            "name": str,
            "email": str,
            "age": int,
            "created_at": str,
            "updated_at": str,
        },
        "required": {
            "create": ["name", "email"],
            "update": []  # za update “partial” je True, pa ništa nije obavezno
        },
        "defaults": {
            "age": 18
        },
        "validators": {
            "email": lambda v: bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", str(v)))
        },
        "coerce": {
            "age": int
        },
        "transform": {
            "name": str.strip
        },
        "unique": ["email"],
        "immutable": ["email"]  # primer: email nepovratan nakon kreiranja
    }
