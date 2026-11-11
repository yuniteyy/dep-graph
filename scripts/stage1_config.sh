#!/bin/sh
# Этап 1: параметры, их вывод и обработка ошибок для каждого параметра.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT" || exit 1
RUN="./run.sh"
URL="https://registry.npmjs.org"
REPO="examples/repos/simple.txt"
mkdir -p out/dir.png

try() {
    echo "--- $*"
    "$RUN" "$@"
    echo "код возврата: $?"
}

echo "=== Корректные запуски"
try --package express --repo "$URL" --version 4.18.2
try --package express --repo "$URL" --version 4.18.2 \
    --output out/express.png --max-depth 5
try --package @types/node --repo "$URL" --version 20.1.0
try --package A --repo "$REPO" --repo-mode test --max-depth 2

echo "=== Ошибки: имя пакета"
try --package "" --repo "$URL" --version 1.0.0
try --package Express --repo "$URL" --version 1.0.0
try --package ab --repo "$REPO" --repo-mode test
echo "=== Ошибки: репозиторий"
try --package express --repo registry --version 1.0.0
try --package express --repo ftp://example.org --version 1.0.0
try --package A --repo no_such_file.txt --repo-mode test
try --package A --repo examples --repo-mode test
echo "=== Ошибки: режим"
try --package A --repo "$REPO" --repo-mode other
echo "=== Ошибки: версия"
try --package express --repo "$URL"
try --package express --repo "$URL" --version 1.2
try --package express --repo "$URL" --version "^1.2.3"
echo "=== Ошибки: файл изображения"
try --package express --repo "$URL" --version 1.0.0 --output graph.jpg
try --package express --repo "$URL" --version 1.0.0 --output no_dir/g.png
try --package express --repo "$URL" --version 1.0.0 --output out/dir.png
echo "=== Ошибки: глубина"
try --package express --repo "$URL" --version 1.0.0 --max-depth abc
try --package express --repo "$URL" --version 1.0.0 --max-depth 0
try --package express --repo "$URL" --version 1.0.0 --max-depth -2
echo "=== Ошибки: обязательные параметры"
try --repo "$URL" --version 1.0.0
try --package express --version 1.0.0
