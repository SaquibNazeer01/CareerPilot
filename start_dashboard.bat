@echo off
title AutoApply Studio Dashboard
echo =======================================================
echo    AutoApply Studio — Job Automation Command Center
echo =======================================================

:: Auto-detect verified Python environment
set "PY_CMD=python"
if exist "C:\Program Files\Python312\python.exe" set "PY_CMD=C:\Program Files\Python312\python.exe"
if exist "%USERPROFILE%\anaconda3\python.exe" set "PY_CMD=%USERPROFILE%\anaconda3\python.exe"

echo Using Python: %PY_CMD%
echo Starting local web server on http://127.0.0.1:5000 ...
start "" "http://127.0.0.1:5000"
"%PY_CMD%" server.py
pause
