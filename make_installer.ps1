$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$distRoot = Join-Path $projectRoot 'dist\SkyCityDemo'
$stageRoot = Join-Path $projectRoot 'build\installer_payload'
$payloadRoot = Join-Path $stageRoot 'payload'
$archivePath = Join-Path $stageRoot 'SkyCityPayload.tar'
$sedPath = Join-Path $stageRoot 'SkyCityDemo_Setup.sed'
$outputPath = Join-Path $projectRoot 'dist\SkyCityDemo_Setup.exe'

if (-not (Test-Path -LiteralPath (Join-Path $distRoot 'SkyCityDemo.exe'))) {
    throw 'dist\SkyCityDemo is missing. Build the PyInstaller distribution first.'
}

if (Test-Path -LiteralPath $stageRoot) {
    Remove-Item -LiteralPath $stageRoot -Recurse -Force
}
if (Test-Path -LiteralPath $outputPath) {
    Remove-Item -LiteralPath $outputPath -Force
}
New-Item -ItemType Directory -Force -Path $payloadRoot | Out-Null
Copy-Item -LiteralPath (Join-Path $projectRoot 'installer\install.cmd'), (Join-Path $projectRoot 'installer\install.ps1') -Destination $stageRoot -Force
Get-ChildItem -LiteralPath $distRoot -Force | Copy-Item -Destination $payloadRoot -Recurse -Force
Copy-Item -LiteralPath (Join-Path $projectRoot 'installer\uninstall.cmd'), (Join-Path $projectRoot 'installer\uninstall.ps1'), (Join-Path $projectRoot 'README_DEMO.md'), (Join-Path $projectRoot 'INSTALLER_README.md'), (Join-Path $projectRoot 'BUILDING_QUOTES.md'), (Join-Path $projectRoot 'quote_research.md') -Destination $payloadRoot -Force

tar.exe -cf $archivePath -C $payloadRoot .
if ($LASTEXITCODE -ne 0) {
    throw 'Could not create the installer payload archive.'
}

$sed = @"
[Version]
Class=IEXPRESS
SEDVersion=3

[Options]
PackagePurpose=InstallApp
ShowInstallProgramWindow=1
HideExtractAnimation=1
UseLongFileName=1
InsideCompressed=0
CAB_FixedSize=0
CAB_ResvCodeSigning=0
RebootMode=N
InstallPrompt=%InstallPrompt%
DisplayLicense=%DisplayLicense%
FinishMessage=%FinishMessage%
TargetName=%TargetName%
FriendlyName=%FriendlyName%
AppLaunched=%AppLaunched%
PostInstallCmd=%PostInstallCmd%
SourceFiles=SourceFiles

[Strings]
InstallPrompt=
DisplayLicense=
FinishMessage=
TargetName="$outputPath"
FriendlyName="Sky City Demo Setup"
AppLaunched="install.cmd"
PostInstallCmd=<None>
FILE0="install.cmd"
FILE1="install.ps1"
FILE2="SkyCityPayload.tar"

[SourceFiles]
SourceFiles0=$stageRoot

[SourceFiles0]
%FILE0%=
%FILE1%=
%FILE2%=
"@
Set-Content -LiteralPath $sedPath -Value $sed -Encoding ASCII

$iexpress = Start-Process -FilePath 'iexpress.exe' -ArgumentList @('/N', '/Q', $sedPath) -PassThru
for ($attempt = 0; $attempt -lt 180 -and -not (Test-Path -LiteralPath $outputPath); $attempt++) {
    Start-Sleep -Seconds 1
}
if (-not (Test-Path -LiteralPath $outputPath)) {
    if ($iexpress -and -not $iexpress.HasExited) {
        Stop-Process -Id $iexpress.Id -Force -ErrorAction SilentlyContinue
    }
    throw 'IExpress did not create the installer executable.'
}
if ($iexpress -and -not $iexpress.HasExited) {
    $iexpress.WaitForExit(5000) | Out-Null
}

$size = (Get-Item -LiteralPath $outputPath).Length
Write-Host "Created $outputPath ($size bytes)"
