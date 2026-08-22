@echo off
setlocal
cd /d "%~dp0\.."

if not exist .venv\Scripts\python.exe python -m venv .venv
.venv\Scripts\python.exe -c "import fastapi, sqlalchemy, pdfplumber, openpyxl, reportlab" >nul 2>&1
if errorlevel 1 .venv\Scripts\pip.exe install -r backend\requirements.txt

if not exist node_modules npm install

start "Hera Backend" /min cmd /c "cd backend && ..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
echo.
echo Hera iniciado. Abra http://127.0.0.1:3000 no navegador.
echo.
npm run dev -- --host 127.0.0.1 --port 3000
