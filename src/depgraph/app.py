"""Application entry: parameters in, results out, exit codes."""
import sys

from .cli import MODE_TEST, ConfigError, format_config, parse_args
from .registry import NpmRegistry, RegistryError, fetch_json

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_CONFIG = 2


def show_direct_dependencies(config, fetch):
    """Print the direct dependencies of the requested package version."""
    if config.repo_mode == MODE_TEST:
        raise RegistryError("тестовый режим будет доступен на этапе 3")
    registry = NpmRegistry(config.repo, fetch)
    deps = registry.direct_dependencies(config.package, config.version)
    print(f"Прямые зависимости {config.package}@{config.version}:")
    for name, spec in sorted(deps.items()):
        print(f"  {name}: {spec}")
    if not deps:
        print("  (нет зависимостей)")


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
        show_direct_dependencies(config, fetch)
    except RegistryError as exc:
        print(f"ошибка: {exc}", file=sys.stderr)
        return EXIT_ERROR
    return EXIT_OK
