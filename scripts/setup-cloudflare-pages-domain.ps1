# Vincula gymsite.vectracargo.com.br ao Cloudflare Pages gymsite-3p0 (GYM-03)
#
# Uso:
#   $env:CLOUDFLARE_API_TOKEN = "..."   # Zone.DNS Edit + Account Cloudflare Pages:Edit
#   .\scripts\setup-cloudflare-pages-domain.ps1
#
# O endpoint Pages /domains retorna 404 em alguns tokens — fallback: CNAME DNS na zona.

$ErrorActionPreference = "Stop"

$ProjectName = "gymsite-3p0"
$CustomDomain = "gymsite.vectracargo.com.br"
$PagesTarget = "$ProjectName.pages.dev"
$ZoneName = "vectracargo.com.br"
$RecordName = "gymsite"
$AccountId = "361e9e1383bfa8e95e1db54e6c2a3bba"
$DashboardUrl = "https://dash.cloudflare.com/$AccountId/pages/view/$ProjectName"

Write-Host "==> Cloudflare Pages: $ProjectName"
Write-Host "    Custom domain: $CustomDomain"
Write-Host ""

$token = $env:CLOUDFLARE_API_TOKEN
if (-not $token) {
    Write-Host "CLOUDFLARE_API_TOKEN não definido."
    Write-Host ""
    Write-Host "Opção A — Dashboard:"
    Write-Host "  1. $DashboardUrl -> Custom domains -> Add -> $CustomDomain"
    Write-Host "  2. Ou DNS: CNAME gymsite -> $PagesTarget (proxied)"
    Write-Host ""
    Write-Host "Opção B — Script:"
    Write-Host '  $env:CLOUDFLARE_API_TOKEN = "seu-token"'
    Write-Host "  .\scripts\setup-cloudflare-pages-domain.ps1"
    exit 0
}

$headers = @{
    Authorization = "Bearer $token"
    "Content-Type" = "application/json"
}

function Ensure-DnsCname {
    Write-Host "==> DNS CNAME: $RecordName.$ZoneName -> $PagesTarget"
    $zoneResp = Invoke-RestMethod -Method GET `
        -Uri "https://api.cloudflare.com/client/v4/zones?name=$ZoneName" `
        -Headers $headers
    if (-not $zoneResp.success -or $zoneResp.result.Count -eq 0) {
        throw "Zona $ZoneName não encontrada na conta Cloudflare"
    }
    $zoneId = $zoneResp.result[0].id

    $existing = Invoke-RestMethod -Method GET `
        -Uri "https://api.cloudflare.com/client/v4/zones/$zoneId/dns_records?type=CNAME&name=$RecordName.$ZoneName" `
        -Headers $headers

    $body = @{
        type = "CNAME"
        name = $RecordName
        content = $PagesTarget
        proxied = $true
        ttl = 1
    } | ConvertTo-Json

    if ($existing.result.Count -gt 0) {
        $recId = $existing.result[0].id
        $upd = Invoke-RestMethod -Method PUT `
            -Uri "https://api.cloudflare.com/client/v4/zones/$zoneId/dns_records/$recId" `
            -Headers $headers -Body $body
        if (-not $upd.success) { throw ($upd.errors | ConvertTo-Json -Compress) }
        Write-Host "    CNAME atualizado (id=$recId)"
    } else {
        $crt = Invoke-RestMethod -Method POST `
            -Uri "https://api.cloudflare.com/client/v4/zones/$zoneId/dns_records" `
            -Headers $headers -Body $body
        if (-not $crt.success) { throw ($crt.errors | ConvertTo-Json -Compress) }
        Write-Host "    CNAME criado (id=$($crt.result.id))"
    }
}

Write-Host "==> Tentativa 1: Pages custom domain API..."
$uri = "https://api.cloudflare.com/client/v4/accounts/$AccountId/pages/projects/$ProjectName/domains"
try {
    $result = Invoke-RestMethod -Method POST -Uri $uri -Headers $headers -Body (@{ name = $CustomDomain } | ConvertTo-Json)
    if ($result.success) {
        Write-Host "    OK: $($result.result.name) status=$($result.result.status)"
    }
} catch {
    Write-Host "    Pages API falhou ($($_.Exception.Message)) — usando DNS CNAME..."
    Ensure-DnsCname
}

Write-Host ""
Write-Host "==> Aguardando propagação (20s)..."
Start-Sleep -Seconds 20

Write-Host "==> DNS:"
nslookup $CustomDomain 8.8.8.8

Write-Host ""
Write-Host "==> Auth check:"
& (Join-Path $PSScriptRoot "verify-gymsite-domain-auth.ps1")
