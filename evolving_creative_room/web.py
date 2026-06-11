from __future__ import annotations

import argparse
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from evolving_creative_room.models import FeedbackSignal
from evolving_creative_room.orchestration import CreativeRoomRunner


PROJECT_ROOT = Path(__file__).resolve().parents[1]
STATIC_ROOT = PROJECT_ROOT / "evolving_creative_room" / "static"


class CreativeRoomWebHandler(BaseHTTPRequestHandler):
    runner: CreativeRoomRunner

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        if path == "/" or path.startswith("/chat/") or path == "/assets" or path.startswith("/asset/") or path == "/profile" or path == "/publish" or path.startswith("/publish/") or path == "/settings" or path.startswith("/settings/"):
            self._serve_file(STATIC_ROOT / "index.html", "text/html; charset=utf-8")
            return
        if path in {"/app.js", "/styles.css"}:
            content_type = "application/javascript; charset=utf-8" if path.endswith(".js") else "text/css; charset=utf-8"
            self._serve_file(STATIC_ROOT / path.lstrip("/"), content_type)
            return
        if path.startswith("/assets/"):
            suffix = Path(path).suffix.lower()
            content_type = "image/png" if suffix == ".png" else "image/jpeg" if suffix in {".jpg", ".jpeg"} else "application/octet-stream"
            self._serve_file(STATIC_ROOT / path.lstrip("/"), content_type)
            return
        if path.startswith("/media/"):
            suffix = Path(path).suffix.lower()
            content_type = "image/png" if suffix == ".png" else "image/jpeg" if suffix in {".jpg", ".jpeg"} else "image/webp" if suffix == ".webp" else "application/octet-stream"
            self._serve_file(self.runner.media_dir / Path(path).name, content_type)
            return
        if path == "/api/sessions":
            self._json({"sessions": self.runner.memory.list_sessions()})
            return
        if path == "/api/assets":
            self._json(self.runner.assets_view(project_id=_first(query, "project_id") or "default"))
            return
        if path == "/api/posts":
            include_drafts = (_first(query, "include_drafts") or "").lower() in {"1", "true", "yes"}
            self._json(self.runner.published_posts_view(include_drafts=include_drafts, project_id=_first(query, "project_id") or "default"))
            return
        if path.startswith("/api/post/"):
            post_id = path.rsplit("/", 1)[-1]
            self._json(self.runner.post_view(post_id))
            return
        if path.startswith("/api/asset/"):
            asset_id = path.rsplit("/", 1)[-1]
            self._json(self.runner.asset_view(asset_id))
            return
        if path == "/api/config":
            self._json({"llm": self.runner.llm_info()})
            return
        if path == "/api/capabilities":
            self._json(self.runner.capabilities_view())
            return
        if path == "/api/settings":
            self._json(self.runner.settings_view())
            return
        if path == "/api/projects":
            self._json(self.runner.project_view())
            return
        if path == "/api/memory":
            self._json(self.runner.memory_view(_first(query, "q"), project_id=_first(query, "project_id") or "default"))
            return
        if path == "/api/preferences":
            self._json(self.runner.preferences_view())
            return
        if path == "/api/knowledge":
            self._json(
                self.runner.knowledge_view(
                    query=_first(query, "q"),
                    kind=_first(query, "kind") or None,
                    project_id=_first(query, "project_id") or "default",
                )
            )
            return
        if path == "/api/evaluations":
            self._json(self.runner.evaluation_view())
            return
        if path == "/api/observability":
            self._json(self.runner.observability_view())
            return
        if path == "/api/data/doctor":
            self._json(self.runner.data_doctor())
            return
        if path.startswith("/api/session/"):
            session_id = path.rsplit("/", 1)[-1]
            self._json(self.runner.session_view(session_id))
            return
        self._json({"error": "not_found"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            if path == "/api/session":
                payload = self._read_json()
                request = str(payload.get("request", "")).strip()
                if not request:
                    self._json({"error": "missing_request"}, HTTPStatus.BAD_REQUEST)
                    return
                preferences = _split_lines(str(payload.get("preferences", "")))
                project_id = str(payload.get("project_id", "default")).strip() or "default"
                capability_id = str(payload.get("capability_id", "")).strip()
                state = self.runner.run_seed_session(request, user_preferences=preferences, project_id=project_id, capability_id=capability_id)
                self._json(self.runner.session_view(state.session_id), HTTPStatus.CREATED)
                return
            if path == "/api/workflow/preview":
                payload = self._read_json()
                request = str(payload.get("request", "")).strip()
                preferences = _split_lines(str(payload.get("preferences", "")))
                project_id = str(payload.get("project_id", "default")).strip() or "default"
                capability_id = str(payload.get("capability_id", "")).strip()
                self._json(self.runner.workflow_preview(request, preferences=preferences, project_id=project_id, capability_id=capability_id))
                return
            self._do_post_inner(path)
        except (FileNotFoundError, ValueError) as exc:
            self._json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)

    def _do_post_inner(self, path: str) -> None:
        if path == "/api/projects":
            payload = self._read_json()
            project = self.runner.create_project(
                name=str(payload.get("name", "")).strip(),
                description=str(payload.get("description", "")).strip(),
                tags=_split_lines(str(payload.get("tags", ""))),
            )
            self._json({"project": project}, HTTPStatus.CREATED)
            return
        if path == "/api/knowledge":
            payload = self._read_json()
            record = self.runner.add_knowledge(
                kind=str(payload.get("kind", "project")).strip() or "project",
                title=str(payload.get("title", "")).strip(),
                content=str(payload.get("content", "")).strip(),
                project_id=str(payload.get("project_id", "default")).strip() or "default",
                source=str(payload.get("source", "")).strip(),
                tags=_split_lines(str(payload.get("tags", ""))),
            )
            self._json({"record": record}, HTTPStatus.CREATED)
            return
        if path == "/api/assets/collect":
            payload = self._read_json()
            self._json({"asset": self.runner.collect_asset(payload)}, HTTPStatus.CREATED)
            return
        if path == "/api/assets/uncollect":
            payload = self._read_json()
            self._json({"asset": self.runner.uncollect_asset(payload)}, HTTPStatus.CREATED)
            return
        if path == "/api/assets/like":
            payload = self._read_json()
            self._json({"asset": self.runner.like_asset(payload)}, HTTPStatus.CREATED)
            return
        if path == "/api/publish/draft":
            payload = self._read_json()
            post = self.runner.create_publish_draft(str(payload.get("work_id", "")).strip())
            self._json({"post": post, "default_tags": self.runner.published_posts_view()["default_tags"]}, HTTPStatus.CREATED)
            return
        if path.startswith("/api/post/"):
            post_id = path.rsplit("/", 1)[-1]
            payload = self._read_json()
            post = self.runner.update_post(post_id, payload)
            self._json({"post": post, "default_tags": self.runner.published_posts_view()["default_tags"]})
            return
        if path == "/api/memory/review":
            payload = self._read_json()
            result = self.runner.review_memory(
                record_id=str(payload.get("record_id", "")).strip(),
                status=str(payload.get("status", "active")).strip() or "active",
            )
            self._json(result)
            return
        if path == "/api/preferences/delete":
            payload = self._read_json()
            self._json(self.runner.delete_preference(str(payload.get("record_id", "")).strip()))
            return
        if path.startswith("/api/learning/"):
            candidate_id = path.rsplit("/", 1)[-1]
            payload = self._read_json()
            result = self.runner.apply_learning(
                candidate_id=candidate_id,
                action=str(payload.get("action", "")).strip(),
            )
            self._json(result)
            return
        if path == "/api/evaluations/run":
            self._json(self.runner.run_evaluation_suite(), HTTPStatus.CREATED)
            return
        if path == "/api/evaluations/ab":
            payload = self._read_json()
            self._json(
                self.runner.run_ab_evaluation(
                    session_id=str(payload.get("session_id", "")).strip() or None,
                    proposal_id=str(payload.get("proposal_id", "")).strip() or None,
                ),
                HTTPStatus.CREATED,
            )
            return
        if path == "/api/llm/test":
            self._json(self.runner.test_llm())
            return
        if path == "/api/knowledge/import-url":
            payload = self._read_json()
            record = self.runner.import_knowledge_url(
                url=str(payload.get("url", "")).strip(),
                kind=str(payload.get("kind", "norm")).strip() or "norm",
                project_id=str(payload.get("project_id", "default")).strip() or "default",
                tags=_split_lines(str(payload.get("tags", ""))),
            )
            self._json({"record": record}, HTTPStatus.CREATED)
            return
        if path == "/api/settings":
            payload = self._read_json()
            self._json(self.runner.update_settings(payload))
            return
        if path == "/api/data/rebuild-index":
            self._json(self.runner.rebuild_indexes(), HTTPStatus.CREATED)
            return
        if path.startswith("/api/session/") and path.endswith("/feedback"):
            session_id = path.split("/")[-2]
            payload = self._read_json()
            signal = FeedbackSignal(str(payload.get("signal", "edit")))
            note = str(payload.get("note", "")).strip()
            edited_text = str(payload.get("edited_text", "")).strip() or None
            state = self.runner.record_feedback(session_id, signal=signal, note=note, edited_text=edited_text)
            self._json(self.runner.session_view(state.session_id))
            return
        if path.startswith("/api/session/") and path.endswith("/complete"):
            session_id = path.split("/")[-2]
            payload = self._read_json()
            self._json(
                self.runner.complete_session(
                    session_id,
                    bool(payload.get("completed", True)),
                    revoke_learning_on_reopen=bool(payload.get("revoke_learning", True)),
                )
            )
            return
        if path.startswith("/api/session/") and path.endswith("/evolution/apply"):
            session_id = path.split("/")[-3]
            payload = self._read_json()
            result = self.runner.apply_evolution(
                session_id=session_id,
                proposal_id=str(payload.get("proposal_id", "")).strip(),
                reviewer_note=str(payload.get("reviewer_note", "")).strip(),
            )
            self._json(result)
            return
        if path.startswith("/api/session/") and path.endswith("/evolution/ignore"):
            session_id = path.split("/")[-3]
            payload = self._read_json()
            result = self.runner.ignore_evolution(
                session_id=session_id,
                proposal_id=str(payload.get("proposal_id", "")).strip(),
                reviewer_note=str(payload.get("reviewer_note", "")).strip(),
            )
            self._json(result)
            return
        if path.startswith("/api/session/") and "/review/" in path and (path.endswith("/accept") or path.endswith("/skip")):
            parts = path.strip("/").split("/")
            session_id = parts[2]
            item_id = unquote(parts[4])
            payload = self._read_json()
            if path.endswith("/accept"):
                result = self.runner.accept_review_item(
                    session_id,
                    item_id,
                    scope=str(payload.get("scope", "")).strip(),
                    reviewer_note=str(payload.get("reviewer_note", "")).strip(),
                )
            else:
                result = self.runner.skip_review_item(
                    session_id,
                    item_id,
                    reviewer_note=str(payload.get("reviewer_note", "")).strip(),
                )
            self._json(result)
            return
        self._json({"error": "not_found"}, HTTPStatus.NOT_FOUND)

    def do_PATCH(self) -> None:
        path = urlparse(self.path).path
        if path.startswith("/api/session/"):
            session_id = path.split("/")[-1]
            payload = self._read_json()
            result = self.runner.update_session_meta(
                session_id=session_id,
                title=str(payload.get("title", "")).strip() if "title" in payload else None,
                pinned=bool(payload.get("pinned")) if "pinned" in payload else None,
            )
            self._json(result)
            return
        self._json({"error": "not_found"}, HTTPStatus.NOT_FOUND)

    def do_DELETE(self) -> None:
        path = urlparse(self.path).path
        try:
            if path.startswith("/api/asset/"):
                asset_id = path.rsplit("/", 1)[-1]
                self._json(self.runner.delete_asset(asset_id))
                return
            if path.startswith("/api/post/"):
                post_id = path.rsplit("/", 1)[-1]
                self._json(self.runner.delete_post(post_id))
                return
            if path.startswith("/api/session/"):
                session_id = path.split("/")[-1]
                payload = self._read_json()
                mode = str(payload.get("mode", "revoke_memory")).strip() or "revoke_memory"
                self._json(self.runner.delete_session(session_id, mode=mode))
                return
            self._json({"error": "not_found"}, HTTPStatus.NOT_FOUND)
        except (FileNotFoundError, ValueError) as exc:
            self._json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)

    def log_message(self, format: str, *args: object) -> None:
        return

    def _read_json(self) -> dict[str, object]:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        data = self.rfile.read(length).decode("utf-8")
        return json.loads(data) if data else {}

    def _json(self, payload: dict[str, object], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_file(self, path: Path, content_type: str) -> None:
        if not path.exists():
            self._json({"error": "not_found"}, HTTPStatus.NOT_FOUND)
            return
        body = path.read_bytes()
        self.send_response(HTTPStatus.OK.value)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _split_lines(value: str) -> list[str]:
    return [line.strip() for line in value.replace("；", "\n").replace(";", "\n").splitlines() if line.strip()]


def _first(query: dict[str, list[str]], name: str) -> str:
    values = query.get(name, [])
    return values[0].strip() if values else ""


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the EcRoom local web app.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--workspace", default=".ecr_workspace")
    args = parser.parse_args()

    runner = CreativeRoomRunner(Path(args.workspace))

    class Handler(CreativeRoomWebHandler):
        pass

    Handler.runner = runner
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"EcRoom is running at http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
