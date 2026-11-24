# Builds the browser version (WebAssembly via pygbag) into build\web.
#
#   .\build_web.ps1                                  # build
#   .venv\Scripts\python.exe -m pygbag --port 8000 build\stage   # local test server, open http://localhost:8000
#
# Upload build\web to any static host (for example itch.io) to share the game.

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$stage = Join-Path $root "build\stage"
$out = Join-Path $root "build\web"

Remove-Item -Recurse -Force $stage, $out -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $stage | Out-Null
Copy-Item (Join-Path $root "main.py") $stage
Copy-Item (Join-Path $root "babyblade") (Join-Path $stage "babyblade") -Recurse
Get-ChildItem $stage -Recurse -Filter __pycache__ | Remove-Item -Recurse -Force

$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "python" }
& $py -m pygbag --build $stage
if ($LASTEXITCODE -ne 0) { throw "pygbag build failed" }
Copy-Item (Join-Path $stage "build\web") $out -Recurse
Write-Host "Web build ready in: $out"
