@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" goto :NOENV

echo Starting Cat Snake Adventures...
".venv\Scripts\python.exe" -m cat_snake_adventures.main

echo.
pause

exit /b 0

:NOENV
echo.
echo Could not find the project's Python virtual environment.
echo.
echo Fix:
echo   1) Open PowerShell in this folder
echo   2) Run:  py -3.11 -m venv .venv
echo   3) Run:  .venv\Scripts\python.exe -m pip install -r requirements.txt
echo.
pause
exit /b 1
