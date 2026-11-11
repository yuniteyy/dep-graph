@echo off
set "ROOT=%~dp0"
set "PYTHONPATH=%ROOT%src"
if "%1"=="test" (
    python -m unittest discover -s "%ROOT%tests" -v
) else (
    python -m depgraph %*
)
