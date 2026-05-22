from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class TencentVectorConfig:
    url: str
    username: str
    key: str
    database: str

    @classmethod
    def from_env(cls) -> "TencentVectorConfig":
        url = os.environ.get("TENCENT_VECTORDB_URL", "").strip()
        username = os.environ.get("TENCENT_VECTORDB_USERNAME", "").strip()
        key = os.environ.get("TENCENT_VECTORDB_KEY", "").strip()
        database = os.environ.get("TENCENT_VECTORDB_DATABASE", "ecroom").strip()
        missing = [
            name
            for name, value in {
                "TENCENT_VECTORDB_URL": url,
                "TENCENT_VECTORDB_USERNAME": username,
                "TENCENT_VECTORDB_KEY": key,
            }.items()
            if not value
        ]
        if missing:
            raise RuntimeError("Tencent VectorDB 缺少配置：" + ", ".join(missing))
        return cls(url=url, username=username, key=key, database=database)


class TencentVectorIndex:
    """Tencent VectorDB adapter boundary.

    The concrete SDK calls are isolated here so product code can use the same
    VectorIndex API with Chroma locally and Tencent VectorDB in production.
    """

    def __init__(self, root: Path, collection_name: str, dimensions: int) -> None:
        self.root = root
        self.collection_name = collection_name
        self.dimensions = dimensions
        self.config = TencentVectorConfig.from_env()
        try:
            import tcvectordb  # type: ignore
        except Exception as exc:
            raise RuntimeError("未安装 Tencent VectorDB SDK。请安装 tcvectordb 后再启用 ECROOM_VECTOR_BACKEND=tencent。") from exc
        self._sdk = tcvectordb
        raise RuntimeError("Tencent VectorDB adapter 已预留，等待账号和 SDK 参数确认后启用。")

    def upsert(self, *, record_id: str, document: str, embedding: list[float], metadata: dict[str, object]) -> None:
        raise NotImplementedError

    def query(self, *, embedding: list[float], limit: int, where: dict[str, object] | None = None) -> list[dict[str, object]]:
        raise NotImplementedError
