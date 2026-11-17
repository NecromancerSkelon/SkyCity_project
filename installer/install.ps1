param(
    [Parameter(Mandatory = $true)]
    [string]$PayloadRoot
)

$ErrorActionPreference = 'Stop'
$productName = 'Sky City Demo'
$targetRoot = $env:SKYCITY_INSTALL_ROOT
if ([string]::IsNullOrWhiteSpace($targetRoot)) {
    $targetRoot = Join-Path $env:LOCALAPPDATA 'SkyCityDemo'
}

if (-not (Test-Path -LiteralPath $PayloadRoot)) {
    throw "Payload directory was not found: $PayloadRoot"
}

New-Item -ItemType Directory -Force -Path $targetRoot | Out-Null
Get-ChildItem -LiteralPath $PayloadRoot -Force | Copy-Item -Destination $targetRoot -Recurse -Force

$gameExe = Join-Path $targetRoot 'SkyCityDemo.exe'
if (-not (Test-Path -LiteralPath $gameExe)) {
    throw "The installed game executable was not found: $gameExe"
}

$shell = New-Object -ComObject WScript.Shell
$startMenu = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Sky City Demo'
New-Item -ItemType Directory -Force -Path $startMenu | Out-Null

function New-Shortcut([string]$path, [string]$target, [string]$workingDirectory) {
    $shortcut = $shell.CreateShortcut($path)
    $shortcut.TargetPath = $target
    $shortcut.WorkingDirectory = $workingDirectory
    $shortcut.IconLocation = "$target,0"
    $shortcut.Save()
}

New-Shortcut (Join-Path $startMenu 'Sky City Demo.lnk') $gameExe $targetRoot
$uninstallCmd = Join-Path $targetRoot 'Uninstall.cmd'
if (Test-Path -LiteralPath $uninstallCmd) {
    New-Shortcut (Join-Path $startMenu 'Uninstall Sky City Demo.lnk') $uninstallCmd $targetRoot
}

$desktop = Join-Path $env:USERPROFILE 'Desktop'
if (Test-Path -LiteralPath $desktop) {
    New-Shortcut (Join-Path $desktop 'Sky City Demo.lnk') $gameExe $targetRoot
}

Write-Host "$productName installed to $targetRoot"
exit 0
