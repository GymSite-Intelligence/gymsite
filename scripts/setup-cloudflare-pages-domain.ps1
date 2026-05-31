# Vincula gymsite.vectracargo.com.br ao projeto Cloudflare Pages gymsite-3p0 (GYM-03)
#
# Uso:
#   $env:CLOUDFLARE_API_TOKEN = "..."   # Account -> Cloudflare Pages:Edit
#   .\scripts\setup-cloudflare-pages-domain.ps1
#
# Ou manualmente no dashboard:
#   https://dash.cloudflare.com/361e9e1383bfa8e95e1db54e6c2a3bba/pages/view/gymsite-3p0
#   -> Custom domains -> Add -> gymsite.vectracargo.com.br
#
# Secrets GitHub (para .github/workflows/pages.yml):
#   CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID
#   VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY

$ErrorActionPreference = "Stop"

$ProjectName = "gymsite-3p0"
$CustomDomain = "gymsite.vectracargo.com.br"
$AccountId = "361e9e1383bfa8e95e1db54e6c2a3bba"
$DashboardUrl = "https://dash.cloudflare.com/$AccountId/pages/view/$ProjectName"

Write-Host "==> Cloudflare Pages: $ProjectName"
Write-Host "    Custom domain: $CustomDomain"
Write-Host ""

$token = $env:CLOUDFLARE_API_TOKEN
if (-not $token) {
    Write-Host "CLOUDFLARE_API_TOKEN não definido."
    Write-Host ""
    Write-Host "Opção A — Dashboard (recomendado):"
    Write-Host "  1. Abra: $DashboardUrl"
    Write-Host "  2. Custom domains -> Add -> $CustomDomain"
    Write-Host ""
    Write-Host "Opção B — API via script:"
    Write-Host '  $env:CLOUDFLARE_API_TOKEN = "seu-token"'
    Write-Host "  .\scripts\setup-cloudflare-pages-domain.ps1"
    exit 0
}

$headers = @{
    Authorization = "Bearer $token"
    "Content-Type" = "application/json"
}

Write-Host "==> Registrando custom domain via API..."
$uri = "https://api.cloudflare.com/client/v4/accounts/$AccountId/pages/projects/$ProjectName/domains"
$body = @{ name = $CustomDomain } | ConvertTo-Json

try {
    $result = Invoke-RestMethod -Method POST -Uri $uri -Headers $headers -Body $body
    if (-not $result.success) {
        throw ($result.errors | ConvertTo-Json -Compress)
    }
    Write-Host "    OK: $($result.result.name) -> status $($result.result.status)"
} catch {
    $msg = $_.Exception.Message
    if ($msg -match "already exists|duplicate") {
        Write-Host "    Domínio já registrado no projeto."
    } else {
        Write-Host "    Erro: $msg"
        Write-Host ""
        Write-Host "Fallback manual: $DashboardUrl"
        exit 1
    }
}

Write-Host ""
Write-Host "==> Aguardando propagação DNS (15s)..."
Start-Sleep -Seconds 15

Write-Host "==> Teste DNS:"
nslookup $CustomDomain 8.8.8.8

Write-Host ""
Write-Host "==> Teste HTTP:"
try {
    $resp = Invoke-WebRequest -Uri "https://$CustomDomain/" -UseBasicParsing -TimeoutSec 20
    Write-Host "    Status: $($resp.StatusCode)"
    if ($resp.Content -match '<title>([^<]+)</title>') {
        Write-Host "    Title: $($Matches[1])"
    }
} catch {
    Write-Host "    Ainda propagando ou SSL pendente: $($_.Exception.Message)"
    Write-Host "    Preview: https://$ProjectName.pages.dev"
}

Write-Host ""
Write-Host "GitHub secrets (Settings -> Secrets and variables -> Actions):"
Write-Host "  CLOUDFLARE_API_TOKEN"
Write-Host "  CLOUDFLARE_ACCOUNT_ID = $AccountId"
Write-Host "  VITE_SUPABASE_URL"
Write-Host "  VITE_SUPABASE_ANON_KEY"
