"""DAO cho bang pet_care_media."""
from __future__ import annotations

from typing import Any

from ..db import execute, fetch_all


def create(
    stay_id: int,
    care_log_id: int | None,
    media_type: str,
    file_path: str,
    caption: str | None,
) -> int:
    return execute(
        """
        INSERT INTO pet_care_media (stay_id, care_log_id, media_type, file_path, caption)
        VALUES (%s,%s,%s,%s,%s)
        """,
        (stay_id, care_log_id, media_type, file_path, caption),
    )


def list_by_stay(stay_id: int, limit: int = 100) -> list[dict[str, Any]]:
    return fetch_all(
        """
        SELECT * FROM pet_care_media
        WHERE stay_id=%s
        ORDER BY created_at DESC, id DESC
        LIMIT %s
        """,
        (stay_id, int(limit)),
    )
