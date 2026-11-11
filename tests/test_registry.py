"""Tests for the registry client, including a local HTTP server."""
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote

from depgraph.registry import (
    NotFoundError, NpmRegistry, RegistryError, fetch_json)

DOCS = {
    "/left-pad": {"versions": {"1.0.0": {"dependencies": {"a": "^1"}}}},
    "/@scope/pkg": {"versions": {"2.0.0": {}}},
    "/broken": "not an object",
    "/no-versions": {"name": "x"},
}


class Handler(BaseHTTPRequestHandler):
    """Serve ``DOCS`` and a few failure cases."""

    def do_GET(self):  # noqa: N802
        """Answer a GET request."""
        path = unquote(self.path)
        if path == "/garbage":
            self.reply(200, b"{oops")
        elif path == "/boom":
            self.reply(500, b"{}")
        elif path in DOCS:
            self.reply(200, json.dumps(DOCS[path]).encode())
        else:
            self.reply(404, b"{}")

    def reply(self, code, body):
        """Send a complete response."""
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        """Keep the test output clean."""


class ServerCase(unittest.TestCase):
    """Run a real HTTP server for the duration of the tests."""

    @classmethod
    def setUpClass(cls):
        """Start the server on a free port."""
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.url = f"http://127.0.0.1:{cls.server.server_address[1]}"
        threading.Thread(target=cls.server.serve_forever,
                         daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        """Stop the server."""
        cls.server.shutdown()
        cls.server.server_close()


class FetchTests(ServerCase):
    """Network behaviour of :func:`fetch_json`."""

    def test_ok(self):
        """A JSON document is decoded."""
        data = fetch_json(self.url + "/left-pad")
        self.assertIn("1.0.0", data["versions"])

    def test_not_found(self):
        """HTTP 404 becomes NotFoundError."""
        with self.assertRaises(NotFoundError):
            fetch_json(self.url + "/missing")

    def test_server_error(self):
        """Other HTTP errors become RegistryError."""
        with self.assertRaisesRegex(RegistryError, "500"):
            fetch_json(self.url + "/boom")

    def test_invalid_json(self):
        """A malformed body is reported."""
        with self.assertRaisesRegex(RegistryError, "JSON"):
            fetch_json(self.url + "/garbage")

    def test_connection_refused(self):
        """An unreachable host is reported."""
        with self.assertRaises(RegistryError):
            fetch_json("http://127.0.0.1:9/x", timeout=2)

    def test_malformed_url(self):
        """A URL without a usable scheme is reported."""
        with self.assertRaises(RegistryError):
            fetch_json("nonsense")


class RegistryTests(ServerCase):
    """Package metadata access."""

    def setUp(self):
        """Create a client for the local server."""
        self.registry = NpmRegistry(self.url + "/")

    def test_direct_dependencies(self):
        """Dependencies of an exact version are returned."""
        deps = self.registry.direct_dependencies("left-pad", "1.0.0")
        self.assertEqual(deps, {"a": "^1"})

    def test_no_dependencies_field(self):
        """A version without dependencies gives an empty mapping."""
        deps = self.registry.direct_dependencies("@scope/pkg", "2.0.0")
        self.assertEqual(deps, {})

    def test_unknown_package(self):
        """A missing package is NotFoundError with its name."""
        with self.assertRaisesRegex(NotFoundError, "ghost"):
            self.registry.packument("ghost")

    def test_unknown_version(self):
        """A missing version is NotFoundError with the version."""
        with self.assertRaisesRegex(NotFoundError, "3.0.0"):
            self.registry.version_info("left-pad", "3.0.0")

    def test_bad_documents(self):
        """Unexpected document shapes are reported."""
        with self.assertRaises(RegistryError):
            self.registry.packument("broken")
        with self.assertRaises(RegistryError):
            self.registry.versions("no-versions")

    def test_cache(self):
        """A package is downloaded only once."""
        calls = []

        def fetch(url):
            """Record the call and return an empty document."""
            calls.append(url)
            return {"versions": {}}

        registry = NpmRegistry("http://x", fetch)
        registry.packument("p")
        registry.packument("p")
        self.assertEqual(calls, ["http://x/p"])
