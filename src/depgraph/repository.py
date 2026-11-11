"""Resolution of npm version specs into concrete ``name@version`` nodes."""
import re

from .registry import NotFoundError
from .semver import SemverError, max_satisfying, satisfies

ALIAS_PREFIX = "npm:"
TAG = re.compile(r"[A-Za-z][A-Za-z0-9._-]*")
LATEST = "latest"


def split_node(node):
    """Split ``name@version`` (names may start with ``@``)."""
    name, _, version = node.rpartition("@")
    return name, version


def unalias(name, spec):
    """Resolve ``npm:real@range`` aliases to ``(real name, range)``."""
    if not spec.startswith(ALIAS_PREFIX):
        return name, spec
    target = spec[len(ALIAS_PREFIX):]
    real, at, wanted = target.rpartition("@")
    if not at or not real:
        return target, "*"
    return real, wanted


def _best(pool, latest, spec):
    """Pick from ``pool`` like npm: the ``latest`` tag if it fits."""
    if latest in pool and satisfies(latest, spec):
        return latest
    return max_satisfying(pool, spec)


def pick_version(versions, latest, spec):
    """Choose a version of a package for ``spec``.

    Non-deprecated versions are preferred; the ``latest`` dist-tag wins
    if it satisfies the spec, otherwise the highest satisfying version.
    """
    everything = list(versions)
    live = [item for item in everything
            if not versions[item].get("deprecated")]
    for pool in (live, everything):
        best = _best(pool, latest, spec)
        if best:
            return best
    return None


class NpmRepository:
    """Dependencies of ``name@version`` nodes taken from a registry."""

    def __init__(self, registry):
        """Create a repository on top of ``registry``."""
        self.registry = registry
        self.warnings = []
        self._unresolved = set()

    def root(self, name, version):
        """Return the node of an existing package version."""
        self.registry.version_info(name, version)
        return f"{name}@{version}"

    def dependencies(self, node):
        """Return the resolved direct dependencies of ``node``."""
        if node in self._unresolved:
            return []
        name, version = split_node(node)
        specs = self.registry.direct_dependencies(name, version)
        return [self._resolve(dep, specs[dep]) for dep in sorted(specs)]

    def _resolve(self, name, spec):
        """Return the node for dependency ``name`` with version ``spec``."""
        real, wanted = unalias(name, spec)
        try:
            version = self._pick(real, wanted)
        except (NotFoundError, SemverError) as exc:
            return self._unresolved_node(real, wanted, exc)
        return f"{real}@{version}"

    def _pick(self, name, spec):
        """Return the concrete version of ``name`` for ``spec``."""
        packument = self.registry.packument(name)
        tags = packument.get("dist-tags") or {}
        versions = self.registry.versions(name)
        try:
            best = pick_version(versions, tags.get(LATEST), spec)
        except SemverError:
            if not TAG.fullmatch(spec) or spec not in tags:
                raise
            return tags[spec]
        if best is None:
            raise NotFoundError(f"нет версии {name}, подходящей к '{spec}'")
        return best

    def _unresolved_node(self, name, spec, error):
        """Remember a dependency that cannot be resolved."""
        node = f"{name}@{spec}"
        self._unresolved.add(node)
        self.warnings.append(f"не удалось разрешить {node}: {error}")
        return node
