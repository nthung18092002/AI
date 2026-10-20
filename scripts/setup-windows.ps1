param([ValidateSet('basic','images','video','all','reference')][string]$Profile = 'reference')
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
function Check-Exit([string]$Step) {
    if ($LASTEXITCODE -ne 0) { throw "$Step failed (exit $LASTEXITCODE). See the output above; fix the cause and rerun setup." }
}
function Install-Winget([string]$Package) {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) { throw "Install $Package using its official website, then run setup again. winget is unavailable." }
    & winget install --exact --id $Package --accept-package-agreements --accept-source-agreements --disable-interactivity
    Check-Exit "Installing $Package"
}
$Python = $null
if (Get-Command py -ErrorAction SilentlyContinue) {
    $Python = & py -3.12 -c "import sys; print(sys.executable)" 2>$null
}
if (-not $Python) {
    $Candidate = Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe'
    if (-not (Test-Path $Candidate)) { Install-Winget 'Python.Python.3.12' }
    if (Test-Path $Candidate) { $Python = $Candidate } else { throw 'Python 3.12 not found. Restart this installer after installing Python 3.12 with the Python launcher.' }
}
if (-not (Test-Path '.venv\Scripts\python.exe')) {
    & $Python -m venv .venv
    Check-Exit 'Creating app environment'
}
$AppPython = Join-Path (Get-Location) '.venv\Scripts\python.exe'
& $AppPython -m pip install -r requirements.txt
Check-Exit 'Installing app dependencies'
if ($Profile -ne 'basic') {
    $OllamaCandidate = Join-Path $env:LOCALAPPDATA 'Programs\Ollama\ollama.exe'
    if (-not (Get-Command ollama -ErrorAction SilentlyContinue) -and -not (Test-Path $OllamaCandidate)) { Install-Winget 'Ollama.Ollama' }
}
& $AppPython scripts\install.py --profile $Profile
Check-Exit 'Installing local AI components'
& $AppPython scripts\doctor.py --profile $Profile
Check-Exit 'Checking installation'
Write-Host 'Visual/TTS setup complete. Run start-windows.bat and review reference frames/clips. Lip-sync requires a separate validated MuseTalk environment; see docs/REFERENCE.md.' -ForegroundColor Green
