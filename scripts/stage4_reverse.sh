#!/bin/sh
# Этап 4: обратные зависимости (--reverse) на разных тестовых репозиториях.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT" || exit 1
RUN="./run.sh"
REPOS="examples/repos"

try() {
    echo "--- $*"
    "$RUN" "$@"
    echo "код возврата: $?"
}

rev() {
    file="$1"
    shift
    try --repo-mode test --repo "$REPOS/$file" --reverse "$@"
}

echo "=== Дерево с общей зависимостью: кто зависит от D"
rev simple.txt --package D
echo "=== Пакет, от которого никто не зависит (корень)"
rev simple.txt --package A
echo "=== Прямые обратные зависимости (глубина 1) и полные"
rev wide.txt --package K --max-depth 1
rev wide.txt --package K --max-depth 10
rev wide.txt --package M --max-depth 10
echo "=== Циклы"
rev cycle.txt --package A --max-depth 10
rev self_loop.txt --package B
rev two_cycles.txt --package C --max-depth 10
echo "=== Упоминаемый, но не описанный пакет"
rev undefined.txt --package X
echo "=== Сравнение с прямым режимом"
try --repo-mode test --repo "$REPOS/simple.txt" --package A
rev simple.txt --package E
echo "=== Ошибки"
rev simple.txt --package Q
rev invalid/duplicate.txt --package A
try --package chalk --repo https://registry.npmjs.org --version 2.4.2 \
    --reverse
