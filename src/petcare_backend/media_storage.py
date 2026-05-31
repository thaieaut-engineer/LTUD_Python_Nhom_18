"""Sao chep anh danh muc (pet / product) vao thu muc luu tru cua ung dung."""
from __future__ import annotations

import shutil
import uuid
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CATALOG_MEDIA_ROOT = PROJECT_ROOT / "data" / "catalog_images"


class MediaStorageError(Exception):
    pass


def _entity_dir(kind: str, entity_id: int) -> Path:
    d = CATALOG_MEDIA_ROOT / kind / str(entity_id)
    d.mkdir(parents=True, exist_ok=True)
    return d


def copy_catalog_image(kind: str, entity_id: int, source_path: str) -> str:
    """kind: 'pets' | 'products'. Tra ve duong dan file da luu."""
    src = Path(source_path)
    if not src.is_file():
        raise MediaStorageError("File không tồn tại.")
    dest = _entity_dir(kind, entity_id) / f"{uuid.uuid4().hex}_{src.name}"
    shutil.copy2(src, dest)
    return str(dest)


def remove_stored_file(path: str | None) -> None:
    """Xoa file cu trong thu muc catalog (bo qua loi / duong dan ngoai)."""
    if not path:
        return
    try:
        p = Path(path).resolve()
        root = CATALOG_MEDIA_ROOT.resolve()
        if root in p.parents and p.is_file():
            p.unlink()
    except OSError:
        pass
