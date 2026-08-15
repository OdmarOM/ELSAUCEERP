@echo off
title Iniciar ERP El Sauce
color 0A

echo ==========================================
echo    INICIANDO SERVIDORES ERP EL SAUCE
echo ==========================================
echo.

echo [1] Iniciando Backend en nueva ventana...
start "ERP_Backend" cmd /k "title ERP_Backend && color 0A && cd backend && call venv\Scripts\activate && uvicorn app.main:app --host 0.0.0.0 --port 8001"

echo [2] Iniciando Frontend en nueva ventana...
start "ERP_Frontend" cmd /k "title ERP_Frontend && color 0B && cd frontend && npm run dev"

echo.
echo ==========================================
echo    SISTEMA INICIADO
echo    (Se abrieron dos ventanas negras extra, NO LAS CIERRES)
echo    Puedes cerrar esta ventana.
echo ==========================================
pause
