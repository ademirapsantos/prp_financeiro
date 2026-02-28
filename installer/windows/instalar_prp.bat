@echo off
setlocal

set SCRIPT_DIR=%~dp0
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%install.ps1"

if errorlevel 1 (
  echo.
  echo Falha na instalacao. Veja as mensagens acima.
  pause
  exit /b 1
)

echo.
echo Instalacao concluida com sucesso.
pause

