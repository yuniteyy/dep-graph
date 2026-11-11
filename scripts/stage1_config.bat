@echo off
rem Этап 1: параметры, их вывод и обработка ошибок.
set "ROOT=%~dp0..\"
cd /d "%ROOT%"
set "URL=https://registry.npmjs.org"
set "REPO=examples\repos\simple.txt"
if not exist out\dir.png mkdir out\dir.png

echo === Корректные запуски
call run.bat --package express --repo %URL% --version 4.18.2
call run.bat --package express --repo %URL% --version 4.18.2 --output out\express.png --max-depth 5
call run.bat --package A --repo %REPO% --repo-mode test --max-depth 2

echo === Ошибки: имя пакета
call run.bat --package Express --repo %URL% --version 1.0.0
call run.bat --package ab --repo %REPO% --repo-mode test
echo === Ошибки: репозиторий
call run.bat --package express --repo registry --version 1.0.0
call run.bat --package A --repo no_such_file.txt --repo-mode test
call run.bat --package A --repo examples --repo-mode test
echo === Ошибки: режим
call run.bat --package A --repo %REPO% --repo-mode other
echo === Ошибки: версия
call run.bat --package express --repo %URL%
call run.bat --package express --repo %URL% --version 1.2
echo === Ошибки: файл изображения
call run.bat --package express --repo %URL% --version 1.0.0 --output graph.jpg
call run.bat --package express --repo %URL% --version 1.0.0 --output no_dir\g.png
call run.bat --package express --repo %URL% --version 1.0.0 --output out\dir.png
echo === Ошибки: глубина
call run.bat --package express --repo %URL% --version 1.0.0 --max-depth abc
call run.bat --package express --repo %URL% --version 1.0.0 --max-depth 0
echo === Ошибки: обязательные параметры
call run.bat --repo %URL% --version 1.0.0
