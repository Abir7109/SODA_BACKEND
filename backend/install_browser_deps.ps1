# SODA Browser Automation - Dependency Installer
# Run this script to install Playwright + Chromium for browser automation

Write-Host "SODA Browser Automation - Installing dependencies..." -ForegroundColor Cyan

# 1. Install Playwright Python package
Write-Host "[1/3] Installing Playwright Python package..." -ForegroundColor Yellow
pip install playwright
if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to install playwright. Try: pip install playwright" -ForegroundColor Red
    exit 1
}
Write-Host "  OK" -ForegroundColor Green

# 2. Install Chromium browser for Playwright
Write-Host "[2/3] Installing Chromium browser (headless)..." -ForegroundColor Yellow
python -m playwright install chromium
if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to install Chromium. Try: python -m playwright install chromium" -ForegroundColor Red
    exit 1
}
Write-Host "  OK" -ForegroundColor Green

# 3. Verify installation
Write-Host "[3/3] Verifying installation..." -ForegroundColor Yellow
python -c "from playwright.sync_api import sync_playwright; p=sync_playwright().start(); b=p.chromium.launch(headless=True); print('Playwright OK - Chromium', b.version); b.close(); p.stop()"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Verification failed. Check Playwright installation." -ForegroundColor Red
    exit 1
}
Write-Host "  OK" -ForegroundColor Green

Write-Host "`nAll dependencies installed successfully!" -ForegroundColor Green
Write-Host "You can now use browser automation features in SODA." -ForegroundColor Cyan
