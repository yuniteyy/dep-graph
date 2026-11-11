@echo off
rem Этап 4: обратные зависимости (--reverse) на тестовых репозиториях.
set "ROOT=%~dp0..\"
cd /d "%ROOT%"
set "REPOS=examples\repos"

echo === Дерево с общей зависимостью: кто зависит от D
call run.bat --repo-mode test --repo %REPOS%\simple.txt --reverse --package D
echo === Пакет, от которого никто не зависит
call run.bat --repo-mode test --repo %REPOS%\simple.txt --reverse --package A
echo === Глубина 1 и полный граф
call run.bat --repo-mode test --repo %REPOS%\wide.txt --reverse --package K --max-depth 1
call run.bat --repo-mode test --repo %REPOS%\wide.txt --reverse --package M --max-depth 10
echo === Циклы
call run.bat --repo-mode test --repo %REPOS%\cycle.txt --reverse --package A --max-depth 10
call run.bat --repo-mode test --repo %REPOS%\self_loop.txt --reverse --package B
echo === Ошибки
call run.bat --repo-mode test --repo %REPOS%\simple.txt --reverse --package Q
call run.bat --package chalk --repo https://registry.npmjs.org --version 2.4.2 --reverse
