<#
.SYNOPSIS
    Analisa todos os arquivos Python do projeto usando Qwen Code e gera relatório de erros.

.DESCRIPTION
    Executa o Qwen Code para analisar todos os arquivos .py do projeto,
    identificar erros potenciais e gerar um relatório em errors.md.
    Adaptado para Windows/PowerShell.

.PARAMETER Path
    Caminho para o diretório raiz do projeto (default: diretório atual).

.PARAMETER OutputFile
    Nome do arquivo de saída (default: errors.md).

.PARAMETER IncludeTests
    Incluir arquivos de teste na análise (default: false).

.EXAMPLE
    .\qwen-analyze.ps1
    .\qwen-analyze.ps1 -Path "C:\Users\marce\gymsite_intelligence"
    .\qwen-analyze.ps1 -IncludeTests -OutputFile "report.md"
#>

param(
    [string]$Path = ".",
    [string]$OutputFile = "errors.md",
    [switch]$IncludeTests
)

# Resolve caminho absoluto
$ProjectPath = (Resolve-Path $Path).Path

# Monta lista de arquivos Python
$PyFiles = Get-ChildItem -Path $ProjectPath -Filter "*.py" -Recurse -File |
    Where-Object {
        # Excluir .venv, __pycache__, node_modules
        $_.FullName -notmatch '[\\/]\.venv[\\/]' -and
        $_.FullName -notmatch '[\\]__pycache__[\\]' -and
        $_.FullName -notmatch '[\\]node_modules[\\]'
    } |
    Where-Object {
        if (-not $IncludeTests) {
            # Excluir arquivos de teste
            $_.Name -notmatch '^test_'
        } else { $true }
    }

if ($PyFiles.Count -eq 0) {
    Write-Host "[ERRO] Nenhum arquivo Python encontrado em $ProjectPath" -ForegroundColor Red
    exit 1
}

Write-Host "[INFO] Analisando $($PyFiles.Count) arquivos Python..." -ForegroundColor Cyan

# Monta o prompt para o Qwen
$Prompt = @"
Analyze all Python files in the following list for potential errors and output a summary report to $OutputFile.

Files to analyze:
$($PyFiles | ForEach-Object { $_.FullName })

Check for:
1. Syntax errors and typos
2. Unused imports
3. Undefined variables
4. Type mismatches
5. Potential runtime errors (NoneType access, missing keys, etc.)
6. Exception handling gaps

Output a structured markdown report with:
- File name
- Line number (if applicable)
- Error description
- Severity (error/warning/info)

Write the report to $OutputFile.
"@

# Executa o Qwen Code
try {
    Write-Host "[INFO] Executando análise com Qwen Code..." -ForegroundColor Cyan

    $Result = qwen -p $Prompt --output-format json 2>&1

    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] Análise concluída!" -ForegroundColor Green

        if (Test-Path (Join-Path $ProjectPath $OutputFile)) {
            Write-Host "[OK] Relatório salvo em: $(Join-Path $ProjectPath $OutputFile)" -ForegroundColor Green
        } else {
            Write-Host "[AVISO] Arquivo de saída não encontrado. Verifique se o Qwen gerou o relatório." -ForegroundColor Yellow
        }
    } else {
        Write-Host "[ERRO] Qwen Code retornou erro (exit code: $LASTEXITCODE)" -ForegroundColor Red
        Write-Host $Result -ForegroundColor Red
        exit $LASTEXITCODE
    }
} catch {
    Write-Host "[ERRO] Falha ao executar Qwen Code: $_" -ForegroundColor Red
    exit 1
}
