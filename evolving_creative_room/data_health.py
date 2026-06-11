from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class DoctorIssue:
    severity: str
    code: str
    message: str
    path: str = ""
    ref: str = ""


class WorkspaceDoctor:
    """Check local EcRoom workspace consistency without mutating data."""

    def __init__(self, root: Path | str):
        self.root = Path(root)

    def run(self) -> dict[str, object]:
        issues: list[DoctorIssue] = []
        stats: dict[str, int] = {
            "sessions": 0,
            "memory_records": 0,
            "knowledge_records": 0,
            "posts": 0,
            "media_files": 0,
            "temp_files": 0,
        }
        self._check_temp_files(issues, stats)
        self._check_session_meta(issues)
        self._check_sessions(issues, stats)
        self._check_jsonl(self.root / "memory", "L*.jsonl", "memory", issues, stats)
        self._check_jsonl(self.root / "knowledge", "records.jsonl", "knowledge", issues, stats)
        self._check_posts(issues, stats)
        self._check_media(issues, stats)
        status = "pass"
        if any(item.severity == "error" for item in issues):
            status = "fail"
        elif issues:
            status = "warn"
        return {
            "status": status,
            "summary": {
                **stats,
                "errors": sum(1 for item in issues if item.severity == "error"),
                "warnings": sum(1 for item in issues if item.severity == "warning"),
            },
            "issues": [asdict(item) for item in issues],
        }

    def _check_session_meta(self, issues: list[DoctorIssue]) -> None:
        path = self.root / "session_meta.json"
        if not path.exists():
            return
        data = self._read_json(path, issues, "invalid_session_meta")
        if data is None:
            return
        if not isinstance(data, dict):
            issues.append(DoctorIssue("error", "invalid_session_meta", "session_meta.json must contain an object.", str(path)))
            return
        for session_id, item in data.items():
            if not isinstance(item, dict):
                issues.append(DoctorIssue("warning", "invalid_session_meta_item", "Session meta item is not an object.", str(path), str(session_id)))
                continue
            ref_path = self.root / "refs" / f"{session_id}.json"
            if not item.get("deleted") and not ref_path.exists():
                issues.append(DoctorIssue("warning", "missing_session_ref", "Session meta points to a missing session file.", str(ref_path), str(session_id)))

    def _check_temp_files(self, issues: list[DoctorIssue], stats: dict[str, int]) -> None:
        if not self.root.exists():
            return
        for path in self.root.rglob("*.tmp"):
            if not path.is_file():
                continue
            stats["temp_files"] += 1
            issues.append(DoctorIssue("warning", "stale_temp_file", "A temporary write file was left behind.", str(path)))

    def _check_sessions(self, issues: list[DoctorIssue], stats: dict[str, int]) -> None:
        refs_dir = self.root / "refs"
        if not refs_dir.exists():
            return
        for path in refs_dir.glob("session_*.json"):
            data = self._read_json(path, issues, "invalid_session_json")
            if not isinstance(data, dict):
                continue
            stats["sessions"] += 1
            session_id = str(data.get("session_id", ""))
            if not session_id:
                issues.append(DoctorIssue("error", "missing_session_id", "Session file has no session_id.", str(path)))
            elif path.name != f"{session_id}.json":
                issues.append(DoctorIssue("warning", "session_id_filename_mismatch", "Session id does not match filename.", str(path), session_id))
            intent = data.get("intent")
            if not isinstance(intent, dict) or not str(intent.get("raw_request", "")).strip():
                issues.append(DoctorIssue("warning", "missing_raw_request", "Session has no raw request.", str(path), session_id))
            if not isinstance(data.get("drafts", []), list):
                issues.append(DoctorIssue("warning", "invalid_drafts", "Session drafts must be a list.", str(path), session_id))

    def _check_jsonl(
        self,
        directory: Path,
        pattern: str,
        kind: str,
        issues: list[DoctorIssue],
        stats: dict[str, int],
    ) -> None:
        if not directory.exists():
            return
        key = "memory_records" if kind == "memory" else "knowledge_records"
        for path in directory.glob(pattern):
            for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError as exc:
                    issues.append(DoctorIssue("error", f"invalid_{kind}_jsonl", f"Invalid JSONL at line {index}: {exc}", str(path)))
                    continue
                stats[key] += 1
                if not isinstance(row, dict):
                    issues.append(DoctorIssue("warning", f"invalid_{kind}_row", f"{kind} row is not an object.", str(path)))
                    continue
                if not str(row.get("record_id", "")).strip():
                    issues.append(DoctorIssue("warning", f"missing_{kind}_record_id", f"{kind} row has no record_id.", str(path)))

    def _check_posts(self, issues: list[DoctorIssue], stats: dict[str, int]) -> None:
        path = self.root / "published_posts.json"
        if not path.exists():
            return
        data = self._read_json(path, issues, "invalid_posts_json")
        if data is None:
            return
        if not isinstance(data, list):
            issues.append(DoctorIssue("error", "invalid_posts_json", "published_posts.json must contain a list.", str(path)))
            return
        for post in data:
            if not isinstance(post, dict):
                continue
            stats["posts"] += 1
            if not str(post.get("post_id", "")).strip():
                issues.append(DoctorIssue("warning", "missing_post_id", "Published post has no post_id.", str(path)))
            cover_url = str(post.get("cover_url", ""))
            if cover_url.startswith("/media/") and not (self.root / "media" / Path(cover_url).name).exists():
                issues.append(DoctorIssue("warning", "missing_post_media", "Post cover media is missing.", str(path), cover_url))

    def _check_media(self, issues: list[DoctorIssue], stats: dict[str, int]) -> None:
        media_dir = self.root / "media"
        if not media_dir.exists():
            return
        for path in media_dir.iterdir():
            if path.is_file():
                stats["media_files"] += 1
                if path.stat().st_size == 0:
                    issues.append(DoctorIssue("warning", "empty_media_file", "Media file is empty.", str(path)))

    def _read_json(self, path: Path, issues: list[DoctorIssue], code: str) -> Any | None:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            issues.append(DoctorIssue("error", code, f"Invalid JSON: {exc}", str(path)))
        except OSError as exc:
            issues.append(DoctorIssue("error", "unreadable_file", str(exc), str(path)))
        return None
