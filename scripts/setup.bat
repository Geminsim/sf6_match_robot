@echo off
setlocal

cd /d "%~dp0.."

if not exist .venv (
    echo Creating virtual environment...
    py -m venv .venv
)

call .venv\Scripts\activate.bat

echo Upgrading pip...
python -m pip install --upgrade pip

echo Installing requirements...
pip install -r requirements.txt

if not exist .env (
    copy .env.example .env
    echo Created .env from template. Please fill in DISCORD_TOKEN before running the bot.
)

echo.
echo Setup complete! 
echo To activate the virtual environment, run: .venv\Scripts\activate
echo To start the bot, run: scripts\run.bat (or python main.py)
pause
