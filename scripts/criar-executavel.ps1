$ErrorActionPreference = "Stop"
$project = Split-Path -Parent $PSScriptRoot
Set-Location $project

$python = Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"
if (-not (Test-Path $python)) { throw "Python 3.12 não encontrado para a compilação." }

$node = Get-ChildItem (Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Packages") -Filter node.exe -Recurse |
    Select-Object -First 1 -ExpandProperty FullName
if (-not $node) { throw "Node.js não encontrado para a compilação." }
$nodeDir = Split-Path $node
$env:Path = "$nodeDir;$env:Path"

& npm.cmd install
if ($LASTEXITCODE -ne 0) { throw "Falha ao instalar as dependências da interface." }
& npx.cmd next build
if ($LASTEXITCODE -ne 0) { throw "Falha ao gerar a interface." }

& $python -m venv .build-venv
& .\.build-venv\Scripts\python.exe -m pip install --disable-pip-version-check -r backend\requirements.txt pyinstaller==6.16.0
if ($LASTEXITCODE -ne 0) { throw "Falha ao preparar o empacotador." }

& .\.build-venv\Scripts\pyinstaller.exe --noconfirm --clean --onefile --windowed `
    --name "FarmaHub Academico" `
    --add-data "out;frontend" `
    --collect-all pdfplumber `
    --collect-all reportlab `
    launcher.py
if ($LASTEXITCODE -ne 0) { throw "Falha ao criar o executável." }

Write-Host "Executável criado em: $project\dist\FarmaHub Academico.exe"
