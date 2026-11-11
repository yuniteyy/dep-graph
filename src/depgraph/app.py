"""Application entry: parameters in, results out, exit codes."""
import sys

from .cli import MODE_TEST, ConfigError, format_config, parse_args
from .errors import ToolError
from .graph import build_graph
from .plantuml import puml_path, render_png, to_plantuml, write_file
from .registry import NpmRegistry, fetch_json
from .report import format_graph
from .repository import NpmRepository
from .testrepo import FileRepository, TestRepoError

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_CONFIG = 2


def open_test_repo(config):
    """Return the test repository (inverted in reverse mode)."""
    repo = FileRepository.load(config.repo)
    if not repo.has(config.package):
        raise TestRepoError(
            f"пакет '{config.package}' не найден в тестовом репозитории")
    return repo.reversed() if config.reverse else repo


def open_source(config, fetch):
    """Return ``(repository, root node)`` for the configured source."""
    if config.repo_mode == MODE_TEST:
        return open_test_repo(config), config.package
    repo = NpmRepository(NpmRegistry(config.repo, fetch))
    return repo, repo.root(config.package, config.version)


def analyse(config, fetch):
    """Build the dependency graph and print its report.

    Returns the graph and the title used for the diagram.
    """
    repo, root = open_source(config, fetch)
    graph = build_graph(repo, root, config.max_depth)
    kind = "Обратные зависимости" if config.reverse else "Граф зависимостей"
    lines = format_graph(graph, config.max_depth, f"{kind} {root}",
                         config.reverse)
    print("\n".join(lines))
    for warning in repo.warnings:
        print(f"предупреждение: {warning}", file=sys.stderr)
    return graph, f"{kind} {root} (глубина не более {config.max_depth})"


def visualize(graph, title, config, render):
    """Write the PlantUML source and the PNG image of the graph."""
    text = to_plantuml(graph, title, config.reverse)
    if config.print_puml:
        print(text, end="")
    path = puml_path(config.output)
    write_file(path, text)
    image = render(text, config.plantuml_jar, config.plantuml_server)
    write_file(config.output, image)
    print(f"Исходник PlantUML: {path}")
    print(f"Изображение графа: {config.output}")


def main(argv=None, fetch=fetch_json, render=render_png):
    """Run the tool and return the process exit code.

    ``fetch`` downloads JSON documents and ``render`` turns PlantUML text
    into PNG bytes; tests replace both by fakes.
    """
    try:
        config = parse_args(argv)
    except ConfigError as exc:
        print(f"ошибка: {exc}", file=sys.stderr)
        return EXIT_CONFIG
    if config.show_config:
        print("\n".join(format_config(config)))
    try:
        graph, title = analyse(config, fetch)
        visualize(graph, title, config, render)
    except ToolError as exc:
        print(f"ошибка: {exc}", file=sys.stderr)
        return EXIT_ERROR
    return EXIT_OK
