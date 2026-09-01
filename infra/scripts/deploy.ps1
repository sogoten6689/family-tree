# deploy.ps1 — Deploy family-saga-io to Vercel
# Usage: .\deploy.ps1           (preview deployment)
#        .\deploy.ps1 --prod    (production deployment)

param(
  [switch]$prod
)

$ProjectDir = Join-Path $PSScriptRoot "family-saga-io"

# 1. Check Vercel CLI
if (-not (Get-Command vercel -ErrorAction SilentlyContinue)) {
  Write-Host "Vercel CLI not found. Installing..." -ForegroundColor Yellow
  npm install -g vercel
  if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to install Vercel CLI."
    exit 1
  }
}

# 2. Build
Write-Host "`n[1/2] Building project..." -ForegroundColor Cyan
Set-Location $ProjectDir
npm run build
if ($LASTEXITCODE -ne 0) {
  Write-Error "Build failed. Aborting deploy."
  exit 1
}

# 3. Deploy
Write-Host "`n[2/2] Deploying to Vercel..." -ForegroundColor Cyan
if ($prod) {
  Write-Host "Mode: PRODUCTION" -ForegroundColor Green
  vercel --prod
} else {
  Write-Host "Mode: PREVIEW" -ForegroundColor Yellow
  vercel
}

if ($LASTEXITCODE -ne 0) {
  Write-Error "Deployment failed."
  exit 1
}

Write-Host "`nDeploy completed successfully!" -ForegroundColor Green
