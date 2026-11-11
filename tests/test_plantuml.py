"""Tests for the PlantUML text, its encoding and the renderers."""
import base64
import os
import shutil
import tempfile
import threading
import unittest
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from depgraph.graph import build_graph
from depgraph.plantuml import (
    PNG_SIGNATURE, PUML_ALPHABET, RenderError, STD_ALPHABET, encode,
    puml_path, render_png, render_with_jar, render_with_server,
    to_plantuml, write_file)
from depgraph.testrepo import FileRepository

REPOS = Path(__file__).resolve().parent.parent / "examples" / "repos"
JAR = os.environ.get("PLANTUML_JAR")
SAMPLE = "@startuml\nBob -> Alice : hello\n@enduml"
REPEAT = 20


def make_graph(name, root, depth, reverse=False):
    """Build a graph from a bundled test repository."""
    repo = FileRepository.load(REPOS / name)
    if reverse:
        repo = repo.reversed()
    return build_graph(repo, root, depth)


def decode(text):
    """Invert :func:`encode` (for the round-trip check)."""
    table = str.maketrans(PUML_ALPHABET, STD_ALPHABET)
    data = base64.b64decode(text.translate(table))
    return zlib.decompressobj(-zlib.MAX_WBITS).decompress(data)


class TextTests(unittest.TestCase):
    """The generated PlantUML source."""

    def test_simple_graph(self):
        """Nodes and edges are declared; the root is highlighted."""
        graph = make_graph("simple.txt", "A", 5)
        lines = to_plantuml(graph, "T").splitlines()
        self.assertEqual(lines[0:3], [
            "@startuml", "title T", "skinparam shadowing false"])
        self.assertIn('rectangle "A" as n0 #LightSkyBlue', lines)
        self.assertIn('rectangle "D" as n3', lines)
        self.assertIn("n0 --> n1", lines)
        self.assertIn("n2 --> n3", lines)
        self.assertEqual(lines[-1], "@enduml")
        self.assertEqual(lines.count("n1 --> n3"), 1)

    def test_cycle_edges_are_red(self):
        """Only the edges that belong to a cycle are red."""
        graph = make_graph("cycle.txt", "A", 10)
        text = to_plantuml(graph, "T")
        self.assertIn("n2 -[#red]-> n0", text)
        self.assertIn("n0 -[#red]-> n1", text)
        self.assertIn("n2 --> n3", text)

    def test_self_loop(self):
        """A self-dependency is a red loop."""
        text = to_plantuml(make_graph("self_loop.txt", "A", 3), "T")
        self.assertIn("n0 -[#red]-> n0", text)

    def test_frontier_is_dashed(self):
        """Nodes that were not expanded are drawn dashed."""
        text = to_plantuml(make_graph("chain.txt", "A", 2), "T")
        self.assertIn('rectangle "C" as n2 #WhiteSmoke;line.dashed', text)

    def test_reverse_keeps_dependency_direction(self):
        """Reverse graphs are drawn from dependent to dependency."""
        graph = make_graph("simple.txt", "D", 5, reverse=True)
        text = to_plantuml(graph, "T", reverse=True)
        self.assertIn('rectangle "D" as n0 #LightSkyBlue', text)
        self.assertIn("n1 --> n0", text)

    def test_puml_path(self):
        """The source file sits next to the image."""
        self.assertEqual(puml_path("out/g.png"), "out/g.puml")
        self.assertEqual(puml_path("g.PNG"), "g.puml")


class EncodeTests(unittest.TestCase):
    """The URL encoding of the diagram."""

    def test_known_vector(self):
        """The result matches the one from the PlantUML documentation."""
        self.assertEqual(encode("Bob -> Alice : hello"),
                         "SyfFKj2rKt3CoKnELR1Io4ZDoSa70000")

    def test_round_trip(self):
        """Decoding gives back the original text, also for Cyrillic."""
        text = "@startuml\ntitle Граф зависимостей\nA --> B\n@enduml\n"
        self.assertEqual(decode(encode(text)).decode("utf-8"), text)

    def test_alphabet(self):
        """Only URL-safe characters are produced."""
        allowed = set(PUML_ALPHABET)
        self.assertTrue(set(encode(SAMPLE * REPEAT)) <= allowed)


