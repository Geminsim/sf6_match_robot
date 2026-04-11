@echo off
REM Run the SF6 Match Robot bot on Windows.
cd /d "%~dp0\.."

if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
)

python main.py
pause
