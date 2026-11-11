#!/bin/sh
# Этап 3: граф зависимостей (BFS, глубина, циклы), тестовый и реальный режим.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT" || exit 1
RUN="./run.sh"
URL="https://registry.npmjs.org"
REPOS="examples/repos"

try() {
    echo "--- $*"
    "$RUN" "$@"
    echo "код возврата: $?"
}

test_repo() {
    file="$1"
    shift
    try --repo-mode test --repo "$REPOS/$file" "$@"
}

echo "=== Тестовый репозиторий: дерево и ромбы"
test_repo simple.txt --package A
test_repo wide.txt --package A --max-depth 10
test_repo wide.txt --package C --max-depth 10
echo "=== Ограничение глубины на цепочке (1, 3, 10)"
test_repo chain.txt --package A --max-depth 1
test_repo chain.txt --package A --max-depth 3
test_repo chain.txt --package A --max-depth 10
echo "=== Циклические зависимости"
test_repo cycle.txt --package A --max-depth 10
test_repo self_loop.txt --package A
test_repo two_cycles.txt --package A --max-depth 10
test_repo cycle.txt --package A --max-depth 2
echo "=== Пакеты, которые только упоминаются"
test_repo undefined.txt --package A
echo "=== Ошибки тестового репозитория"
test_repo simple.txt --package Q
for bad in lowercase no_colon duplicate bad_dependency; do
    test_repo "invalid/$bad.txt" --package A
done
echo "=== Реальный реестр npm: глубина 1, 2 и полный граф"
try --package chalk --repo "$URL" --version 2.4.2 --max-depth 1
try --package chalk --repo "$URL" --version 2.4.2 --max-depth 2
try --package chalk --repo "$URL" --version 2.4.2 --max-depth 10
try --package express --repo "$URL" --version 4.18.2 --max-depth 2
echo "=== Реальный реестр: пакет без зависимостей и scope-пакет"
try --package is-number --repo "$URL" --version 7.0.0
try --package @babel/code-frame --repo "$URL" --version 7.22.5 \
    --max-depth 10
echo "=== Реальный реестр: ошибки"
try --package express --repo "$URL" --version 99.0.0
try --package no-such-package-zzz-123 --repo "$URL" --version 1.0.0
