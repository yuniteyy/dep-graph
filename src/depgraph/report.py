"""Text report of a dependency graph."""
from .graph import find_cycles

ARROW = " -> "
REVERSE_ARROW = " <- "
NONE_TEXT = "(нет)"
FRONTIER_TEXT = "(глубина исчерпана)"


def format_graph(graph, max_depth, title, reverse=False):
    """Return the lines describing ``graph`` in BFS order.

    With ``reverse`` the edges point from a package to its dependents.
    """
    arrow = REVERSE_ARROW if reverse else ARROW
    nodes = graph.nodes()
    lines = [f"{title} (максимальная глубина {max_depth})",
             f"Узлов: {len(nodes)}, рёбер: {len(graph.edge_list())}"]
    frontier = set(graph.frontier)
    for node in nodes:
        if node in frontier:
            targets = FRONTIER_TEXT
        else:
            targets = ", ".join(graph.edges.get(node, [])) or NONE_TEXT
        lines.append(f"  {node} [{graph.depth[node]}]{arrow}{targets}")
    return lines + format_cycles(graph, arrow)


def format_cycles(graph, arrow=ARROW):
    """Return lines describing the cyclic dependencies, if any."""
    cycles = find_cycles(graph)
    if not cycles:
        return []
    lines = [f"Циклические зависимости ({len(cycles)}):"]
    lines.extend(f"  {arrow.join(cycle)}" for cycle in cycles)
    return lines
