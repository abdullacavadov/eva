@echo off
chcp 65001 >nul
cd /d "%~dp0"

REM E.V.A üçün bütün girişlər vahid launcher-dən keçir.
REM Launcher UI yaradıldıqdan sonra Start.mp3-ü bir dəfə səsləndirir.
if exist "venv\Scripts\pythonw.exe" (
    "venv\Scripts\pythonw.exe" launcher.py
) else if exist "venv\Scripts\python.exe" (
    "venv\Scripts\python.exe" launcher.py
) else (
    start "" pythonw launcher.py
)
