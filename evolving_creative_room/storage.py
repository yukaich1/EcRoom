from __future__ import annotations

import json
import os
from pathlib import Path
from uuid import uuid4


def atomic_write_text(path: Path, content: str, *, encoding: str = "utf-8") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        temp_path.write_text(content, encoding=encoding)
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def atomic_write_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        temp_path.write_bytes(content)
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def atomic_write_json(path: Path, payload: object, *, indent: int = 2) -> None:
    atomic_write_text(path, json.dumps(payload, ensure_ascii=False, indent=indent))


def atomic_write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    body = "\n".join(json.dumps(item, ensure_ascii=False) for item in rows)
    atomic_write_text(path, body + ("\n" if rows else ""))
