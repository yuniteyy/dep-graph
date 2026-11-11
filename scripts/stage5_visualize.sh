#!/bin/sh
# Этап 5: PlantUML и PNG для трёх пакетов, цикла и обратных зависимостей.
# Нужны Java и Graphviz; путь к plantuml.jar задаётся переменной
# PLANTUML_JAR (без неё используется PlantUML-сервер из --plantuml-server).
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT" || exit 1
RUN="./run.sh"
URL="https://registry.npmjs.org"
REPOS="examples/repos"
mkdir -p out

try() {
    echo "--- $*"
    "$RUN" "$@"
    echo "код возврата: $?"
}

echo "=== Три реальных пакета (полный граф)"
try --package express --repo "$URL" --version 4.18.2 --max-depth 20 \
    --output out/express.png
try --package mocha --repo "$URL" --version 10.2.0 --max-depth 20 \
    --output out/mocha.png
try --package react-dom --repo "$URL" --version 18.2.0 --max-depth 20 \
    --print-puml --output out/react-dom.png
echo "=== Ограничение глубины на реальном пакете"
try --package express --repo "$URL" --version 4.18.2 --max-depth 1 \
    --output out/express_depth1.png
echo "=== Тестовый репозиторий: ромбы, цикл, обратные зависимости"
try --repo-mode test --repo "$REPOS/wide.txt" --package A --max-depth 10 \
    --output out/test_wide.png
try --repo-mode test --repo "$REPOS/cycle.txt" --package A --max-depth 10 \
    --print-puml --output out/test_cycle.png
try --repo-mode test --repo "$REPOS/wide.txt" --package K --reverse \
    --max-depth 10 --output out/test_reverse.png
echo "=== Ошибки визуализации"
try --repo-mode test --repo "$REPOS/simple.txt" --package A \
    --plantuml-jar /no/such/plantuml.jar
echo "--- недоступный PlantUML-сервер (jar не задан)"
env PLANTUML_JAR= "$RUN" --repo-mode test --repo "$REPOS/simple.txt" \
    --package A --plantuml-server http://127.0.0.1:9 \
    --output out/unreachable.png
echo "код возврата: $?"
