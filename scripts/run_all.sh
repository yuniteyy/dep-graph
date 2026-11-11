#!/bin/sh
# Запуск всех проверочных скриптов подряд (нужны сеть, Java, Graphviz).
DIR="$(cd "$(dirname "$0")" && pwd)"
for script in stage1_config stage2_direct stage3_graph stage4_reverse \
        stage5_visualize stage5_compare; do
    echo "################ $script"
    "$DIR/$script.sh" || exit 1
done
