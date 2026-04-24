"""Session singleton - luu user dang dang nhap o phia client (UI)."""
from __future__ import annotations

from .models import User


class Session:
    _current: User | None = None

    @classmethod
    def set(cls, user: User) -> None:
        cls._current = user

    @classmethod
    def clear(cls) -> None:
        cls._current = None

    @classmethod
    def current(cls) -> User | None:
        return cls._current

    @classmethod
    def require(cls) -> User:
        if cls._current is None:
            raise PermissionError("Chua dang nhap.")
        return cls._current

    @classmethod
    def is_admin(cls) -> bool:
        return cls._current is not None and cls._current.is_admin
