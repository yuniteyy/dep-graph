"""Test repository: a graph described in a text file.

Format: one package per line, ``A: B C`` (dependencies separated by
spaces or commas); ``#`` starts a comment. Package names are upper-case
Latin letters. A package that is only mentioned as a dependency has no
dependencies of its own.
"""
import re

from .errors import ToolError

NAME = re.compile(r"[A-Z]+")
SEPARATORS = re.compile(r"[\s,]+")
COMMENT = "#"
DEFINITION_SEPARATOR = ":"


class TestRepoError(ToolError):
    """The test repository file is malformed."""

    __test__ = False


def _check_name(name, number):
    """Raise unless ``name`` is made of upper-case Latin letters."""
    if not NAME.fullmatch(name):
        raise TestRepoError(
            f"строка {number}: имя пакета '{name}' должно состоять из "
            "заглавных латинских букв")


def _parse_line(line, number):
    """Return ``(package, dependencies)`` for one non-empty line."""
    head, colon, tail = line.partition(DEFINITION_SEPARATOR)
    if not colon:
        raise TestRepoError(
            f"строка {number}: ожидается формат 'A: B C' (нет ':')")
    name = head.strip()
    _check_name(name, number)
    deps = []
    for dep in SEPARATORS.split(tail.strip()):
        if not dep:
            continue
        _check_name(dep, number)
        if dep not in deps:
            deps.append(dep)
    return name, deps


class FileRepository:
    """Dependencies of packages read from a test repository file."""

    def __init__(self, graph):
        """Create a repository from a ``package -> dependencies`` dict."""
        self.graph = graph
        self.warnings = []

    @classmethod
    def load(cls, path):
        """Read and validate the file ``path``."""
        try:
            with open(path, encoding="utf-8-sig") as handle:
                lines = handle.read().splitlines()
        except (OSError, UnicodeDecodeError) as exc:
            raise TestRepoError(
                f"не удалось прочитать файл {path}: {exc}") from None
        graph = {}
        for number, raw in enumerate(lines, start=1):
            line = raw.split(COMMENT, 1)[0].strip()
            if not line:
                continue
            name, deps = _parse_line(line, number)
            if name in graph:
                raise TestRepoError(
                    f"строка {number}: пакет '{name}' описан повторно")
            graph[name] = deps
        return cls(graph)

    def packages(self):
        """Return every package mentioned in the file."""
        names = set(self.graph)
        for deps in self.graph.values():
            names.update(deps)
        return sorted(names)

    def has(self, name):
        """Tell whether ``name`` is mentioned in the file."""
        return name in self.packages()

    def dependencies(self, node):
        """Return the direct dependencies of ``node``."""
        return list(self.graph.get(node, ()))

    def reversed(self):
        """Return a repository with all dependency edges inverted."""
        inverted = {name: [] for name in self.packages()}
        for name in sorted(self.graph):
            for dep in self.graph[name]:
                inverted[dep].append(name)
        return FileRepository(inverted)
