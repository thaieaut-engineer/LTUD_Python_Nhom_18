"""Activity log (optional): ghi nhat ky thao tac ADMIN.

Thiet ke:
 - Log vao bang `activity_log` (neu bang chua ton tai -> silent no-op).
 - Chi log khi Session.is_admin() == True.
 - UI/service co the goi log_admin(...) sau khi thao tac thanh cong.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from mysql.connector import Error as MySQLError

from . import db
from .session import Session


def log_admin(
    action: str,
    *,
    entity: str | None = None,
    entity_id: int | None = None,
    message: str | None = None,
    extra: dict[str, Any] | None = None,
    created_at: datetime | None = None,
) -> None:
    """Ghi 1 dong activity log cho ADMIN.

    - action: short code, vd: CREATE_SERVICE, UPDATE_USER, BACKUP_DB...
    - entity/entity_id: doi tuong bi tac dong (optional)
    - message: mo ta ngan gon (optional)
    - extra: dict se duoc stringify (optional)
    """

    if not Session.is_admin():
        return

    current = Session.current()
    if current is None:
        return

    action = (action or "").strip()
    if not action:
        return

    extra_text = None
    if extra:
        try:
            extra_text = str(extra)
        except Exception:
            extra_text = None

    try:
        db.execute(
            """
            INSERT INTO activity_log
                (actor_user_id, actor_username, action, entity, entity_id, message, extra, created_at)
            VALUES
                (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                int(current.id),
                current.username,
                action,
                (entity or None),
                int(entity_id) if entity_id is not None else None,
                (message or None),
                extra_text,
                created_at or datetime.now(),
            ),
        )
    except MySQLError:
        # Optional feature: neu chua migrate bang activity_log thi bo qua.
        return

