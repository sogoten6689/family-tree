from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


class HistoryRepository:
    def __init__(self) -> None:
        self._engine: Optional[Engine] = None
        self._enabled = False
        self._init_error: Optional[str] = None

        mysql_host = os.getenv("MYSQL_HOST")
        mysql_port = os.getenv("MYSQL_PORT", "3306")
        mysql_db = os.getenv("MYSQL_DATABASE", "family_tree")
        mysql_user = os.getenv("MYSQL_USER")
        mysql_password = os.getenv("MYSQL_PASSWORD")

        if not mysql_host or not mysql_user or not mysql_password:
            self._init_error = "MySQL env vars are missing. Use in-memory history fallback."
            return

        url = (
            f"mysql+pymysql://{mysql_user}:{mysql_password}@{mysql_host}:{mysql_port}/{mysql_db}"
            "?charset=utf8mb4"
        )

        try:
            self._engine = create_engine(url, pool_pre_ping=True, future=True)
            self._ensure_schema()
            self._enabled = True
        except Exception as exc:  # pragma: no cover - safety for infra issues
            self._init_error = str(exc)
            self._engine = None
            self._enabled = False

    @property
    def enabled(self) -> bool:
        return self._enabled and self._engine is not None

    @property
    def init_error(self) -> Optional[str]:
        return self._init_error

    def _ensure_schema(self) -> None:
        if not self._engine:
            return

        ddl = """
        CREATE TABLE IF NOT EXISTS request_history (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            request_id VARCHAR(64) NOT NULL UNIQUE,
            created_at VARCHAR(64) NOT NULL,
            source VARCHAR(100) NOT NULL,
            metadata_json JSON NOT NULL,
            analysis_json JSON NULL,
            people_count INT NOT NULL,
            relationship_count INT NOT NULL,
            warning_count INT NOT NULL,
            created_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """

        with self._engine.begin() as conn:
            conn.execute(text(ddl))
            # Backward compatibility for existing tables created before analysis_json.
            has_analysis_column = conn.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA = DATABASE()
                      AND TABLE_NAME = 'request_history'
                      AND COLUMN_NAME = 'analysis_json'
                    """
                )
            ).scalar_one()

            if int(has_analysis_column or 0) == 0:
                conn.execute(text("ALTER TABLE request_history ADD COLUMN analysis_json JSON NULL"))

    def append(self, item: Dict[str, Any]) -> bool:
        if not self.enabled or not self._engine:
            return False

        stmt = text(
            """
            INSERT INTO request_history (
                request_id, created_at, source, metadata_json, analysis_json,
                people_count, relationship_count, warning_count
            ) VALUES (
                :request_id, :created_at, :source, CAST(:metadata_json AS JSON), CAST(:analysis_json AS JSON),
                :people_count, :relationship_count, :warning_count
            )
            ON DUPLICATE KEY UPDATE
                source = VALUES(source),
                metadata_json = VALUES(metadata_json),
                analysis_json = VALUES(analysis_json),
                people_count = VALUES(people_count),
                relationship_count = VALUES(relationship_count),
                warning_count = VALUES(warning_count);
            """
        )

        try:
            with self._engine.begin() as conn:
                conn.execute(
                    stmt,
                    {
                        "request_id": item["request_id"],
                        "created_at": item["created_at"],
                        "source": item["source"],
                        "metadata_json": json.dumps(item.get("metadata", {}), ensure_ascii=False),
                        "analysis_json": json.dumps(item.get("analysis", {}), ensure_ascii=False),
                        "people_count": int(item["people_count"]),
                        "relationship_count": int(item["relationship_count"]),
                        "warning_count": int(item["warning_count"]),
                    },
                )
            return True
        except Exception:
            return False

    def list_recent(self, limit: int) -> Tuple[int, List[Dict[str, Any]]]:
        if not self.enabled or not self._engine:
            return 0, []

        q_count = text("SELECT COUNT(*) AS total FROM request_history")
        q_rows = text(
            """
            SELECT request_id, created_at, source, metadata_json,
                   people_count, relationship_count, warning_count
            FROM request_history
            ORDER BY id DESC
            LIMIT :limit;
            """
        )

        try:
            with self._engine.connect() as conn:
                total = int(conn.execute(q_count).scalar_one())
                rows = conn.execute(q_rows, {"limit": limit}).mappings().all()

            items: List[Dict[str, Any]] = []
            for row in rows:
                raw_metadata = row["metadata_json"]
                if isinstance(raw_metadata, str):
                    try:
                        metadata = json.loads(raw_metadata)
                    except Exception:
                        metadata = {}
                else:
                    metadata = raw_metadata or {}

                items.append(
                    {
                        "request_id": row["request_id"],
                        "created_at": row["created_at"],
                        "source": row["source"],
                        "metadata": metadata,
                        "people_count": int(row["people_count"]),
                        "relationship_count": int(row["relationship_count"]),
                        "warning_count": int(row["warning_count"]),
                    }
                )

            return total, items
        except Exception:
            return 0, []

    def clear(self) -> Optional[int]:
        if not self.enabled or not self._engine:
            return None

        stmt = text("DELETE FROM request_history")
        try:
            with self._engine.begin() as conn:
                result = conn.execute(stmt)
                return int(result.rowcount or 0)
        except Exception:
            return None

    def get_detail(self, request_id: str) -> Optional[Dict[str, Any]]:
        if not self.enabled or not self._engine:
            return None

        q = text(
            """
            SELECT analysis_json
            FROM request_history
            WHERE request_id = :request_id
            LIMIT 1;
            """
        )

        try:
            with self._engine.connect() as conn:
                row = conn.execute(q, {"request_id": request_id}).mappings().first()
            if not row:
                return None

            raw = row.get("analysis_json")
            if raw is None:
                return None
            if isinstance(raw, str):
                return json.loads(raw)
            return raw
        except Exception:
            return None
