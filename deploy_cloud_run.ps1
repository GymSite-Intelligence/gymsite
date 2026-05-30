param (
    [string]$Project = "gen-lang-client-0662901510",
    [string]$Service = "gymsite-api",
    [string]$Region = "us-central1"
)

Write-Host "Preparando deploy do Cloud Run para o serviço: $Service" -ForegroundColor Cyan

# Carrega as variáveis do .env ignorando comentários e linhas vazias
$envContent = Get-Content -Path ".env" | Where-Object { $_ -match "^[A-Za-z0-9_]+=" -and $_ -notmatch "^#" }
$envDict = @{}

foreach ($line in $envContent) {
    $idx = $line.IndexOf("=")
    if ($idx -gt 0) {
        $key = $line.Substring(0, $idx).Trim()
        $value = $line.Substring($idx + 1).Trim()
        # Remove aspas se houver
        if ($value -match '^"(.*)"$' -or $value -match "^'(.*)'$") {
            $value = $Matches[1]
        }
        $envDict[$key] = $value
    }
}

# Definindo origens CORS para o frontend em produção e preview
$envDict["CORS_ORIGINS"] = "https://gymsite.vectracargo.com.br,https://gymsite-3p0.pages.dev"

# Cria arquivo YAML temporário para injetar as variáveis sem conflito de escaping no gcloud
$yamlContent = @()
foreach ($key in $envDict.Keys) {
    $val = $envDict[$key]
    # Encapsula o valor com aspas duplas no yaml para evitar parsing incorreto
    $yamlContent += "${key}: '${val}'"
}

$yamlPath = Join-Path $PWD ".cloudrun_env.yaml"
$yamlContent | Out-File -FilePath $yamlPath -Encoding UTF8

Write-Host "Realizando o build local e deploy no Cloud Run..." -ForegroundColor Yellow

gcloud run deploy $Service `
    --project=$Project `
    --region=$Region `
    --source . `
    --env-vars-file="$yamlPath" `
    --allow-unauthenticated `
    --quiet

if ($LASTEXITCODE -eq 0) {
    Write-Host "`nDeploy concluído com sucesso!" -ForegroundColor Green
    Write-Host "As variáveis de ambiente e regras de CORS foram injetadas corretamente." -ForegroundColor Green
} else {
    Write-Host "`nFalha no deploy. Veja os logs acima." -ForegroundColor Red
}

# Limpa o arquivo temporário
Remove-Item $yamlPath -ErrorAction SilentlyContinue
