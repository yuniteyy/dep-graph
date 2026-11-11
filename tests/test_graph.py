"""Tests for the BFS traversal, depth limit and cycle detection."""
import unittest

from depgraph.graph import build_graph, find_cycles


class DictRepo:
    """Repository backed by a dictionary."""

    def __init__(self, data):
        """Store the ``node -> dependencies`` mapping."""
        self.data = data
        self.calls = []

    def dependencies(self, node):
        """Return dependencies and remember the call."""
        self.calls.append(node)
        return self.data.get(node, [])


TREE = {"A": ["B", "C"], "B": ["D"], "C": ["D", "E"]}


class BuildTests(unittest.TestCase):
    """Breadth-first construction of the graph."""

    def test_bfs_order_and_depths(self):
        """Nodes are discovered level by level."""
        graph = build_graph(DictRepo(TREE), "A", 10)
        self.assertEqual(graph.nodes(), ["A", "B", "C", "D", "E"])
        self.assertEqual(graph.depth, {"A": 0, "B": 1, "C": 1, "D": 2,
                                       "E": 2})

    def test_shared_dependency_is_expanded_once(self):
        """A diamond does not duplicate nodes or calls."""
        repo = DictRepo(TREE)
        graph = build_graph(repo, "A", 10)
        self.assertEqual(sorted(repo.calls), ["A", "B", "C", "D", "E"])
        self.assertEqual(len(graph.edge_list()), 5)

    def test_depth_limit(self):
        """Nodes beyond the limit are not discovered."""
        graph = build_graph(DictRepo(TREE), "A", 1)
        self.assertEqual(graph.nodes(), ["A", "B", "C"])
        self.assertEqual(graph.frontier, ["B", "C"])
        self.assertNotIn("B", graph.edges.get("B", []))

    def test_depth_one_is_direct_dependencies(self):
        """Depth 1 shows exactly the direct dependencies."""
        graph = build_graph(DictRepo(TREE), "A", 1)
        self.assertEqual(graph.edges, {"A": ["B", "C"]})

    def test_leaf_root(self):
        """A root without dependencies gives a one-node graph."""
        graph = build_graph(DictRepo({}), "Z", 5)
        self.assertEqual(graph.nodes(), ["Z"])
        self.assertEqual(graph.edge_list(), [])

    def test_very_deep_chain_needs_no_recursion(self):
        """A chain longer than the recursion limit is handled."""
        size = 5000
        data = {str(i): [str(i + 1)] for i in range(size)}
        graph = build_graph(DictRepo(data), "0", size + 1)
        self.assertEqual(len(graph.nodes()), size + 1)
        self.assertEqual(find_cycles(graph), [])


class CycleTests(unittest.TestCase):
    """Cyclic dependencies terminate and are reported."""

    def test_simple_cycle(self):
        """A -> B -> C -> A is found once."""
        data = {"A": ["B"], "B": ["C"], "C": ["A", "D"]}
        graph = build_graph(DictRepo(data), "A", 10)
        self.assertEqual(graph.nodes(), ["A", "B", "C", "D"])
        self.assertEqual(find_cycles(graph), [["A", "B", "C", "A"]])

    def test_self_loop(self):
        """A package that depends on itself is a cycle of length one."""
        graph = build_graph(DictRepo({"A": ["A", "B"]}), "A", 10)
        self.assertEqual(find_cycles(graph), [["A", "A"]])
        self.assertEqual(graph.nodes(), ["A", "B"])

    def test_two_cycles(self):
        """Independent cycles are all reported."""
        data = {"A": ["B", "C"], "B": ["A"], "C": ["D"], "D": ["C"]}
        graph = build_graph(DictRepo(data), "A", 10)
        self.assertEqual(find_cycles(graph),
                         [["A", "B", "A"], ["C", "D", "C"]])

    def test_acyclic_graph(self):
        """A diamond is not a cycle."""
        graph = build_graph(DictRepo(TREE), "A", 10)
        self.assertEqual(find_cycles(graph), [])

    def test_cycle_cut_by_depth(self):
        """A cycle that is cut by the depth limit is not reported."""
        data = {"A": ["B"], "B": ["C"], "C": ["A"]}
        graph = build_graph(DictRepo(data), "A", 2)
        self.assertEqual(find_cycles(graph), [])