class ImageHandler(BaseHTTPRequestHandler):
    """A fake PlantUML server that records the requested path."""

    paths = []

    def do_GET(self):  # noqa: N802
        """Answer with a PNG, an HTML page or an error."""
        self.paths.append(self.path)
        if self.path.startswith("/ok/png/"):
            self.reply(200, PNG_SIGNATURE + b"data")
        elif self.path.startswith("/html/png/"):
            self.reply(200, b"<html></html>")
        else:
            self.reply(500, b"error")

    def reply(self, code, body):
        """Send a complete response."""
        self.send_response(code)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        """Keep the test output clean."""


class ServerTests(unittest.TestCase):
    """Rendering through a (fake) PlantUML server."""

    @classmethod
    def setUpClass(cls):
        """Start the fake server."""
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), ImageHandler)
        cls.url = f"http://127.0.0.1:{cls.server.server_address[1]}"
        threading.Thread(target=cls.server.serve_forever,
                         daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        """Stop the fake server."""
        cls.server.shutdown()
        cls.server.server_close()

    def test_png_is_downloaded(self):
        """The server receives the encoded diagram and returns a PNG."""
        data = render_with_server(SAMPLE, self.url + "/ok/")
        self.assertTrue(data.startswith(PNG_SIGNATURE))
        self.assertIn(encode(SAMPLE), ImageHandler.paths[-1])

    def test_not_an_image(self):
        """A non-PNG answer is rejected."""
        with self.assertRaisesRegex(RenderError, "PNG"):
            render_with_server(SAMPLE, self.url + "/html")

    def test_server_error(self):
        """An HTTP error is reported."""
        with self.assertRaisesRegex(RenderError, "недоступен"):
            render_with_server(SAMPLE, self.url + "/other")

    def test_too_large_for_url(self):
        """A huge diagram is refused with a hint about the jar."""
        big = "\n".join(f"n{i} --> n{i + 1}" for i in range(3000))
        with self.assertRaisesRegex(RenderError, "plantuml-jar"):
            render_with_server(big, self.url + "/ok")

    def test_render_png_chooses_server(self):
        """Without a jar the server is used."""
        data = render_png(SAMPLE, None, self.url + "/ok")
        self.assertTrue(data.startswith(PNG_SIGNATURE))


class JarTests(unittest.TestCase):
    """Rendering through a local jar (needs Java and PLANTUML_JAR)."""

    def test_missing_java_or_jar(self):
        """A broken command line is reported, not raised."""
        with self.assertRaises(RenderError):
            render_with_jar(SAMPLE, "/no/such/plantuml.jar")

    @unittest.skipUnless(JAR and shutil.which("java"),
                         "set PLANTUML_JAR and install Java")
    def test_real_rendering(self):
        """A real PNG is produced, including Cyrillic labels."""
        text = "@startuml\ntitle Граф\nA --> B\n@enduml\n"
        data = render_with_jar(text, JAR)
        self.assertTrue(data.startswith(PNG_SIGNATURE))
        self.assertGreater(len(data), len(PNG_SIGNATURE))


class WriteTests(unittest.TestCase):
    """Writing text and binary files."""

    def test_text_and_bytes(self):
        """Both kinds of data are stored; errors are reported."""
        with tempfile.TemporaryDirectory() as folder:
            write_file(os.path.join(folder, "a.puml"), "Граф")
            write_file(os.path.join(folder, "a.png"), b"\x89PNG")
            self.assertEqual(
                Path(folder, "a.puml").read_text(encoding="utf-8"), "Граф")
            with self.assertRaises(RenderError):
                write_file(os.path.join(folder, "no", "a.png"), b"x")
