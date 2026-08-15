@echo off
title Apagar ERP El Sauce
color 0C

echo ==========================================
echo    APAGANDO SERVIDORES ERP EL SAUCE
echo ==========================================
echo.
echo Cerrando ventanas de los servidores...

:: Cierra usando el título de la ventana que establecimos en 02_Iniciar.bat
taskkill /FI "WINDOWTITLE eq ERP_Backend*" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq ERP_Frontend*" /T /F >nul 2>&1

echo Liberando puertos 8000 (Frontend) y 8001 (Backend)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000') do taskkill /F /PID %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8001') do taskkill /F /PID %%a >nul 2>&1

echo.
echo ==========================================
echo    SERVIDORES APAGADOS COMPLETAMENTE
echo ==========================================
pause
