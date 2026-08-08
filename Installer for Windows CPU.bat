@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

echo ==============================================
echo    Adding-manga-chapters - Installer (CPU)
echo ==============================================

rem ---- 1. Detect Python (python or py launcher) ----
set "PY=python"
where python >nul 2>nul
if errorlevel 1 (
    where py >nul 2>nul
    if errorlevel 1 (
        echo [ERROR] Python is not installed or not in PATH.
        echo Install Python 3.10+ from https://www.python.org/downloads/
        pause
        exit /b 1
    )
    set "PY=py -3"
)

rem ---- Check Python version (must be 3.10+) ----
set "PYVER="
for /f "tokens=2 delims= " %%v in ('%PY% --version 2^>^&1') do if not defined PYVER set "PYVER=%%v"
for /f "tokens=1,2 delims=." %%a in ("%PYVER%") do set "PYMAJOR=%%a" & set "PYMINOR=%%b"

if not "%PYMAJOR%"=="3" goto :bad_python
if %PYMINOR% LSS 10 goto :old_python
echo [OK] Python detected: %PYVER%
goto :python_ok

:bad_python
echo [ERROR] Unsupported Python version: %PYVER%
echo Install Python 3.10+ from https://www.python.org/downloads/
pause
exit /b 1

:old_python
echo [WARNING] Python %PYVER% is older than 3.10. It may not work correctly.
echo Continue anyway? Press Ctrl+C to abort.
pause
goto :python_ok

:python_ok

rem ---- 2. Create virtual environment if it does not exist ----
if not exist "venv\Scripts\python.exe" (
    echo [1/4] Creating virtual environment...
    %PY% -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create the virtual environment.
        pause
        exit /b 1
    )
) else (
    echo [1/4] Virtual environment already exists.
)

rem ---- 3. Install dependencies into the virtual environment ----
echo [2/4] Updating pip...
"venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 (
    echo [ERROR] Failed to update pip.
    pause
    exit /b 1
)

echo [3/4] Installing dependencies...
"venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

rem ---- 4. Run the program automatically ----
echo [4/4] Starting the program...
set "SOURCE_DIR=%~1"
if "%SOURCE_DIR%"=="" set /p "SOURCE_DIR=Enter the path to the folder with manga chapters: "
if "%SOURCE_DIR%"=="" set "SOURCE_DIR=."

"venv\Scripts\python.exe" "Архивирование-глав-(Archiving-chapters).py" -i "%SOURCE_DIR%"
if errorlevel 1 (
    echo [ERROR] The program finished with an error (exit code %errorlevel%).
)

pause
endlocal
