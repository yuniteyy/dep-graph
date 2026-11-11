"""A tiny in-memory npm registry used by several test modules."""
from depgraph.registry import NotFoundError

URL = "https://registry.npmjs.org"


def package(latest, versions):
    """Build a packument; ``versions`` maps version -> dependencies."""
    return {
        "dist-tags": {"latest": latest},
        "versions": {ver: {"dependencies": deps}
                     for ver, deps in versions.items()},
    }


DOCS = {
    "app": package("1.0.0", {"1.0.0": {"lib": "^1.0.0", "util": "~2.1.0"}}),
    "lib": package("1.5.0", {
        "1.0.0": {}, "1.4.0": {"util": "*"}, "1.5.0": {"util": "^2.0.0"},
        "1.9.0": {}, "2.0.0": {}}),
    "util": package("2.3.0", {
        "2.0.0": {}, "2.1.0": {}, "2.1.5": {}, "2.2.0": {}, "2.3.0": {}}),
    "loop-a": package("1.0.0", {"1.0.0": {"loop-b": "1.0.0"}}),
    "loop-b": package("1.0.0", {"1.0.0": {"loop-a": "1.0.0"}}),
    "ghosts": package("1.0.0", {"1.0.0": {
        "missing-pkg": "^1.0.0", "lib": "^9.0.0", "git-dep": "user/repo",
        "tagged": "next", "aliased": "npm:util@^2.0.0"}}),
    "tagged": {"dist-tags": {"latest": "1.0.0", "next": "1.1.0"},
               "versions": {"1.0.0": {}, "1.1.0": {}}},
    "@scope/pkg": package("1.0.0", {"1.0.0": {"util": "2.1.0"}}),
}


def fake_fetch(url):
    """Serve ``DOCS`` as if it were the registry."""
    name = url[len(URL) + 1:].replace("%2F", "/")
    if name not in DOCS:
        raise NotFoundError(url)
    return DOCS[name]
