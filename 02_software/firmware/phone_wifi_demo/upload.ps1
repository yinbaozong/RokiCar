param(
  [Parameter(Mandatory = $true)]
  [string]$Port
)

$ErrorActionPreference = "Stop"
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Main = Join-Path $Here "main.py"

if (-not (Get-Command mpremote -ErrorAction SilentlyContinue)) {
  throw "mpremote not found. Install with: pip install mpremote"
}

Write-Host "Stopping current program on $Port..."
mpremote connect $Port exec "import machine; print('connected')"

Write-Host "Uploading main.py..."
mpremote connect $Port fs cp $Main :main.py

Write-Host "Resetting board..."
mpremote connect $Port reset

Write-Host "Done. Phone WiFi: RokiCar-Demo / 12345678 / http://192.168.4.1/"
