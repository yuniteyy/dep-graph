"""End-to-end tests of ``main`` for parameters and exit codes."""
import contextlib
import io
import unittest

from depgraph.app import main

URL = "https://registry.npmjs.org"


def run(argv):
    """Run ``main``; return (code, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = main(argv)
        except SystemExit as exc:
            code = exc.code
    return code, out.getvalue(), err.getvalue()


class MainTests(unittest.TestCase):
    """Exit codes and messages."""

    def test_prints_parameters(self):
        """Valid parameters are printed as key-value pairs."""
        code, out, _ = run(["--package", "express", "--repo", URL,
                            "--version", "4.18.2", "--max-depth", "2"])
        self.assertEqual(code, 0)
        self.assertIn("package   = express", out)
        self.assertIn("max_depth = 2", out)

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
