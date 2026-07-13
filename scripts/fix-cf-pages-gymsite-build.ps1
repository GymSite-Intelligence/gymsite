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

$WantBuildCommand = "npm run build"
$WantRootDir = "frontend"
$WantDestinationDir = "dist"

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
    Write-Host "    OK - config ja correta."
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
