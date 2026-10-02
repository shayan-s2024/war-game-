@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "ROOT=%~dp0"
set "BACKEND=%ROOT%backend"
set "FRONTEND=%ROOT%frontend"
set "PYTHON="

cls
echo ========================================
echo       WW3 Local Development Launcher
echo ========================================
echo.

where py >nul 2>nul
if not errorlevel 1 set "PYTHON=py -3"
if not defined PYTHON (
    where python >nul 2>nul
    if not errorlevel 1 set "PYTHON=python"
)
if not defined PYTHON (
    echo [ERROR] Python was not found in PATH.
    pause
    exit /b 1
)
where npm >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Node.js / npm was not found in PATH.
    pause
    exit /b 1
)

if not exist "%BACKEND%\venv\Scripts\python.exe" (
    echo [INFO] Creating backend virtual environment...
    pushd "%BACKEND%"
    %PYTHON% -m venv venv
    if errorlevel 1 (
        popd
        echo [ERROR] Could not create backend virtual environment.
        pause
        exit /b 1
    )
    popd
)
set "VENV_PY=%BACKEND%\venv\Scripts\python.exe"

"%VENV_PY%" -c "import django, daphne" >nul 2>nul
if errorlevel 1 (
    echo [INFO] Installing local SQLite backend dependencies...
    pushd "%BACKEND%"
    call venv\Scripts\python.exe -m pip install --upgrade pip
    call venv\Scripts\python.exe -m pip install -r requirements-local.txt
    if errorlevel 1 (
        popd
        echo [ERROR] Backend dependency installation failed.
        pause
        exit /b 1
    )
    rem Pillow 10.3 can attempt a source build on newer CPython. Keep a wheel-only local install.
    call venv\Scripts\python.exe -m pip install --only-binary=:all: "Pillow>=12.0.0"
    if errorlevel 1 (
        popd
        echo [ERROR] Pillow wheel installation failed. Use Python 3.14 x64 on Windows.
        pause
        exit /b 1
    )
    popd
)

pushd "%BACKEND%"
echo [INFO] Running database migrations...
call venv\Scripts\python.exe manage.py migrate --noinput
if errorlevel 1 (
    popd
    echo [ERROR] Django migrations failed.
    pause
    exit /b 1
)

echo [INFO] Syncing country data and command names...
call venv\Scripts\python.exe manage.py seed_gamedata
if errorlevel 1 (
    echo [WARN] Country seed failed; existing database will be used.
)
popd

netstat -ano | findstr /R /C:":8000 .*LISTENING" >nul 2>nul
if errorlevel 1 (
    echo [INFO] Starting backend on http://127.0.0.1:8000 ...
    start "WW3 Backend" /D "%BACKEND%" cmd /k "echo ======================================== && echo            WW3 Backend (Daphne) && echo ======================================== && echo. && venv\Scripts\daphne.exe -b 0.0.0.0 -p 8000 config.asgi:application"
) else (
    echo [INFO] Backend is already running on port 8000.
)

echo [INFO] Waiting for backend...
set /a ATTEMPTS=0
:WAIT_BACKEND
set /a ATTEMPTS+=1
netstat -ano | findstr /R /C:":8000 .*LISTENING" >nul 2>nul
if not errorlevel 1 goto BACKEND_READY
if !ATTEMPTS! GEQ 30 goto BACKEND_FAILED
timeout /t 1 /nobreak >nul
goto WAIT_BACKEND

:BACKEND_READY
echo [OK] Backend is listening on port 8000.
echo.

pushd "%FRONTEND%"
if not exist "node_modules" (
    echo [INFO] Installing frontend dependencies...
    call npm install
    if errorlevel 1 (
        popd
        echo [ERROR] npm install failed.
        pause
        exit /b 1
    )
)

echo.
echo ========================================
echo       Starting WW3 Frontend (Vite)
echo ========================================
echo.
echo [OK] Backend:  http://127.0.0.1:8000
echo [OK] Frontend: http://localhost:5173
echo.
call npm run dev -- --host 0.0.0.0
set "FRONTEND_EXIT=%ERRORLEVEL%"
popd

if not "%FRONTEND_EXIT%"=="0" (
    echo.
    echo [ERROR] Frontend stopped with exit code %FRONTEND_EXIT%.
    pause
    exit /b %FRONTEND_EXIT%
)
endlocal
exit /b 0

:BACKEND_FAILED
echo.
echo [ERROR] Backend did not start listening on port 8000.
echo [INFO] Check the separate WW3 Backend window.
echo.
pause
exit /b 1
