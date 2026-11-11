@echo off
rem Этап 2: прямые зависимости пакета из реального реестра npm.
set "ROOT=%~dp0..\"
cd /d "%ROOT%"
set "URL=https://registry.npmjs.org"

echo === Пакеты с зависимостями
call run.bat --package express --repo %URL% --version 4.18.2
call run.bat --package chalk --repo %URL% --version 2.4.2
call run.bat --package @babel/code-frame --repo %URL% --version 7.22.5
echo === Пакет без зависимостей
call run.bat --package is-number --repo %URL% --version 7.0.0
echo === Ошибки
call run.bat --package no-such-package-zzz-123 --repo %URL% --version 1.0.0
call run.bat --package express --repo %URL% --version 99.0.0
call run.bat --package express --repo http://127.0.0.1:9 --version 4.18.2
call run.bat --package express --repo https://registry.invalid --version 4.18.2
