"""Command-line parameters of the tool and the checks of their values."""
import argparse
import os
import re
from dataclasses import dataclass
from urllib.parse import urlparse

MODE_REMOTE = "remote"
MODE_TEST = "test"
MODES = (MODE_REMOTE, MODE_TEST)
DEFAULT_OUTPUT = "graph.png"
DEFAULT_MAX_DEPTH = 3
MIN_DEPTH = 1
MAX_NAME_LENGTH = 214
OUTPUT_SUFFIX = ".png"
DEFAULT_SERVER = "https://www.plantuml.com/plantuml"
JAR_ENV = "PLANTUML_JAR"
HTTP_SCHEMES = ("http", "https")
NPM_NAME = re.compile(
    r"(@[a-z0-9~-][a-z0-9._~-]*/)?[a-z0-9~-][a-z0-9._~-]*")
TEST_NAME = re.compile(r"[A-Z]+")
SEMVER = re.compile(
    r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    r"(-[0-9A-Za-z.-]+)?(\+[0-9A-Za-z.-]+)?")


class ConfigError(Exception):
    """A user-supplied parameter has an invalid value."""


@dataclass
class Config:
    """Validated parameters given by the user."""

    package: str
    repo: str
    repo_mode: str = MODE_REMOTE
    version: str = None
    output: str = DEFAULT_OUTPUT
    max_depth: int = DEFAULT_MAX_DEPTH
    show_config: bool = False
    reverse: bool = False
    plantuml_jar: str = None
    plantuml_server: str = DEFAULT_SERVER
    print_puml: bool = False


def _add_analysis_options(parser):
    """Add the options that select what is analysed."""
    parser.add_argument(
        "--package", required=True, metavar="NAME",
        help="name of the analysed package")
    parser.add_argument(
        "--repo", required=True, metavar="URL_OR_PATH",
        help="registry URL (remote mode) or test repository file (test)")
    parser.add_argument(
        "--repo-mode", choices=MODES, default=MODE_REMOTE,
        help="remote: real npm registry by URL; test: graph from a file")
    parser.add_argument(
        "--version", metavar="X.Y.Z",
        help="exact package version (required in remote mode)")
    parser.add_argument(
        "--max-depth", default=str(DEFAULT_MAX_DEPTH), metavar="N",
        help="maximum depth of dependency analysis (default: %(default)s)")
    parser.add_argument(
        "--reverse", action="store_true",
        help="show reverse dependencies: packages that depend on the "
             "given one (test repository only)")


def _add_output_options(parser):
    """Add the options of the visualization and diagnostics."""
    parser.add_argument(
        "--output", default=DEFAULT_OUTPUT, metavar="FILE.png",
        help="name of the generated image file (default: %(default)s)")
    parser.add_argument(
        "--plantuml-jar", metavar="PATH", default=os.environ.get(JAR_ENV),
        help="local plantuml.jar used for rendering (default: env "
             f"{JAR_ENV}); without it a PlantUML server is used")
    parser.add_argument(
        "--plantuml-server", metavar="URL", default=DEFAULT_SERVER,
        help="PlantUML server used when no jar is given "
             "(default: %(default)s)")
    parser.add_argument(
        "--print-puml", action="store_true",
        help="print the PlantUML source of the graph")
    parser.add_argument(
        "--show-config", action="store_true",
        help="print all parameters as key = value before the analysis")


def build_parser():
    """Create the argument parser of the tool."""
    parser = argparse.ArgumentParser(
        prog="depgraph",
        description="Visualizer of npm package dependency graphs.")
    _add_analysis_options(parser)
    _add_output_options(parser)
    return parser


def check_package(package, mode):
    """Validate the package name for the given repository ``mode``."""
    if not package.strip():
        raise ConfigError("имя пакета не может быть пустым")
    if mode == MODE_TEST:
        if not TEST_NAME.fullmatch(package):
            raise ConfigError(
                f"имя пакета тестового репозитория '{package}' должно "
                "состоять из заглавных латинских букв")
        return
    too_long = len(package) > MAX_NAME_LENGTH
    if too_long or not NPM_NAME.fullmatch(package):
        raise ConfigError(f"недопустимое имя npm-пакета '{package}'")


