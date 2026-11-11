#!/bin/sh
ROOT="$(cd "$(dirname "$0")" && pwd)"
export PYTHONPATH="$ROOT/src"
if [ "$1" = "test" ]; then
    shift
    exec python3 -m unittest discover -s "$ROOT/tests" -v "$@"
fi
exec python3 -m depgraph "$@"
