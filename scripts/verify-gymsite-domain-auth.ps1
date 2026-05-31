# Verifica DNS + HTTP + Supabase Auth para gymsite.vectracargo.com.br
# Uso: .\scripts\verify-gymsite-domain-auth.ps1

$ErrorActionPreference = "Continue"
$Domain = "gymsite.vectracargo.com.br"
$PagesDev = "gymsite-3p0.pages.dev"
$SupabaseUrl = "https://epgedaiukjippepujuzc.supabase.co"

Write-Host "==> 1. DNS ($Domain)"
nslookup $Domain 8.8.8.8
Write-Host ""

Write-Host "==> 2. HTTP"
foreach ($url in @("https://$Domain/", "https://$PagesDev/")) {
    try {
        $r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 20
        $title = if ($r.Content -match '<title>([^<]+)</title>') { $Matches[1] } else { "?" }
        Write-Host "    $url -> $($r.StatusCode) | $title"
    } catch {
        Write-Host "    $url -> FALHOU: $($_.Exception.Message)"
    }
}
Write-Host ""

Write-Host "==> 3. Supabase Auth (anon key do frontend/.env)"
$Root = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $Root "frontend\.env"
$anonKey = $null
Get-Content $envFile | ForEach-Object {
    if ($_ -match '^VITE_SUPABASE_ANON_KEY=(.+)$') {
        $anonKey = $Matches[1].Trim('"').Trim("'")
    }
}
if (-not $anonKey) {
    Write-Host "    VITE_SUPABASE_ANON_KEY não encontrada em $envFile"
} else {
    $headers = @{
        apikey = $anonKey
        "Content-Type" = "application/json"
    }
    try {
        $body = '{"email":"test@invalid.local","password":"wrong"}'
        $resp = Invoke-WebRequest -Method POST `
            -Uri "$SupabaseUrl/auth/v1/token?grant_type=password" `
            -Headers $headers -Body $body -UseBasicParsing
        Write-Host "    token endpoint: $($resp.StatusCode) (inesperado — credenciais fake deveriam dar 400)"
    } catch {
        $code = $_.Exception.Response.StatusCode.value__
        if ($code -eq 400) {
            Write-Host "    token endpoint: 400 Invalid login — anon key OK"
        } elseif ($code -eq 401) {
            Write-Host "    token endpoint: 401 — ANON KEY INVÁLIDA ou projeto errado"
            Write-Host "    Corrija VITE_SUPABASE_ANON_KEY (role=anon) no build Cloudflare Pages"
        } else {
            Write-Host "    token endpoint: $code — $($_.Exception.Message)"
        }
    }
}
Write-Host ""

Write-Host "==> 4. Supabase Dashboard (auth no domínio)"
Write-Host "    Authentication -> URL Configuration:"
Write-Host "      Site URL: https://$Domain"
Write-Host "      Redirect URLs (+):"
Write-Host "        https://$Domain/**"
Write-Host "        https://$PagesDev/**"
Write-Host "        http://localhost:5173/**"
Write-Host ""
Write-Host "    Cloudflare Pages -> gymsite-3p0 -> Settings -> Environment variables:"
Write-Host "      VITE_SUPABASE_URL=$SupabaseUrl"
Write-Host "      VITE_SUPABASE_ANON_KEY=<anon legacy key>"
Write-Host "      VITE_API_BASE=https://gymsite-api.vectracargo.com.br"
