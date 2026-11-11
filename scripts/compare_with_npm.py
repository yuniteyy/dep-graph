"""Compare the graph built by depgraph with the tree reported by npm.

Usage: ``compare_with_npm.py NAME@VERSION [REGISTRY_URL]``. npm is used
here only as a reference for the comparison, never by depgraph itself.
"""
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_URL = "https://registry.npmjs.org"
UNLIMITED_DEPTH = 1000
NPM_TIMEOUT = 300
USAGE = "usage: compare_with_npm.py NAME@VERSION [REGISTRY_URL]"


def run_npm(args, folder):
    """Run ``npm`` with ``args`` inside ``folder``; return its stdout."""
    done = subprocess.run(
        ["npm", *args], cwd=folder, capture_output=True, text=True,
        timeout=NPM_TIMEOUT, check=False)
    return done.stdout


def collect_pairs(tree):
    """Return ``{name@version}`` for every node of an ``npm ls`` tree."""
    pairs = set()
    stack = list(tree.get("dependencies", {}).items())
    while stack:
        name, info = stack.pop()
        pairs.add(f"{name}@{info.get('version')}")
        stack.extend(info.get("dependencies", {}).items())
    return pairs


def npm_nodes(spec):
    """Return the nodes that ``npm ls --all`` reports for ``spec``."""
    with tempfile.TemporaryDirectory() as folder:
        run_npm(["init", "-y"], folder)
        run_npm(["install", "--package-lock-only", "--ignore-scripts",
                 "--no-audit", "--no-fund", spec], folder)
        listing = run_npm(["ls", "--all", "--json", "--package-lock-only"],
                          folder)
    return collect_pairs(json.loads(listing))


def our_nodes(spec, url):
    """Return the nodes that depgraph finds for ``spec`` (root excluded)."""
    sys.path.insert(0, os.path.join(ROOT, "src"))
    from depgraph.graph import build_graph
    from depgraph.registry import NpmRegistry
    from depgraph.repository import NpmRepository
    name, _, version = spec.rpartition("@")
    repo = NpmRepository(NpmRegistry(url))
    graph = build_graph(repo, repo.root(name, version), UNLIMITED_DEPTH)
    return set(graph.nodes()) - {graph.root}


def show(title, items):
    """Print a titled, sorted list of nodes."""
    print(f"{title} ({len(items)}):")
    for item in sorted(items):
        print(f"  {item}")


def compare(spec, url):
    """Print the differences between depgraph and npm for ``spec``."""
    ours = our_nodes(spec, url)
    theirs = npm_nodes(spec) - {spec}
    print(f"=== {spec}")
    print(f"depgraph: {len(ours)} узлов, npm ls: {len(theirs)} узлов, "
          f"общих: {len(ours & theirs)}")
    show("только в depgraph", ours - theirs)
    show("только в npm", theirs - ours)


def main(argv):
    """Entry point; returns the process exit code."""
    if not argv:
        print(USAGE, file=sys.stderr)
        return 2
    compare(argv[0], argv[1] if argv[1:] else DEFAULT_URL)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
