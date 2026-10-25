"""A tiny SQLite corpus with versions, access labels, and verifiable citations."""

from __future__ import annotations

import hashlib
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from chunking import Chunk


@dataclass(frozen=True)
class SearchResult:
    chunk_id: str
    source_id: str
    source_path: str
    version: str
    locator: str
    permission: str
    text: str
    score: int


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _terms(text: str) -> set[str]:
    """Return English words and adjacent Chinese character pairs."""
    terms = set(re.findall(r"[a-z0-9]+", text.lower()))
    for run in re.findall(r"[\u4e00-\u9fff]+", text):
        if len(run) == 1:
            terms.add(run)
        else:
            terms.update(run[index : index + 2] for index in range(len(run) - 1))
    return terms


class KnowledgeBase:
    """Store small teaching corpora in one SQLite database file."""

    def __init__(self, database_path: Path) -> None:
        self.connection = sqlite3.connect(database_path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS sources (
                source_id TEXT PRIMARY KEY,
                source_path TEXT NOT NULL,
                version TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                permission TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS chunks (
                chunk_id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL REFERENCES sources(source_id)
                    ON DELETE CASCADE,
                version TEXT NOT NULL,
                locator TEXT NOT NULL,
                permission TEXT NOT NULL,
                text TEXT NOT NULL
            );
            """
        )
        self.connection.commit()

    def replace_source(
        self,
        source_id: str,
        source_path: str,
        version: str,
        permission: str,
        chunks: list[Chunk],
    ) -> bool:
        """Atomically replace one source; return False when its content is unchanged."""
        content_hash = _sha256(
            "\n".join(
                f"{chunk.permission or permission}\0{chunk.text}" for chunk in chunks
            )
        )
        current = self.connection.execute(
            "SELECT source_path, content_hash, version, permission "
            "FROM sources WHERE source_id = ?",
            (source_id,),
        ).fetchone()
        if current and (
            current["content_hash"],
            current["version"],
            current["permission"],
            current["source_path"],
        ) == (content_hash, version, permission, source_path):
            return False

        with self.connection:
            self.connection.execute(
                "DELETE FROM sources WHERE source_id = ?", (source_id,)
            )
            self.connection.execute(
                "INSERT INTO sources VALUES (?, ?, ?, ?, ?)",
                (source_id, source_path, version, content_hash, permission),
            )
            for chunk in chunks:
                chunk_id = _sha256(
                    f"{source_id}\0{version}\0{chunk.chunk_index}\0{chunk.text}"
                )
                self.connection.execute(
                    "INSERT INTO chunks VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        chunk_id,
                        source_id,
                        version,
                        chunk.locator,
                        chunk.permission or permission,
                        chunk.text,
                    ),
                )
        return True

    def delete_source(self, source_id: str) -> None:
        """Delete a source and its chunks together."""
        with self.connection:
            self.connection.execute(
                "DELETE FROM sources WHERE source_id = ?", (source_id,)
            )

    def search(
        self, query: str, allowed_permissions: set[str], limit: int = 5
    ) -> list[SearchResult]:
        """Run a transparent lexical baseline after enforcing access labels."""
        if limit <= 0:
            raise ValueError("limit 必须大于 0")
        query_terms = _terms(query)
        rows = self.connection.execute(
            "SELECT chunks.*, sources.source_path "
            "FROM chunks JOIN sources USING (source_id) "
            "ORDER BY chunks.source_id, chunks.chunk_id"
        ).fetchall()
        results = []
        for row in rows:
            if row["permission"] not in allowed_permissions:
                continue
            score = len(query_terms & _terms(row["text"]))
            if score:
                results.append(SearchResult(**dict(row), score=score))
        return sorted(results, key=lambda result: (-result.score, result.source_id))[
            :limit
        ]

    def count_chunks(self, source_id: str | None = None) -> int:
        """Count indexed chunks, optionally for one source."""
        if source_id is None:
            row = self.connection.execute("SELECT COUNT(*) FROM chunks").fetchone()
        else:
            row = self.connection.execute(
                "SELECT COUNT(*) FROM chunks WHERE source_id = ?", (source_id,)
            ).fetchone()
        return int(row[0])

    def close(self) -> None:
        self.connection.close()
