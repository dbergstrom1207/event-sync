"""Load the two input files and serve the meeting API and browser page."""

import argparse
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
from urllib.parse import parse_qs, urlsplit

from .reconcile import reconcile

ROOT = Path(__file__).resolve().parent.parent
ASSETS = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
}
FILTERS = ("all", "conflicts", "review", "crm", "calendar")


def reject_invalid_constant(value):
    raise ValueError(f"Invalid JSON constant: {value}")


def load_snapshot(data_dir):
    sources = []
    for filename in ("crm_events.json", "calendar_events.json"):
        try:
            text = (Path(data_dir) / filename).read_text(encoding="utf-8")
            records = json.loads(text, parse_constant=reject_invalid_constant)
            sources.append(records)
        except (OSError, ValueError) as error:
            raise ValueError(f"Cannot load {filename}: {error}") from error
    result = reconcile(*sources)
    result["loaded_at"] = datetime.now(timezone.utc).isoformat()
    return result


def matches_filter(meeting, selected_filter):
    if selected_filter == "all":
        return True
    if selected_filter == "conflicts":
        return meeting["has_conflicts"]
    if selected_filter == "review":
        return meeting["needs_review"]
    return selected_filter in meeting["sources"]


def filter_meetings(meetings, search, selected_filter):
    results = []
    for meeting in meetings:
        if not matches_filter(meeting, selected_filter):
            continue
        values = [
            str(field["value"]) if field["value"] is not None else ""
            for field in meeting["fields"].values()
        ]
        source_ids = [str(record["source_id"] or "") for record in meeting["records"]]
        searchable_text = " ".join(values + source_ids).casefold()
        if search.casefold() in searchable_text:
            results.append(meeting)
    return results


def make_server(data_dir, host="127.0.0.1", port=8000):
    snapshot = load_snapshot(data_dir)

    class MeetingRequestHandler(BaseHTTPRequestHandler):
        def send_response_body(
            self, status, body, content_type="application/json; charset=utf-8"
        ):
            if content_type.startswith("application/json"):
                payload = json.dumps(body, ensure_ascii=False, allow_nan=False).encode()
            else:
                payload = body
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'",
            )
            self.end_headers()
            self.wfile.write(payload)

        def send_meeting_list(self, query_string):
            query = parse_qs(query_string, keep_blank_values=True)
            unknown_parameters = set(query) - {"q", "filter"}
            repeated_parameters = any(len(values) != 1 for values in query.values())
            if unknown_parameters or repeated_parameters:
                return self.send_response_body(
                    400, {"error": "Use single q and/or filter query parameters"}
                )

            selected_filter = query.get("filter", ["all"])[0]
            if selected_filter not in FILTERS:
                return self.send_response_body(
                    400,
                    {
                        "error": "filter must be all, conflicts, review, crm, or calendar"
                    },
                )
            search = query.get("q", [""])[0]
            meetings = filter_meetings(snapshot["meetings"], search, selected_filter)
            return self.send_response_body(
                200, {**snapshot, "meetings": meetings, "total": len(meetings)}
            )

        def send_meeting_detail(self, meeting_id):
            for meeting in snapshot["meetings"]:
                if meeting["id"] == meeting_id:
                    return self.send_response_body(200, meeting)
            return self.send_response_body(404, {"error": "Meeting not found"})

        def do_GET(self):
            url = urlsplit(self.path)
            if url.path == "/api/health":
                return self.send_response_body(
                    200, {"status": "ok", "loaded_at": snapshot["loaded_at"]}
                )
            if url.path == "/api/meetings":
                return self.send_meeting_list(url.query)
            if url.path.startswith("/api/meetings/"):
                return self.send_meeting_detail(url.path.removeprefix("/api/meetings/"))
            if url.path in ASSETS:
                filename, content_type = ASSETS[url.path]
                content = (ROOT / "static" / filename).read_bytes()
                return self.send_response_body(200, content, content_type)
            return self.send_response_body(404, {"error": "Not found"})

        def do_POST(self):
            self.send_response(405)
            self.send_header("Allow", "GET")
            self.send_header("Content-Length", "0")
            self.end_headers()

    return ThreadingHTTPServer((host, port), MeetingRequestHandler)


def main():
    parser = argparse.ArgumentParser(description="Event Sync Service")
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    try:
        server = make_server(args.data_dir, args.host, args.port)
    except (ValueError, OSError) as error:
        print(f"Startup failed: {error}", file=sys.stderr)
        return 1
    print(f"Event Sync ready at http://{args.host}:{server.server_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0
