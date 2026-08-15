@echo off
title Instalar ERP El Sauce
color 0B

echo ==========================================
echo    INSTALANDO DEPENDENCIAS ERP EL SAUCE
echo ==========================================
echo.

echo [1] Instalando Backend (Python)...
cd backend
if exist venv (
    echo [AVISO] Eliminando entorno virtual venv existente...
    rmdir /s /q venv
)
echo Creando entorno virtual nuevo...
python -m venv venv
call venv\Scripts\activate
echo Actualizando pip e instalando dependencias...
python -m pip install --upgrade pip
pip install -r requirements.txt
cd ..

echo.
echo [2] Instalando Frontend (Node/Vue)...
cd frontend
call npm install
echo Compilando Frontend para produccion (opcional)...
call npm run build
cd ..

echo.
echo ==========================================
echo    INSTALACION COMPLETADA CON EXITO
echo ==========================================
pause
