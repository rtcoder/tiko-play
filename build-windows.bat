@echo off
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
if errorlevel 1 exit /b 1
call npm --prefix frontend ci
if errorlevel 1 exit /b 1
call npm --prefix frontend run build
if errorlevel 1 exit /b 1
.venv\Scripts\python.exe -m PyInstaller --noconfirm packaging\windows.spec
if errorlevel 1 exit /b 1
where ISCC.exe >nul 2>&1
if errorlevel 1 (
 echo Zainstaluj Inno Setup 6 i dodaj ISCC.exe do PATH. Aplikacja jest w dist\TikoPlay.
 exit /b 1
)
for /f "delims=" %%V in ('.venv\Scripts\python.exe release_support.py') do set "APP_VERSION=%%V"
if not defined APP_VERSION exit /b 1
ISCC.exe /DAppVersion=%APP_VERSION% packaging\windows.iss
if errorlevel 1 exit /b 1
echo Gotowe: dist\installer\TikoPlay-%APP_VERSION%-windows-x64-setup.exe
