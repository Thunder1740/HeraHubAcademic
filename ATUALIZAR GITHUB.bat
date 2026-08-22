@echo off
setlocal
cd /d "%~dp0"

where git >nul 2>nul
if errorlevel 1 (
  echo O Git nao foi encontrado neste computador.
  echo Instale o Git antes de tentar atualizar o repositorio.
  pause
  exit /b 1
)

git add .
git diff --cached --quiet
if not errorlevel 1 (
  echo Nenhuma alteracao nova para enviar.
  pause
  exit /b 0
)

for /f "tokens=1-3 delims=/ " %%a in ("%date%") do set DATA=%%a-%%b-%%c
for /f "tokens=1-2 delims=: " %%a in ("%time%") do set HORA=%%a-%%b
git commit -m "Atualizacao do Hera %DATA% %HORA%"
if errorlevel 1 goto :erro

git push
if errorlevel 1 goto :erro

echo.
echo Atualizacao enviada ao GitHub com sucesso.
pause
exit /b 0

:erro
echo.
echo Nao foi possivel concluir o envio. Verifique a conexao e tente novamente.
pause
exit /b 1
