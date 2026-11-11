"""Application entry: parameters in, results out, exit codes."""
import sys

from .cli import ConfigError, format_config, parse_args

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_CONFIG = 2


def main(argv=None):
    """Run the tool and return the process exit code."""
    try:
        config = parse_args(argv)
    except ConfigError as exc:
        print(f"ошибка: {exc}", file=sys.stderr)
        return EXIT_CONFIG
    print("\n".join(format_config(config)))
    return EXIT_OK
