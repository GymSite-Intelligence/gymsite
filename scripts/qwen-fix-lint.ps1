<#
.SYNOPSIS
    Executa flake8 nos arquivos Python do projeto e corrige issues auto-corrigíveis.

.DESCRIPTION
    Roda flake8 em todos os arquivos .py do projeto, aplica correções automáticas
    com autopep8/isort quando possível, e gera um diff das mudanças.
    Adaptado para Windows/PowerShell — sem dependência de findstr.

.PARAMETER Path
    Caminho para o diretório raiz do projeto (default: diretório atual).

.PARAMETER DiffFile
    Nome do arquivo de saída para o diff (default: lint-fix.diff).

.PARAMETER IncludeTests
    Incluir arquivos de teste na correção (default: false).

.EXAMPLE
    .\qwen-fix-lint.ps1
    .\qwen-fix-lint.ps1 -Path "C:\Users\marce\gymsite_intelligence"
    .\qwen-fix-lint.ps1 -IncludeTests -DiffFile "changes.diff"
#>

param(
    [string]$Path = ".",
    [string]$DiffFile = "lint-fix.diff",
    [switch]$IncludeTests
)

# Resolve caminho absoluto
$ProjectPath = (Resolve-Path $Path).Path

# Verifica dependências
$MissingDeps = @()

if (-not (Get-Command flake8 -ErrorAction SilentlyContinue)) {
    $MissingDeps += "flake8"
}
if (-not (Get-Command autopep8 -ErrorAction SilentlyContinue)) {
    $MissingDeps += "autopep8"
}
if (-not (Get-Command isort -ErrorAction SilentlyContinue)) {
    $MissingDeps += "isort"
}

if ($MissingDeps.Count -gt 0) {
    Write-Host "[ERRO] Dependências ausentes: $($MissingDeps -join ', ')" -ForegroundColor Red
    Write-Host "Instale com: pip install $($MissingDeps -join ' ')" -ForegroundColor Yellow
    exit 1
}

# Monta lista de arquivos Python
$PyFiles = Get-ChildItem -Path $ProjectPath -Filter "*.py" -Recurse -File |
    Where-Object {
        $_.FullName -notmatch '[\\/]\.venv[\\/]' -and
        $_.FullName -notmatch '[\\]__pycache__[\\]' -and
        $_.FullName -notmatch '[\\]node_modules[\\]'
    } |
    Where-Object {
        if (-not $IncludeTests) {
            $_.Name -notmatch '^test_'
        } else { $true }
    }

if ($PyFiles.Count -eq 0) {
    Write-Host "[ERRO] Nenhum arquivo Python encontrado em $ProjectPath" -ForegroundColor Red
    exit 1
}

Write-Host "[INFO] Processando $($PyFiles.Count) arquivos Python..." -ForegroundColor Cyan

# Salva snapshot pré-correção para gerar diff
$PreDir = Join-Path $env:TEMP "pre-lint-$((Get-Date).ToString('yyyyMMddHHmmss'))"
New-Item -ItemType Directory -Path $PreDir -Force | Out-Null

foreach ($File in $PyFiles) {
    $RelPath = $File.FullName.Replace($ProjectPath, '').TrimStart('\')
    $DestDir = Join-Path $PreDir (Split-Path $RelPath -Parent)
    if ($DestDir -and -not (Test-Path $DestDir)) {
        New-Item -ItemType Directory -Path $DestDir -Force | Out-Null
    }
    Copy-Item $File.FullName -Destination (Join-Path $PreDir $RelPath) -Force
}

# Executa correções
Write-Host "[INFO] Executando isort (organização de imports)..." -ForegroundColor Cyan
foreach ($File in $PyFiles) {
    isort $File.FullName 2>&1 | Out-Null
}

Write-Host "[INFO] Executando autopep8 (formatação)..." -ForegroundColor Cyan
foreach ($File in $PyFiles) {
    autopep8 --in-place --aggressive --aggressive $File.FullName 2>&1 | Out-Null
}

# Gera diff
Write-Host "[INFO] Gerando diff..." -ForegroundColor Cyan

$DiffOutput = @()
foreach ($File in $PyFiles) {
    $RelPath = $File.FullName.Replace($ProjectPath, '').TrimStart('\')
    $PreFile = Join-Path $PreDir $RelPath

    if (Test-Path $PreFile) {
        $Diff = Compare-Object (Get-Content $PreFile -Encoding UTF8) (Get-Content $File.FullName -Encoding UTF8)
        if ($Diff) {
            $DiffOutput += "=== $RelPath ==="
            $DiffOutput += $Diff | ForEach-Object {
                $Side = if ($_.SideIndicator -eq '<=') { '-' } else { '+' }
                "$Side $($_.InputObject)"
            }
            $DiffOutput += ""
        }
    }
}

if ($DiffOutput.Count -gt 0) {
    $DiffOutput | Out-File -FilePath (Join-Path $ProjectPath $DiffFile) -Encoding UTF8
    Write-Host "[OK] Diff salvo em: $(Join-Path $ProjectPath $DiffFile)" -ForegroundColor Green
} else {
    Write-Host "[OK] Nenhuma correção necessária!" -ForegroundColor Green
}

# Roda flake8 pós-correção para relatório
Write-Host "[INFO] Executando flake8 pós-correção..." -ForegroundColor Cyan
$FlakeResult = flake8 --count --statistics $ProjectPath 2>&1

if ($LASTEXITCODE -gt 0) {
    Write-Host "[AVISO] Flake8 encontrou issues restantes:" -ForegroundColor Yellow
    Write-Host $FlakeResult -ForegroundColor Yellow
} else {
    Write-Host "[OK] Flake8 limpo!" -ForegroundColor Green
}

# Limpa temp
Remove-Item $PreDir -Recurse -Force -ErrorAction SilentlyContinue