def check_url(url, what):
    """Validate that ``url`` is an http(s) URL with a host name."""
    parts = urlparse(url)
    if parts.scheme not in HTTP_SCHEMES or not parts.netloc:
        raise ConfigError(
            f"'{url}' не является URL {what} (http:// или https://)")


def check_remote_repo(repo):
    """Validate that ``repo`` is the URL of a registry."""
    check_url(repo, "репозитория")


def check_renderer(jar, server):
    """Validate the PlantUML jar path and the server URL."""
    if jar and not os.path.isfile(jar):
        raise ConfigError(f"файл plantuml.jar не найден: {jar}")
    check_url(server, "PlantUML-сервера")


def check_test_repo(path):
    """Validate that ``path`` is a readable test repository file."""
    if not os.path.exists(path):
        raise ConfigError(f"файл тестового репозитория не найден: {path}")
    if not os.path.isfile(path):
        raise ConfigError(f"'{path}' не является файлом")
    if not os.access(path, os.R_OK):
        raise ConfigError(f"нет доступа на чтение файла: {path}")


def check_repo(repo, mode):
    """Validate the repository location for the given ``mode``."""
    if mode == MODE_TEST:
        check_test_repo(repo)
    else:
        check_remote_repo(repo)


def check_version(version, mode):
    """Validate the exact package version (required in remote mode)."""
    if version is None:
        if mode == MODE_REMOTE:
            raise ConfigError("для режима remote необходимо указать --version")
        return
    if not SEMVER.fullmatch(version):
        raise ConfigError(
            f"версия '{version}' не соответствует формату X.Y.Z")


def check_reverse(reverse, mode):
    """Reverse dependencies need the whole repository, i.e. a test file."""
    if reverse and mode != MODE_TEST:
        raise ConfigError(
            "режим --reverse поддерживается только для тестового "
            "репозитория (--repo-mode test): реестр npm не позволяет "
            "найти все пакеты, зависящие от заданного")


def check_output(output):
    """Validate the name of the image file."""
    if not output.lower().endswith(OUTPUT_SUFFIX):
        raise ConfigError(f"файл изображения должен иметь расширение "
                          f"{OUTPUT_SUFFIX}: {output}")
    if os.path.isdir(output):
        raise ConfigError(f"'{output}' является каталогом")
    folder = os.path.dirname(output) or os.curdir
    if not os.path.isdir(folder):
        raise ConfigError(f"каталог для файла не существует: {folder}")
    if not os.access(folder, os.W_OK):
        raise ConfigError(f"нет доступа на запись в каталог: {folder}")


def parse_depth(text):
    """Convert the ``--max-depth`` text to a positive integer."""
    try:
        depth = int(text)
    except ValueError:
        raise ConfigError(
            f"максимальная глубина '{text}' не является числом") from None
    if depth < MIN_DEPTH:
        raise ConfigError(
            f"максимальная глубина должна быть не меньше {MIN_DEPTH}")
    return depth


def parse_args(argv=None):
    """Parse and validate ``argv``; return a :class:`Config`.

    Raises :class:`ConfigError` for invalid values; argparse itself exits
    for missing or unknown options.
    """
    values = build_parser().parse_args(argv)
    mode = values.repo_mode
    check_package(values.package, mode)
    check_repo(values.repo, mode)
    check_version(values.version, mode)
    check_output(values.output)
    check_reverse(values.reverse, mode)
    check_renderer(values.plantuml_jar, values.plantuml_server)
    return Config(
        package=values.package, repo=values.repo, repo_mode=mode,
        version=values.version, output=values.output,
        max_depth=parse_depth(values.max_depth),
        show_config=values.show_config, reverse=values.reverse,
        plantuml_jar=values.plantuml_jar,
        plantuml_server=values.plantuml_server,
        print_puml=values.print_puml)


def format_config(config):
    """Return the parameters as ``key = value`` lines."""
    return [
        f"package   = {config.package}",
        f"repo      = {config.repo}",
        f"repo_mode = {config.repo_mode}",
        f"version   = {config.version}",
        f"output    = {config.output}",
        f"max_depth = {config.max_depth}",
        f"reverse   = {config.reverse}",
        f"plantuml_jar    = {config.plantuml_jar}",
        f"plantuml_server = {config.plantuml_server}",
    ]
