@echo off
rem Этап 5: PlantUML и PNG для трёх пакетов, цикла и обратных зависимостей.
rem Нужны Java и Graphviz; путь к plantuml.jar - переменная PLANTUML_JAR.
set "ROOT=%~dp0..\"
cd /d "%ROOT%"
set "URL=https://registry.npmjs.org"
set "REPOS=examples\repos"
if not exist out mkdir out

echo === Три реальных пакета (полный граф)
call run.bat --package express --repo %URL% --version 4.18.2 --max-depth 20 --output out\express.png
call run.bat --package mocha --repo %URL% --version 10.2.0 --max-depth 20 --output out\mocha.png
call run.bat --package react-dom --repo %URL% --version 18.2.0 --max-depth 20 --print-puml --output out\react-dom.png
echo === Тестовый репозиторий: ромбы, цикл, обратные зависимости
call run.bat --repo-mode test --repo %REPOS%\wide.txt --package A --max-depth 10 --output out\test_wide.png
call run.bat --repo-mode test --repo %REPOS%\cycle.txt --package A --max-depth 10 --output out\test_cycle.png
call run.bat --repo-mode test --repo %REPOS%\wide.txt --package K --reverse --max-depth 10 --output out\test_reverse.png
echo === Ошибки визуализации
call run.bat --repo-mode test --repo %REPOS%\simple.txt --package A --plantuml-jar C:\no\such\plantuml.jar
set "PLANTUML_JAR="
set "DEAD=http://127.0.0.1:9"
call run.bat --repo-mode test --repo %REPOS%\simple.txt --package A ^
    --plantuml-server %DEAD% --output out\unreachable.png
