@echo off
rem One-click publish for everyone. Clones the repo to a LOCAL folder (not OneDrive) on first run.
rem Problems are written to logs\<username>.log in this folder so we can see who is stuck and why.
set "LOGDIR=%~dp0logs"
if not exist "%LOGDIR%" mkdir "%LOGDIR%"
set "LOG=%LOGDIR%\%USERNAME%.log"
set "REPO=%USERPROFILE%\Shared-Scheduler"

where git >nul 2>nul
if errorlevel 1 (
    echo [%date% %time%] %USERNAME%: Git is not installed >> "%LOG%"
    echo.
    echo Git is not installed. Install "Git for Windows" from https://git-scm.com/download/win and run this again.
    pause
    exit /b 1
)
where python >nul 2>nul
if errorlevel 1 (
    echo [%date% %time%] %USERNAME%: Python is not installed >> "%LOG%"
    echo.
    echo Python is not installed. Install Python from https://www.python.org/downloads/ ^(tick "Add python.exe to PATH"^) and run this again.
    pause
    exit /b 1
)
if not exist "%REPO%\.git" (
    echo First run: cloning repo to %REPO% ...
    git clone https://github.com/FolderNew/Shared-Scheduler.git "%REPO%"
    if errorlevel 1 (
        echo [%date% %time%] %USERNAME%: git clone failed >> "%LOG%"
        echo Clone failed - check internet / GitHub access to FolderNew/Shared-Scheduler.
        pause
        exit /b 1
    )
)
cd /d "%REPO%"
git pull --rebase --autostash
if errorlevel 1 echo [%date% %time%] %USERNAME%: git pull failed >> "%LOG%"
python publish.py
if errorlevel 1 (
    echo.
    echo Something went wrong. Please send the file  %LOG%  to Virat.
)
pause
