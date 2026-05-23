param(
    [string]$Message = ""
)

$ErrorActionPreference = "Stop"

$RepoPath = "C:\Users\Vincere\Documents\Sunny\Astrology GPT\Astro_Code_base"

cd $RepoPath

Write-Host "Checking Git repository..." -ForegroundColor Cyan

git rev-parse --is-inside-work-tree | Out-Null

$branch = (git branch --show-current).Trim()

Write-Host "Current branch: $branch" -ForegroundColor Yellow

if ($branch -ne "main") {
    Write-Host "WARNING: You are not on main branch. You are on: $branch" -ForegroundColor Red
    $continue = Read-Host "Do you still want to continue? Type Y to continue"
    if ($continue -ne "Y") {
        Write-Host "Commit cancelled."
        exit
    }
}

Write-Host "`nCurrent changes:" -ForegroundColor Cyan
git status --short

$changes = git status --porcelain

if (-not $changes) {
    Write-Host "`nNo changes found. Nothing to commit." -ForegroundColor Green
    exit
}

if ([string]::IsNullOrWhiteSpace($Message)) {
    $Message = Read-Host "`nEnter commit message"
}

if ([string]::IsNullOrWhiteSpace($Message)) {
    $Message = "Updated code"
}

Write-Host "`nAdding files..." -ForegroundColor Cyan
git add -A

Write-Host "Committing..." -ForegroundColor Cyan
git commit -m "$Message"

Write-Host "`nPushing to GitHub..." -ForegroundColor Cyan

$upstream = git rev-parse --abbrev-ref --symbolic-full-name "@{u}" 2>$null

if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($upstream)) {
    git push -u origin $branch
} else {
    git push
}

Write-Host "`nDone. Final status:" -ForegroundColor Green
git status