@echo off
rem Этап 3: граф зависимостей (BFS, глубина, циклы), тестовый и реальный режим.
set "ROOT=%~dp0..\"
cd /d "%ROOT%"
set "URL=https://registry.npmjs.org"
set "REPOS=examples\repos"

echo === Тестовый репозиторий: дерево и ромбы
call run.bat --repo-mode test --repo %REPOS%\simple.txt --package A
call run.bat --repo-mode test --repo %REPOS%\wide.txt --package A --max-depth 10
echo === Ограничение глубины на цепочке (1, 3, 10)
call run.bat --repo-mode test --repo %REPOS%\chain.txt --package A --max-depth 1
call run.bat --repo-mode test --repo %REPOS%\chain.txt --package A --max-depth 3
call run.bat --repo-mode test --repo %REPOS%\chain.txt --package A --max-depth 10
echo === Циклические зависимости
call run.bat --repo-mode test --repo %REPOS%\cycle.txt --package A --max-depth 10
call run.bat --repo-mode test --repo %REPOS%\self_loop.txt --package A
call run.bat --repo-mode test --repo %REPOS%\two_cycles.txt --package A --max-depth 10
echo === Ошибки тестового репозитория
call run.bat --repo-mode test --repo %REPOS%\simple.txt --package Q
call run.bat --repo-mode test --repo %REPOS%\invalid\lowercase.txt --package A
call run.bat --repo-mode test --repo %REPOS%\invalid\duplicate.txt --package A
echo === Реальный реестр npm
call run.bat --package chalk --repo %URL% --version 2.4.2 --max-depth 1
call run.bat --package chalk --repo %URL% --version 2.4.2 --max-depth 10
call run.bat --package express --repo %URL% --version 4.18.2 --max-depth 2
echo === Реальный реестр: ошибки
call run.bat --package express --repo %URL% --version 99.0.0
