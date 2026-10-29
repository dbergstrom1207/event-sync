import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.request import urlopen, Request
from urllib.error import HTTPError
from event_sync.server import make_server, load_snapshot


class APITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = make_server(
            Path(__file__).resolve().parent.parent / "data", port=0
        )
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def get(self, path):
        with urlopen(self.base + path) as r:
            return json.load(r)

    def test_provided_dataset_totals(self):
        r = self.get("/api/meetings")
        self.assertEqual(
            r["summary"],
            {
                "input_records": 42,
                "meetings": 29,
                "matched": 13,
                "conflicts": 13,
                "review": 14,
                "duplicates_collapsed": 0,
            },
        )

    def test_detail_and_filters(self):
        r = self.get("/api/meetings?filter=conflicts")
        self.assertEqual(r["total"], 13)
        m = r["meetings"][0]
        self.assertEqual(self.get("/api/meetings/" + m["id"]), m)
        self.assertEqual(self.get("/api/meetings?q=notfound")["total"], 0)
        self.assertEqual(self.get("/api/meetings?filter=review")["total"], 14)

    def test_search_by_original_id_and_client(self):
        self.assertEqual(self.get("/api/meetings?q=CRM-1002")["total"], 1)
        self.assertEqual(
            self.get("/api/meetings?q=CAL-A2")["total"], 4
        )  # A2, A20, A21, A22
        self.assertEqual(self.get("/api/meetings?q=Mark%20Johnson")["total"], 1)

    def test_errors(self):
        for path, status in [
            ("/api/meetings/nope", 404),
            ("/api/meetings?filter=bad", 400),
            ("/api/meetings?q=a&q=b", 400),
            ("/api/meetings?unknown=1", 400),
            ("/data/crm_events.json", 404),
            ("/../app.py", 404),
        ]:
            with self.subTest(path=path), self.assertRaises(HTTPError) as raised:
                urlopen(self.base + path)
            self.assertEqual(raised.exception.code, status)

    def test_assets_and_health(self):
        self.assertEqual(self.get("/api/health")["status"], "ok")
        for path, content_type in [
            ("/", "text/html"),
            ("/app.js", "text/javascript"),
            ("/styles.css", "text/css"),
        ]:
            with urlopen(self.base + path) as response:
                self.assertIn(content_type, response.headers["Content-Type"])
                self.assertIn(
                    "default-src 'self'", response.headers["Content-Security-Policy"]
                )
                self.assertGreater(len(response.read()), 100)

    def test_post_disallowed(self):
        with self.assertRaises(HTTPError) as raised:
            urlopen(Request(self.base + "/api/meetings", data=b"{}"))
        self.assertEqual(raised.exception.code, 405)

    def test_bad_files_fail_startup(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(ValueError):
                load_snapshot(root)
            (root / "calendar_events.json").write_text("[]")
            for invalid in ("{", "{}", "[NaN]"):
                (root / "crm_events.json").write_text(invalid)
                with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                    load_snapshot(root)
