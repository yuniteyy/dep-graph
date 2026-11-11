"""Application entry: parameters in, results out, exit codes."""
import sys

from .cli import MODE_TEST, ConfigError, format_config, parse_args
from .errors import ToolError
from .graph import build_graph
from .registry import NpmRegistry, fetch_json
from .report import format_graph
from .repository import NpmRepository
from .testrepo import FileRepository, TestRepoError

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_CONFIG = 2


def open_source(config, fetch):
    """Return ``(repository, root node)`` for the configured source."""
    if config.repo_mode == MODE_TEST:
        repo = FileRepository.load(config.repo)
        if not repo.has(config.package):
            raise TestRepoError(
                f"пакет '{config.package}' не найден в тестовом репозитории")
        return repo, config.package
    repo = NpmRepository(NpmRegistry(config.repo, fetch))
    return repo, repo.root(config.package, config.version)


def analyse(config, fetch):
    """Build the dependency graph and print its report."""
    repo, root = open_source(config, fetch)
    graph = build_graph(repo, root, config.max_depth)
    title = f"Граф зависимостей {root}"
    print("\n".join(format_graph(graph, config.max_depth, title)))
    for warning in repo.warnings:
        print(f"предупреждение: {warning}", file=sys.stderr)
    return graph


def main(argv=None, fetch=fetch_json):
    """Run the tool and return the process exit code.

    ``fetch`` downloads JSON documents; tests replace it by a fake.
    """
    try:
        config = parse_args(argv)
    except ConfigError as exc:
        print(f"ошибка: {exc}", file=sys.stderr)
        return EXIT_CONFIG
    if config.show_config:
        print("\n".join(format_config(config)))
    try:
        analyse(config, fetch)
    except ToolError as exc:
        print(f"ошибка: {exc}", file=sys.stderr)
        return EXIT_ERROR
    return EXIT_OK
