@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ==============================================
echo    Building "Manga Chapter Tools.exe"
echo ==============================================
"venv\Scripts\python.exe" build_exe.py
if errorlevel 1 (
    echo [ERROR] Build failed. See messages above.
    pause
    exit /b 1
)
pause
