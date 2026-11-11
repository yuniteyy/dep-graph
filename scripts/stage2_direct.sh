#!/bin/sh
# Этап 2: прямые зависимости пакета из реального реестра npm.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT" || exit 1
RUN="./run.sh"
URL="https://registry.npmjs.org"

try() {
    echo "--- $*"
    "$RUN" "$@"
    echo "код возврата: $?"
}

echo "=== Пакеты с зависимостями"
try --package express --repo "$URL" --version 4.18.2
try --package chalk --repo "$URL" --version 2.4.2
try --package @babel/code-frame --repo "$URL" --version 7.22.5
echo "=== Пакет без зависимостей"
try --package is-number --repo "$URL" --version 7.0.0
echo "=== Другая версия того же пакета"
try --package express --repo "$URL" --version 3.0.0
echo "=== Ошибки"
try --package no-such-package-zzz-123 --repo "$URL" --version 1.0.0
try --package express --repo "$URL" --version 99.0.0
try --package express --repo http://127.0.0.1:9 --version 4.18.2
try --package express --repo https://registry.invalid --version 4.18.2
try --package express --repo "$URL/nonexistent-prefix" --version 4.18.2
try --package A --repo examples/repos/simple.txt --repo-mode test
