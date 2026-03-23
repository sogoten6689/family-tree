# commit.ps1
# Usage: .\build-and-commit.ps1 "commit message"
#        .\build-and-commit.ps1          (uses auto message with timestamp)

param(
  [string]$Message = ""
)

$Root = $PSScriptRoot
Set-Location $Root

# 1. Stage all changes
Write-Host "[1/2] Staging changes..." -ForegroundColor Cyan
git add -A
$staged = git diff --cached --name-only
if (-not $staged) {
  Write-Host "Nothing to commit." -ForegroundColor Yellow
  exit 0
}

# 2. Commit
if (-not $Message) {
  $Message = "chore: update $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
}
Write-Host "[2/2] Committing: $Message" -ForegroundColor Cyan
git commit -m $Message
if ($LASTEXITCODE -ne 0) {
  Write-Error "Commit failed."
  exit 1
}

Write-Host "`nDone! Committed successfully." -ForegroundColor Green
git log --oneline -1
