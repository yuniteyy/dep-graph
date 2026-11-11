"""End-to-end tests of ``main`` for parameters, output and exit codes."""
import contextlib
import io
import unittest

from depgraph.app import main
from depgraph.registry import NotFoundError

URL = "https://registry.npmjs.org"
BASE = ["--package", "express", "--repo", URL, "--version", "4.18.2"]
DOCS = {
    "express": {"versions": {
        "4.18.2": {"dependencies": {"qs": "6.11.0", "accepts": "~1.3.8"}},
        "1.0.0": {}}},
}


def fake_fetch(url):
    """Serve ``DOCS`` instead of the network."""
    name = url[len(URL) + 1:]
    if name not in DOCS:
        raise NotFoundError(url)
    return DOCS[name]


def run(argv):
    """Run ``main``; return (code, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = main(argv, fetch=fake_fetch)
        except SystemExit as exc:
            code = exc.code
    return code, out.getvalue(), err.getvalue()


class MainTests(unittest.TestCase):
    """Exit codes and messages."""

    def test_show_config(self):
        """``--show-config`` prints the parameters as key-value pairs."""
        code, out, _ = run([*BASE, "--max-depth", "2", "--show-config"])
        self.assertEqual(code, 0)
        self.assertIn("package   = express", out)
        self.assertIn("max_depth = 2", out)

    def test_config_not_shown_by_default(self):
        """Parameters are printed only on request."""
        _, out, _ = run(BASE)
        self.assertNotIn("max_depth", out)

    def test_direct_dependencies(self):
        """Direct dependencies of the given version are printed."""
        code, out, _ = run(BASE)
        self.assertEqual(code, 0)
        self.assertEqual(out.splitlines(), [
            "Прямые зависимости express@4.18.2:",
            "  accepts: ~1.3.8",
            "  qs: 6.11.0"])

    def test_no_dependencies(self):
        """A package without dependencies is reported as such."""
        _, out, _ = run(["--package", "express", "--repo", URL,
                         "--version", "1.0.0"])
        self.assertIn("(нет зависимостей)", out)

    def test_unknown_package_and_version(self):
        """Unknown packages and versions give exit code 1."""
        code, _, err = run(["--package", "nope", "--repo", URL,
                            "--version", "1.0.0"])
        self.assertEqual(code, 1)
        self.assertIn("не найден", err)
        code, _, err = run(["--package", "express", "--repo", URL,
                            "--version", "9.9.9"])
        self.assertEqual(code, 1)
        self.assertIn("9.9.9", err)

    def test_config_error(self):
        """An invalid value gives exit code 2 and a message on stderr."""
        code, out, err = run(["--package", "express", "--repo", URL,
                              "--version", "latest"])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("ошибка:", err)

    def test_missing_option(self):
        """A missing required option makes argparse exit with code 2."""
        code, _, err = run(["--package", "express"])
        self.assertEqual(code, 2)
        self.assertIn("--repo", err)
