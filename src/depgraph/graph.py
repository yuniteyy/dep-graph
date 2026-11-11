"""Dependency graph, breadth-first traversal and cycle detection."""
from collections import deque
from dataclasses import dataclass, field

GRAY = "gray"
BLACK = "black"


@dataclass
class Graph:
    """Result of a traversal started at ``root``.

    ``depth`` maps every discovered node to its BFS depth (the insertion
    order is the BFS order); ``edges`` maps every expanded node to its
    neighbours; ``frontier`` lists nodes that were not expanded because
    the maximum depth was reached.
    """

    root: str
    depth: dict = field(default_factory=dict)
    edges: dict = field(default_factory=dict)
    frontier: list = field(default_factory=list)

    def nodes(self):
        """Return all nodes in BFS order."""
        return list(self.depth)

    def edge_list(self):
        """Return all ``(source, target)`` pairs in BFS order."""
        return [(node, dep) for node, deps in self.edges.items()
                for dep in deps]


def build_graph(repo, root, max_depth):
    """Traverse ``repo`` from ``root`` breadth-first, without recursion.

    ``repo.dependencies(node)`` returns the neighbours of a node. Nodes
    deeper than ``max_depth`` are not expanded. Every node is expanded at
    most once, so cyclic dependencies cannot cause an endless loop.
    """
    graph = Graph(root)
    graph.depth[root] = 0
    queue = deque([root])
    while queue:
        node = queue.popleft()
        depth = graph.depth[node]
        if depth >= max_depth:
            graph.frontier.append(node)
            continue
        deps = list(repo.dependencies(node))
        graph.edges[node] = deps
        for dep in deps:
            if dep not in graph.depth:
                graph.depth[dep] = depth + 1
                queue.append(dep)
    return graph


def _walk_from(graph, start, color, cycles):
    """Iterative depth-first walk from ``start``; collect back edges."""
    color[start] = GRAY
    path = [start]
    stack = [iter(graph.edges.get(start, ()))]
    while stack:
        target = next(stack[-1], None)
        if target is None:
            color[path.pop()] = BLACK
            stack.pop()
        elif target not in color:
            color[target] = GRAY
            path.append(target)
            stack.append(iter(graph.edges.get(target, ())))
        elif color[target] == GRAY:
            cycles.append(path[path.index(target):] + [target])


def find_cycles(graph):
    """Return the cycles of ``graph`` as lists ``[a, b, ..., a]``.

    Every back edge of a depth-first walk yields one cycle. The walk is
    iterative, so very deep graphs do not exhaust the recursion limit.
    """
    color, cycles = {}, []
    for node in graph.nodes():
        if node not in color:
            _walk_from(graph, node, color, cycles)
    return cycles
