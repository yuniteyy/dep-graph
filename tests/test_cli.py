"""Tests for the command-line parameters and their validation."""
import os
import tempfile
import unittest
from pathlib import Path

from depgraph.cli import (
    ConfigError, MODE_TEST, check_output, check_package, check_version,
    format_config, parse_args, parse_depth)

REPO = Path(__file__).resolve().parent.parent / "examples" / "repos"
URL = "https://registry.npmjs.org"


def args(*extra):
    """Return a valid remote-mode command line plus ``extra`` items."""
    return ["--package", "express", "--repo", URL, "--version", "4.18.2",
            *extra]


class ParseTests(unittest.TestCase):
    """Valid command lines are converted into a configuration."""

    def test_remote_defaults(self):
        """Defaults are used for the optional parameters."""
        config = parse_args(args())
        self.assertEqual(config.package, "express")
        self.assertEqual(config.repo, URL)
        self.assertEqual(config.repo_mode, "remote")
        self.assertEqual(config.output, "graph.png")
        self.assertEqual(config.max_depth, 3)

    def test_all_parameters(self):
        """Every parameter can be set."""
        with tempfile.TemporaryDirectory() as folder:
            out = os.path.join(folder, "g.png")
            config = parse_args(args("--output", out, "--max-depth", "7"))
        self.assertEqual(config.output, out)
        self.assertEqual(config.max_depth, 7)

    def test_test_mode_without_version(self):
        """The version is not needed for the test repository."""
        config = parse_args(
            ["--package", "A", "--repo", str(REPO / "simple.txt"),
             "--repo-mode", "test"])
        self.assertEqual(config.repo_mode, MODE_TEST)
        self.assertIsNone(config.version)

    def test_scoped_package(self):
        """Scoped npm names are accepted."""
        check_package("@types/node", "remote")

    def test_missing_required_option(self):
        """argparse exits when a required option is absent."""
        with self.assertRaises(SystemExit):
            parse_args(["--repo", URL])

    def test_bad_mode(self):
        """An unknown mode is rejected by argparse."""
        with self.assertRaises(SystemExit):
            parse_args(args("--repo-mode", "other"))


class PackageTests(unittest.TestCase):
    """Package name checks."""

    def test_invalid_npm_names(self):
        """Empty, uppercase, spaced and too long names are rejected."""
        for name in ("", "  ", "Express", "a b", "-x" * 200, "@scope/",
                     "a/b"):
            with self.assertRaises(ConfigError, msg=name):
                check_package(name, "remote")

    def test_invalid_test_names(self):
        """Test repository packages are uppercase Latin letters."""
        for name in ("a", "A1", "ab", "Привет"):
            with self.assertRaises(ConfigError, msg=name):
                check_package(name, "test")
        check_package("ABC", "test")


class RepoTests(unittest.TestCase):
    """Repository location checks."""

    def test_bad_urls(self):
        """Non-URLs and non-http schemes are rejected."""
        for repo in ("registry", "ftp://x.org", "file:///tmp", "https://"):
            with self.assertRaises(ConfigError, msg=repo):
                parse_args(["--package", "express", "--repo", repo,
                            "--version", "1.0.0"])

    def test_test_repo_file_problems(self):
        """Missing files and directories are reported."""
        for path in ("/no/such/file.txt", str(REPO)):
            with self.assertRaises(ConfigError, msg=path):
                parse_args(["--package", "A", "--repo", path,
                            "--repo-mode", "test"])


class VersionTests(unittest.TestCase):
    """Version checks."""

    def test_required_in_remote_mode(self):
        """Remote mode needs a version."""
        with self.assertRaises(ConfigError):
            check_version(None, "remote")

    def test_valid_versions(self):
        """Release, pre-release and build versions are valid."""
        for version in ("1.0.0", "0.0.1", "2.0.0-beta.1", "1.2.3+build5"):
            check_version(version, "remote")

    def test_invalid_versions(self):
        """Ranges, partial and malformed versions are rejected."""
        for version in ("1", "1.2", "^1.2.3", "01.2.3", "v1.2.3", "x"):
            with self.assertRaises(ConfigError, msg=version):
                check_version(version, "remote")

    def test_checked_even_in_test_mode(self):
        """A given but malformed version is still an error."""
        with self.assertRaises(ConfigError):
            check_version("abc", "test")


class OutputTests(unittest.TestCase):
    """Image file name checks."""

    def test_extension(self):
        """Only .png is accepted (case-insensitively)."""
        check_output("out.PNG")
        for name in ("out.jpg", "out", "out.png.txt"):
            with self.assertRaises(ConfigError, msg=name):
                check_output(name)

    def test_directory_and_missing_folder(self):
        """A directory or a missing folder are rejected."""
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ConfigError):
                check_output(os.path.join(folder, "missing", "g.png"))
            os.mkdir(os.path.join(folder, "d.png"))
            with self.assertRaises(ConfigError):
                check_output(os.path.join(folder, "d.png"))


class DepthTests(unittest.TestCase):
    """Maximum depth checks."""

    def test_valid(self):
        """Positive integers are accepted."""
        self.assertEqual(parse_depth("1"), 1)
        self.assertEqual(parse_depth("25"), 25)

    def test_invalid(self):
        """Non-numbers, zero and negatives are rejected."""
        for text in ("abc", "", "1.5", "0", "-3"):
            with self.assertRaises(ConfigError, msg=text):
                parse_depth(text)


class FormatTests(unittest.TestCase):
    """Key-value output of the parameters."""

    def test_every_parameter_is_listed(self):
        """Each parameter appears as ``key = value``."""
        text = "\n".join(format_config(parse_args(args())))
        for key in ("package", "repo", "repo_mode", "version", "output",
                    "max_depth"):
            self.assertIn(f"{key} ", text)
        self.assertIn("package   = express", text)
