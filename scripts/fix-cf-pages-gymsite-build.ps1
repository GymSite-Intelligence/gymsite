# Fix build_config for Cloudflare Pages project "gymsite" (Git -> getgymsite.com.br).
# Common bug: build_command "npm build" (invalid) + root_dir "/" (runs pip on monorepo root).
#
# Usage:
#   .\scripts\fix-cf-pages-gymsite-build.ps1
#   .\scripts\fix-cf-pages-gymsite-build.ps1 -Redeploy
#
# Token: $env:CLOUDFLARE_API_TOKEN or wrangler oauth (~/.wrangler/config/default.toml).

param(
    [switch]$Redeploy
)

$ErrorActionPreference = "Stop"

$AccountId = "361e9e1383bfa8e95e1db54e6c2a3bba"
$ProjectName = "gymsite"
$DashboardUrl = "https://dash.cloudflare.com/$AccountId/pages/view/$ProjectName"

$WantRootDir = "frontend"
$WantDestinationDir = "dist"
# Vite precisa de VITE_* no build. CF Pages nao injeta deployment_configs.env_vars no
# subprocess quando root_dir=frontend — gravamos .env.production antes do build.
# Valores publicos (publishable key); mesmo contrato de cloudbuild.frontend.yaml.
$WantBuildCommand = @'
printf '%s\n' 'VITE_USE_MOCKS=false' 'VITE_SUPABASE_URL=https://epgedaiukjippepujuzc.supabase.co' 'VITE_SUPABASE_ANON_KEY=sb_publishable_fj4Ioi3YX8gI-h3lrcb45w_FZa9UzhD' 'VITE_API_BASE=https://gymsite-api.vectracargo.com.br' > .env.production && npm run build
'@

$PublishableKey = "sb_publishable_fj4Ioi3YX8gI-h3lrcb45w_FZa9UzhD"
$SupabaseUrl = "https://epgedaiukjippepujuzc.supabase.co"
$ApiBase = "https://gymsite-api.vectracargo.com.br"

function Get-CfToken {
    if ($env:CLOUDFLARE_API_TOKEN) {
        return $env:CLOUDFLARE_API_TOKEN
    }
    $wranglerCfg = Join-Path $env:USERPROFILE ".wrangler\config\default.toml"
    if (-not (Test-Path $wranglerCfg)) {
        return $null
    }
    $line = Select-String -Path $wranglerCfg -Pattern '^oauth_token = ' | Select-Object -First 1
    if (-not $line) {
        return $null
    }
    return $line.Line -replace '^oauth_token = "|"$'
}

$token = Get-CfToken
if (-not $token) {
    Write-Host "Sem token Cloudflare."
    Write-Host "  `$env:CLOUDFLARE_API_TOKEN = '...'  OU  npx wrangler login"
    Write-Host "  Dashboard: $DashboardUrl -> Settings -> Builds"
    Write-Host "    Build command: $WantBuildCommand"
    Write-Host "    Root directory: $WantRootDir"
    Write-Host "    Build output: $WantDestinationDir"
    exit 1
}

$headers = @{
    Authorization = "Bearer $token"
    "Content-Type" = "application/json"
}

$baseUri = "https://api.cloudflare.com/client/v4/accounts/$AccountId/pages/projects/$ProjectName"

Write-Host "==> Pages: $ProjectName"
$proj = Invoke-RestMethod -Method GET -Uri $baseUri -Headers $headers
if (-not $proj.success) {
    throw ($proj.errors | ConvertTo-Json -Compress)
}

$bc = $proj.result.build_config
Write-Host ('    Atual: build_command={0} root_dir={1} destination_dir={2}' -f $bc.build_command, $bc.root_dir, $bc.destination_dir)

$drifted = ($bc.build_command -ne $WantBuildCommand) -or
           ($bc.root_dir -ne $WantRootDir) -or
           ($bc.destination_dir -ne $WantDestinationDir)

if (-not $drifted) {
    Write-Host "    OK - build_config ja correta."
} else {
    $body = @{
        build_config = @{
            build_command = $WantBuildCommand
            root_dir = $WantRootDir
            destination_dir = $WantDestinationDir
        }
    } | ConvertTo-Json -Depth 4

    $patched = Invoke-RestMethod -Method PATCH -Uri $baseUri -Headers $headers -Body $body
    if (-not $patched.success) {
        throw ($patched.errors | ConvertTo-Json -Compress)
    }
    $nbc = $patched.result.build_config
    Write-Host ('    Fix: build_command={0} root_dir={1} destination_dir={2}' -f $nbc.build_command, $nbc.root_dir, $nbc.destination_dir)
}

Write-Host "==> Env vars (preview + production)"
$wantEnv = @{
    VITE_API_BASE = @{ type = "plain_text"; value = $ApiBase }
    VITE_SUPABASE_ANON_KEY = @{ type = "plain_text"; value = $PublishableKey }
    VITE_SUPABASE_URL = @{ type = "plain_text"; value = $SupabaseUrl }
    VITE_USE_MOCKS = @{ type = "plain_text"; value = "false" }
}
$envBody = @{
    deployment_configs = @{
        preview = @{ env_vars = $wantEnv }
        production = @{ env_vars = $wantEnv }
    }
} | ConvertTo-Json -Depth 6
$envPatched = Invoke-RestMethod -Method PATCH -Uri $baseUri -Headers $headers -Body $envBody
if (-not $envPatched.success) {
    throw ($envPatched.errors | ConvertTo-Json -Compress)
}
$previewKey = $envPatched.result.deployment_configs.preview.env_vars.VITE_SUPABASE_ANON_KEY.value
Write-Host ('    preview key={0} legacy={1}' -f $previewKey.Substring(0, 24), $previewKey.StartsWith('eyJ'))

if ($Redeploy) {
    Write-Host "==> Redeploy branch main..."
    $dep = Invoke-RestMethod -Method POST -Uri "$baseUri/deployments" -Headers $headers -Body (@{ branch = "main" } | ConvertTo-Json)
    if (-not $dep.success) {
        throw ($dep.errors | ConvertTo-Json -Compress)
    }
    $id = $dep.result.id
    $previewUrl = $dep.result.url
    Write-Host "    deployment_id=$id"
    Write-Host "    preview=$previewUrl"
}
