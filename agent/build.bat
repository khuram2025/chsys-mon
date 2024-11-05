@echo off
echo Building CHSys Monitor Agent Package...

REM Create virtual environment
python -m venv venv
call venv\Scripts\activate.bat

REM Install required packages
echo Installing required packages...
pip install psutil requests wxPython pyinstaller

REM Download Python installer if not exists
if not exist "python-3.9.0-amd64.exe" (
    echo Downloading Python installer...
    powershell -Command "(New-Object System.Net.WebClient).DownloadFile('https://www.python.org/ftp/python/3.9.0/python-3.9.0-amd64.exe', 'python-3.9.0-amd64.exe')"
)

REM Create default config
echo Creating default config...
echo { > config.json
echo     "server_url": "http://10.51.0.15:8000/api/metrics", >> config.json
echo     "api_key": "your-api-key", >> config.json
echo     "interval": 30, >> config.json
echo     "log_level": "INFO" >> config.json
echo } >> config.json

REM Build executable
echo Building executable...
pyinstaller --clean --onedir ^
    --add-data "config.json;." ^
    --add-data "icons;icons" ^
    --hidden-import wx ^
    --hidden-import psutil ^
    --hidden-import requests ^
    --noconsole ^
    --name chsys_agent ^
    --icon=icons/connected.ico ^
    agent.py

REM Create output directory
if not exist "output" mkdir output

REM Build installer using Inno Setup
echo Building installer...
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" setup.iss

echo Build complete! MSI package is in the output directory
pause