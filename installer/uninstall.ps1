$ErrorActionPreference = 'SilentlyContinue'
$targetRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$productName = 'Sky City Demo'

$startMenu = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Sky City Demo'
Remove-Item -LiteralPath (Join-Path $startMenu 'Sky City Demo.lnk') -Force
Remove-Item -LiteralPath (Join-Path $startMenu 'Uninstall Sky City Demo.lnk') -Force
Remove-Item -LiteralPath (Join-Path $env:USERPROFILE 'Desktop\Sky City Demo.lnk') -Force

$cleanup = "Start-Sleep -Milliseconds 250; Remove-Item -LiteralPath '$targetRoot' -Recurse -Force"
Start-Process powershell.exe -WindowStyle Hidden -ArgumentList '-NoLogo', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', $cleanup
Write-Host "$productName was removed."
