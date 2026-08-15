@echo off
title Recompilar ERP El Sauce
color 0E

echo ==========================================
echo    ACTUALIZANDO Y RECOMPILANDO FRONTEND
echo ==========================================
echo.

cd frontend
echo [1] Actualizando paquetes (npm install)...
call npm install

echo.
echo [2] Compilando el proyecto Vue (npm run build)...
call npm run build

cd ..

echo.
echo ==========================================
echo    RECOMPILACION FINALIZADA
echo ==========================================
pause
