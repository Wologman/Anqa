@echo off
cd /d "%~dp0"

REM --- Check uv is installed, install via winget if missing ---
where uv >nul 2>nul
if errorlevel 1 (
    echo uv not found - installing it now via winget...
    winget install --id astral-sh.uv --exact --accept-package-agreements --accept-source-agreements
    if errorlevel 1 (
        echo.
        echo Automatic install failed. Please contact Olly for help.
        pause
        exit /b 1
    )
    echo.
    echo uv installed. Refreshing this window...
    REM refresh PATH in this session so 'uv' is found without reopening the window
    for /f "usebackq tokens=2,*" %%A in (`reg query "HKCU\Environment" /v Path 2^>nul`) do set "USERPATH=%%B"
    set "PATH=%USERPATH%;%PATH%"
    where uv >nul 2>nul
    if errorlevel 1 (
        echo.
        echo uv was installed but this window can't see it yet.
        echo Please close this window and double-click the launcher again.
        pause
        exit /b 1
    )
)

REM --- Build the environment on first run ---
if not exist ".venv" (
    echo First time setup - this may take a few minutes...
    echo.
    uv sync --extra notebook
    if errorlevel 1 (
        echo.
        echo Setup failed. Please contact Olly with the error above.
        pause
        exit /b 1
    )
    uv run python -m ipykernel install --user --name python3 --display-name "Python (anqa)"
    echo.
    echo Setup complete!
    echo.
)

echo Starting the annotation tool...
echo A browser window should open automatically.
echo Keep this window open while you work - closing it will stop the tool.
echo.

uv run python config_editor.py
uv run voila notebooks\annotation.ipynb

pause