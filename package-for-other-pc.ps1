$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$release = Join-Path $root 'release'
New-Item -ItemType Directory -Force -Path $release | Out-Null
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$stage = Join-Path $env:TEMP ("VoiceTutor-package-" + [guid]::NewGuid().ToString('N'))
$app = Join-Path $stage 'VoiceTutor'
New-Item -ItemType Directory -Force -Path (Join-Path $app 'characters') | Out-Null

# Copy an allowlist only. This intentionally omits .env, .venv, local characters,
# and all reference voice recordings from the shareable build.
$files = @(
    'start.bat',
    'open-chrome-app.bat',
    'configure_first_run.py',
    '.env.example',
    'server.py',
    'index.html',
    'requirements.txt',
    'requirements-chatterbox.txt',
    'README.md'
)
foreach ($file in $files) {
    $source = Join-Path $root $file
    if (-not (Test-Path -LiteralPath $source -PathType Leaf)) {
        throw "Required package file is missing: $file"
    }
    Copy-Item -LiteralPath $source -Destination (Join-Path $app $file)
}
Copy-Item -LiteralPath (Join-Path $root 'characters/example-japanese.json') -Destination (Join-Path $app 'characters/example-japanese.json')

$zip = Join-Path $release "VoiceTutor-Windows-$stamp.zip"
Compress-Archive -LiteralPath $app -DestinationPath $zip -CompressionLevel Optimal
Write-Host "Created $zip"
Write-Host 'Package contents exclude .env, local character files, and all existing voice recordings.'
