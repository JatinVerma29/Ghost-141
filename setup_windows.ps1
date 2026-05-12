# Ghost-141 Windows Setup Script
# Run this in PowerShell from the ghost141 folder:
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
#   .\setup_windows.ps1

Write-Host ""
Write-Host "  GHOST-141 Windows Setup" -ForegroundColor Green
Write-Host "  ========================" -ForegroundColor Green
Write-Host ""

# Step 1 — Install all packages EXCEPT PyAudio
Write-Host "[1/3] Installing core packages..." -ForegroundColor Cyan
pip install anthropic pyttsx3 pyautogui psutil pyperclip requests beautifulsoup4 lxml python-dotenv SpeechRecognition

# Step 2 — Install PyAudio via pre-built wheel (works on all Python versions)
Write-Host ""
Write-Host "[2/3] Installing PyAudio (pre-built wheel)..." -ForegroundColor Cyan
pip install PyAudio --only-binary=:all:
if ($LASTEXITCODE -ne 0) {
    Write-Host "  Pre-built wheel not found. Trying unofficial binaries..." -ForegroundColor Yellow
    pip install pipwin
    # Add Scripts to PATH temporarily
    $scriptsPath = (python -c "import sys; import os; print(os.path.join(os.path.dirname(sys.executable), 'Scripts'))")
    $env:PATH = "$scriptsPath;$env:PATH"
    pipwin install pyaudio
}
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "  PyAudio install failed. Voice input will be disabled." -ForegroundColor Yellow
    Write-Host "  Ghost-141 will still work in TEXT mode (type commands)." -ForegroundColor Yellow
}

# Step 3 — Set API key
Write-Host ""
Write-Host "[3/3] API Key Setup" -ForegroundColor Cyan
Write-Host ""
$key = Read-Host "  Enter your Anthropic API key (sk-ant-...) or press Enter to skip"
if ($key -ne "") {
    $envDir = "$env:USERPROFILE\.ghost141"
    New-Item -ItemType Directory -Force -Path $envDir | Out-Null
    "ANTHROPIC_API_KEY=$key" | Set-Content "$envDir\.env"
    Write-Host "  API key saved to $envDir\.env" -ForegroundColor Green
} else {
    Write-Host "  Skipped. Set it later in $env:USERPROFILE\.ghost141\.env" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "  Setup complete! Run Ghost-141 with:" -ForegroundColor Green
Write-Host "  python main.py" -ForegroundColor White
Write-Host ""
