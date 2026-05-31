# Recria túnel Cloudflare para GymSite Intelligence (Docker + cloudflared)
# Uso: .\scripts\setup-cloudflare-tunnel.ps1
# Pré-requisito: cloudflared login (cert.pem em %USERPROFILE%\.cloudflared\)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$TunnelName = "gymsite-intelligence"
$Hostnames = @(
    "gymsite-api.vectracargo.com.br"
    # Descomente se quiser mover api.vectracargo.com.br para este túnel:
    # "api.vectracargo.com.br"
)

Write-Host "==> Criando túnel '$TunnelName' (ou reutilizando se existir)..."
$existing = cloudflared tunnel list 2>&1 | Select-String $TunnelName
if (-not $existing) {
    cloudflared tunnel create $TunnelName
}

$tunnelLine = (cloudflared tunnel list 2>&1 | Select-String $TunnelName | Select-Object -First 1).Line
$tunnelId = ($tunnelLine -split '\s+')[0]
Write-Host "    Tunnel ID: $tunnelId"

$srcCred = Join-Path $env:USERPROFILE ".cloudflared\$tunnelId.json"
$dstCred = Join-Path $Root "cloudflared\credentials.json"
if (-not (Test-Path $srcCred)) {
    throw "Credenciais não encontradas em $srcCred — rode: cloudflared tunnel create $TunnelName"
}
Copy-Item $srcCred $dstCred -Force
Write-Host "    credentials.json copiado"

$configPath = Join-Path $Root "cloudflared\config.yml"
$config = Get-Content $configPath -Raw
$config = $config -replace '(?m)^tunnel:.*$', "tunnel: $tunnelId"
Set-Content $configPath $config -NoNewline
Write-Host "    config.yml atualizado"

foreach ($host in $Hostnames) {
    Write-Host "==> DNS: $host -> $tunnelId"
    cloudflared tunnel route dns --overwrite-dns $tunnelId $host
}

Write-Host ""
Write-Host "Pronto. Reinicie o stack:"
Write-Host "  cd $Root"
Write-Host "  docker compose restart cloudflared"
Write-Host ""
Write-Host "Teste:"
Write-Host "  curl https://gymsite-api.vectracargo.com.br/health"
