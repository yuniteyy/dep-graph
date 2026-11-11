"""End-to-end tests of ``main`` for parameters, output and exit codes."""
import contextlib
import io
import unittest
from pathlib import Path

from depgraph.app import main
from fake_registry import URL, fake_fetch

REPOS = Path(__file__).resolve().parent.parent / "examples" / "repos"
BASE = ["--package", "app", "--repo", URL, "--version", "1.0.0"]


def run(argv):
    """Run ``main``; return (code, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = main(argv, fetch=fake_fetch)
        except SystemExit as exc:
            code = exc.code
    return code, out.getvalue(), err.getvalue()


def run_test_repo(name, package, *extra):
    """Run in test mode on the bundled repository file ``name``."""
    return run(["--package", package, "--repo", str(REPOS / name),
                "--repo-mode", "test", *extra])


class RemoteTests(unittest.TestCase):
    """Remote mode on the fake registry."""

    def test_graph_report(self):
        """The report lists nodes in BFS order with their depth."""
        code, out, _ = run(BASE)
        self.assertEqual(code, 0)
        self.assertEqual(out.splitlines(), [
            "Граф зависимостей app@1.0.0 (максимальная глубина 3)",
            "Узлов: 4, рёбер: 3",
            "  app@1.0.0 [0] -> lib@1.5.0, util@2.1.5",
            "  lib@1.5.0 [1] -> util@2.3.0",
            "  util@2.1.5 [1] -> (нет)",
            "  util@2.3.0 [2] -> (нет)"])

    def test_max_depth(self):
        """Depth 1 shows direct dependencies only."""
        _, out, _ = run([*BASE, "--max-depth", "1"])
        self.assertIn("lib@1.5.0 [1] -> (глубина исчерпана)", out)
        self.assertNotIn("util@2.3.0", out)

    def test_warnings_go_to_stderr(self):
        """Unresolvable dependencies produce warnings, not failures."""
        code, _, err = run(["--package", "ghosts", "--repo", URL,
                            "--version", "1.0.0"])
        self.assertEqual(code, 0)
        self.assertEqual(err.count("предупреждение:"), 3)

    def test_unknown_package_and_version(self):
        """Unknown packages and versions give exit code 1."""
        code, _, err = run(["--package", "nope", "--repo", URL,
                            "--version", "1.0.0"])
        self.assertEqual(code, 1)
        self.assertIn("не найден", err)
        code, _, err = run(["--package", "app", "--repo", URL,
                            "--version", "9.9.9"])
        self.assertEqual(code, 1)
        self.assertIn("9.9.9", err)

    def test_show_config(self):
        """``--show-config`` prints the parameters first."""
        _, out, _ = run([*BASE, "--show-config"])
        self.assertTrue(out.startswith("package   = app"))


class TestModeTests(unittest.TestCase):
    """Test repository mode."""

    def test_tree(self):
        """The simple repository is traversed breadth-first."""
        code, out, _ = run_test_repo("simple.txt", "A")
        self.assertEqual(code, 0)
        self.assertEqual(out.splitlines(), [
            "Граф зависимостей A (максимальная глубина 3)",
            "Узлов: 5, рёбер: 5",
            "  A [0] -> B, C",
            "  B [1] -> D",
            "  C [1] -> D, E",
            "  D [2] -> (нет)",
            "  E [2] -> (нет)"])

    def test_other_root(self):
        """Any package of the file can be the root."""
        _, out, _ = run_test_repo("simple.txt", "C")
        self.assertIn("Узлов: 3", out)

    def test_depth_limits(self):
        """Different depths on the chain give different graphs."""
        for depth, nodes in (("1", 2), ("3", 4), ("10", 7)):
            _, out, _ = run_test_repo("chain.txt", "A", "--max-depth", depth)
            self.assertIn(f"Узлов: {nodes},", out, depth)

    def test_cycle_is_reported(self):
        """A cycle terminates and is listed."""
        code, out, _ = run_test_repo("cycle.txt", "A", "--max-depth", "10")
        self.assertEqual(code, 0)
        self.assertIn("Циклические зависимости (1):", out)
        self.assertIn("A -> B -> C -> A", out)

    def test_self_loop_and_two_cycles(self):
        """Self-dependency and several cycles are handled."""
        _, out, _ = run_test_repo("self_loop.txt", "A")
        self.assertIn("  A -> A", out)
        _, out, _ = run_test_repo("two_cycles.txt", "A")
        self.assertIn("Циклические зависимости (2):", out)

    def test_undefined_dependencies(self):
        """Packages that are only mentioned are leaves."""
        _, out, _ = run_test_repo("undefined.txt", "A")
        self.assertIn("  X [1] -> (нет)", out)

    def test_unknown_root(self):
        """A package absent from the file is an error."""
        code, _, err = run_test_repo("simple.txt", "Q")
        self.assertEqual(code, 1)
        self.assertIn("не найден в тестовом репозитории", err)

    def test_broken_files(self):
        """Malformed repository files give exit code 1."""
        for name in ("lowercase", "no_colon", "duplicate",
                     "bad_dependency"):
            code, _, err = run_test_repo(f"invalid/{name}.txt", "A")
            self.assertEqual(code, 1, name)
            self.assertIn("ошибка:", err)


class ConfigErrorTests(unittest.TestCase):
    """Parameter errors keep their exit code."""

    def test_config_error(self):
        """An invalid value gives exit code 2 and a message on stderr."""
        code, out, err = run(["--package", "app", "--repo", URL,
                              "--version", "latest"])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("ошибка:", err)

    def test_missing_option(self):
        """A missing required option makes argparse exit with code 2."""
        code, _, err = run(["--package", "app"])
        self.assertEqual(code, 2)
        self.assertIn("--repo", err)


class ReverseTests(unittest.TestCase):
    """Reverse dependencies in the test repository mode."""

    def test_transitive_dependents(self):
        """Dependents are found level by level with the same BFS."""
        code, out, _ = run_test_repo("simple.txt", "D", "--reverse")
        self.assertEqual(code, 0)
        self.assertEqual(out.splitlines(), [
            "Обратные зависимости D (максимальная глубина 3)",
            "Узлов: 4, рёбер: 4",
            "  D [0] <- B, C",
            "  B [1] <- A",
            "  C [1] <- A",
            "  A [2] <- (нет)"])

    def test_depth_one_gives_direct_dependents(self):
        """Depth 1 lists only the packages depending on the given one."""
        _, out, _ = run_test_repo("wide.txt", "K", "--reverse",
                                  "--max-depth", "1")
        self.assertIn("  K [0] <- G, H", out)
        self.assertNotIn("A [", out)

    def test_package_without_dependents(self):
        """The root of the graph has no dependents."""
        _, out, _ = run_test_repo("simple.txt", "A", "--reverse")
        self.assertIn("  A [0] <- (нет)", out)
        self.assertIn("Узлов: 1,", out)

    def test_leaf_with_many_dependents(self):
        """Every transitive dependent of a leaf is listed once."""
        _, out, _ = run_test_repo("wide.txt", "M", "--reverse",
                                  "--max-depth", "20")
        self.assertIn("Узлов: 11,", out)
        self.assertIn("  M [0] <- L", out)

    def test_cycles(self):
        """Cycles of the inverted graph terminate and are reported."""
        _, out, _ = run_test_repo("cycle.txt", "A", "--reverse",
                                  "--max-depth", "10")
        self.assertIn("Циклические зависимости (1):", out)
        self.assertIn("A <- C <- B <- A", out)

    def test_self_loop(self):
        """A self-dependent package is its own dependent."""
        _, out, _ = run_test_repo("self_loop.txt", "B", "--reverse")
        self.assertIn("  B [0] <- A", out)
        self.assertIn("  A [1] <- A", out)

    def test_unknown_package(self):
        """A package missing from the file is an error."""
        code, _, err = run_test_repo("simple.txt", "Q", "--reverse")
        self.assertEqual(code, 1)
        self.assertIn("не найден", err)

    def test_not_available_for_remote_registry(self):
        """Reverse mode is rejected for the real registry."""
        code, _, err = run([*BASE, "--reverse"])
        self.assertEqual(code, 2)
        self.assertIn("--reverse", err)
