@echo off
title Servidor El Sauce ERP
color 0A

echo ==========================================
echo    INICIANDO EL SAUCE ERP (PRODUCCION)
echo ==========================================
echo.

:: CAMBIA ESTO por la ruta real donde pusiste la carpeta backend en el servidor
cd "C:\ERPELSAUCE\backend"

echo [1] Activando entorno virtual...
call venv\Scripts\activate

echo [2] Iniciando Servidor...
echo.
echo ==========================================
echo  EL SISTEMA ESTA ACTIVO. NO CIERRES ESTA VENTANA.
echo ==========================================
echo.

uvicorn app.main:app --host 0.0.0.0 --port 8000

pause