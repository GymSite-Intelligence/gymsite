param (
    [string]$Project = "gen-lang-client-0106729343",
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
        # Remove comentários no final da linha (ex: 3600 # 1 hora)
        $value = ($value -split '#')[0].Trim()
        # Remove aspas se houver
        if ($value -match '^"(.*)"$' -or $value -match "^'(.*)'$") {
            $value = $Matches[1]
        }
        $envDict[$key] = $value
    }
}

# Definindo origens CORS para o frontend em produção e preview
$envDict["CORS_ORIGINS"] = "https://gymsite.vectracargo.com.br,https://gymsite-3p0.pages.dev,https://getgymsite.com.br,https://www.getgymsite.com.br,https://gymsite.com.br,https://www.gymsite.com.br"

# Variáveis locais/dev que não existem no container Cloud Run (ADC via metadata SA).
$cloudRunStrip = @(
    "GOOGLE_APPLICATION_CREDENTIALS",
    "VITE_API_BASE",
    "VITE_SUPABASE_URL",
    "VITE_SUPABASE_ANON_KEY",
    "VITE_USE_MOCKS",
    "VITE_DEV_AS_ADMIN",
    "CNO_DATA_DIR_HOST",
)
foreach ($key in $cloudRunStrip) {
    $envDict.Remove($key) | Out-Null
}

# SUPABASE_URL precisa estar no serviço (não é secret bindado hoje).
if (-not $envDict.ContainsKey("SUPABASE_URL")) {
    $supabaseUrl = ($envContent | Where-Object { $_ -match "^SUPABASE_URL=" } | Select-Object -First 1)
    if ($supabaseUrl) {
        $idx = $supabaseUrl.IndexOf("=")
        if ($idx -gt 0) {
            $envDict["SUPABASE_URL"] = $supabaseUrl.Substring($idx + 1).Trim()
        }
    }
}

# Lista de variáveis que são gerenciadas como Secrets no Google Cloud Run.
$secretVariables = @(
    "TURNSTILE_SECRET",
    "SUPABASE_SERVICE_ROLE_KEY",
    "GOOGLE_MAPS_API_KEY",
    "GEMINI_API_KEY",
    "SEARCHAPI_KEY",
    "OUTSCRAPER_API_KEY",
    "OPENCLAW_TOKEN",
    "LANGCACHE_API_KEY",
    "CLAW_WEBHOOK_SECRET",
    "REDIS_URL",
    "LANGCACHE_SERVER_URL",
    "CLAW_WEBHOOK_URL"
)

Write-Host "Removendo variáveis de Secret do deploy para preservar a configuração do Cloud Run..." -ForegroundColor Gray
foreach ($secret in $secretVariables) {
    $envDict.Remove($secret) | Out-Null
}

# Cria arquivo YAML temporário
$yamlContent = @()
foreach ($key in $envDict.Keys) {
    $val = $envDict[$key]
    $yamlContent += "${key}: '${val}'"
}

$yamlPath = Join-Path $PWD ".cloudrun_env.yaml"
$yamlContent | Out-File -FilePath $yamlPath -Encoding UTF8

Write-Host "Realizando o build local e deploy no Cloud Run..." -ForegroundColor Yellow

# AQUI ESTÁ A CORREÇÃO: trocado --startup-cpu-boost por --cpu-boost
gcloud run deploy $Service `
    --project=$Project `
    --region=$Region `
    --source . `
    --env-vars-file="$yamlPath" `
    --cpu=1 `
    --memory=2Gi `
    --cpu-boost `
    --allow-unauthenticated `
    --quiet

if ($LASTEXITCODE -eq 0) {
    Write-Host "`nDeploy concluído com sucesso!" -ForegroundColor Green
}
else {
    Write-Host "`nFalha no deploy. Veja os logs acima." -ForegroundColor Red
}

# Limpa o arquivo temporário
Remove-Item $yamlPath -ErrorAction SilentlyContinue
