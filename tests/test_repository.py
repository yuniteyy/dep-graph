"""Tests for resolving npm version specs and building npm graphs."""
import unittest

from depgraph.graph import build_graph, find_cycles
from depgraph.registry import NpmRegistry
from depgraph.repository import (
    NpmRepository, pick_version, split_node, unalias)
from fake_registry import URL, fake_fetch


def make_repo():
    """Create a repository on top of the fake registry."""
    return NpmRepository(NpmRegistry(URL, fake_fetch))


class HelperTests(unittest.TestCase):
    """Small pure helpers."""

    def test_split_node(self):
        """Scoped names keep their leading ``@``."""
        self.assertEqual(split_node("lib@1.0.0"), ("lib", "1.0.0"))
        self.assertEqual(split_node("@s/p@2.0.0"), ("@s/p", "2.0.0"))

    def test_unalias(self):
        """``npm:`` aliases point to the real package."""
        self.assertEqual(unalias("a", "^1"), ("a", "^1"))
        self.assertEqual(unalias("a", "npm:b@^2"), ("b", "^2"))
        self.assertEqual(unalias("a", "npm:@s/b@1.0.0"), ("@s/b", "1.0.0"))
        self.assertEqual(unalias("a", "npm:b"), ("b", "*"))

    def test_pick_prefers_latest_tag(self):
        """The ``latest`` tag wins if it satisfies the range."""
        versions = {"1.0.0": {}, "1.5.0": {}, "1.9.0": {}}
        self.assertEqual(pick_version(versions, "1.5.0", "^1.0.0"), "1.5.0")
        self.assertEqual(pick_version(versions, "1.5.0", "^1.6.0"), "1.9.0")

    def test_pick_avoids_deprecated(self):
        """Deprecated versions are used only as a last resort."""
        versions = {"1.0.0": {}, "1.1.0": {"deprecated": "old"}}
        self.assertEqual(pick_version(versions, None, "^1.0.0"), "1.0.0")
        self.assertEqual(pick_version(versions, None, "^1.1.0"), "1.1.0")
        self.assertIsNone(pick_version(versions, None, "^2.0.0"))


class ResolutionTests(unittest.TestCase):
    """Resolution of ranges to concrete nodes."""

    def test_root_and_dependencies(self):
        """Ranges become concrete versions."""
        repo = make_repo()
        root = repo.root("app", "1.0.0")
        self.assertEqual(repo.dependencies(root),
                         ["lib@1.5.0", "util@2.1.5"])

    def test_latest_is_used_when_it_fits(self):
        """A range that includes ``latest`` resolves to it."""
        repo = make_repo()
        self.assertEqual(repo.dependencies("lib@1.4.0"), ["util@2.3.0"])

    def test_scoped_package(self):
        """Scoped packages are fetched and resolved."""
        repo = make_repo()
        node = repo.root("@scope/pkg", "1.0.0")
        self.assertEqual(repo.dependencies(node), ["util@2.1.0"])

    def test_unresolvable_dependencies(self):
        """Missing, unsatisfiable and unsupported specs become leaves."""
        repo = make_repo()
        deps = repo.dependencies(repo.root("ghosts", "1.0.0"))
        self.assertEqual(deps, [
            "util@2.3.0",
            "git-dep@user/repo", "lib@^9.0.0", "missing-pkg@^1.0.0",
            "tagged@1.1.0"])
        self.assertEqual(len(repo.warnings), 3)
        self.assertEqual(repo.dependencies("lib@^9.0.0"), [])

    def test_graph_with_depth(self):
        """The whole transitive graph is built by BFS."""
        repo = make_repo()
        graph = build_graph(repo, repo.root("app", "1.0.0"), 5)
        self.assertEqual(graph.nodes(),
                         ["app@1.0.0", "lib@1.5.0", "util@2.1.5",
                          "util@2.3.0"])
        self.assertEqual(graph.depth["util@2.3.0"], 2)

    def test_npm_cycle(self):
        """Cycles between real packages terminate and are found."""
        repo = make_repo()
        graph = build_graph(repo, repo.root("loop-a", "1.0.0"), 9)
        self.assertEqual(find_cycles(graph),
                         [["loop-a@1.0.0", "loop-b@1.0.0", "loop-a@1.0.0"]])
