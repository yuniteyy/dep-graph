#!/bin/sh
# Этап 5: сравнение графов depgraph со штатным npm (npm ls --all).
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT" || exit 1
for spec in express@4.18.2 mocha@10.2.0 react-dom@18.2.0 jest@29.5.0; do
    python3 scripts/compare_with_npm.py "$spec"
done
