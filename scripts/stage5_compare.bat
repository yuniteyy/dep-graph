@echo off
rem Этап 5: сравнение графов depgraph со штатным npm (npm ls --all).
set "ROOT=%~dp0..\"
cd /d "%ROOT%"
for %%S in (express@4.18.2 mocha@10.2.0 react-dom@18.2.0 jest@29.5.0) do (
    python scripts\compare_with_npm.py %%S
)
