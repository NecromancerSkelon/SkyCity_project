$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$executable = $env:SKYCITY_TEST_EXE
if ([string]::IsNullOrWhiteSpace($executable)) {
    $executable = Join-Path $projectRoot 'dist\SkyCityDemo\SkyCityDemo.exe'
}
if (-not (Test-Path -LiteralPath $executable)) { throw 'Packaged executable not found' }
Add-Type -AssemblyName System.Drawing
Add-Type @'
using System;
using System.Runtime.InteropServices;
public class SkyCityWindowCheck {
    public delegate bool EnumWindowProc(IntPtr window, IntPtr param);
    [StructLayout(LayoutKind.Sequential)]
    public struct Rect { public int Left, Top, Right, Bottom; }
    [DllImport("user32.dll")]
    public static extern bool GetWindowRect(IntPtr window, out Rect rect);
    [DllImport("user32.dll")]
    public static extern bool PostMessage(IntPtr window, uint message, IntPtr wParam, IntPtr lParam);
    [DllImport("user32.dll")]
    public static extern bool EnumWindows(EnumWindowProc callback, IntPtr param);
    [DllImport("user32.dll")]
    public static extern uint GetWindowThreadProcessId(IntPtr window, out uint processId);
    [DllImport("user32.dll")]
    public static extern bool ShowWindow(IntPtr window, int command);
    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr window);
    [DllImport("user32.dll")]
    public static extern bool SetProcessDPIAware();
    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    public static extern int GetWindowText(IntPtr window, System.Text.StringBuilder text, int length);
    [DllImport("user32.dll")]
    public static extern bool PrintWindow(IntPtr window, IntPtr deviceContext, uint flags);
    public static IntPtr FindWindowForProcess(uint processId) {
        IntPtr found = IntPtr.Zero;
        EnumWindows((window, param) => {
            uint owner;
            GetWindowThreadProcessId(window, out owner);
            var title = new System.Text.StringBuilder(256);
            GetWindowText(window, title, 256);
            if (owner == processId && title.ToString().StartsWith("\u5929\u7a7a\u4e4b\u57ce")) {
                found = window; return false;
            }
            return true;
        }, IntPtr.Zero);
        return found;
    }
}
'@
[SkyCityWindowCheck]::SetProcessDPIAware() | Out-Null

function Save-GameCapture([IntPtr] $window, [string] $filename) {
    $bounds = New-Object SkyCityWindowCheck+Rect
    if (-not [SkyCityWindowCheck]::GetWindowRect($window, [ref]$bounds)) { throw 'Cannot inspect game window' }
    $width = $bounds.Right - $bounds.Left
    $height = $bounds.Bottom - $bounds.Top
    if ($width -lt 640 -or $height -lt 400) { throw "Unexpected window size: $width x $height" }
    $bitmap = New-Object System.Drawing.Bitmap($width, $height)
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    try {
        $context = $graphics.GetHdc()
        try {
            if (-not [SkyCityWindowCheck]::PrintWindow($window, $context, 2)) {
                throw 'Game-specific capture failed'
            }
        } finally { $graphics.ReleaseHdc($context) }
        $bitmap.Save((Join-Path $projectRoot "verification\$filename"), [System.Drawing.Imaging.ImageFormat]::Png)
    } finally {
        $graphics.Dispose()
        $bitmap.Dispose()
    }
    Write-Output "Captured $filename ($width x $height)"
}

$gameProcess = Start-Process -FilePath $executable -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru
try {
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        Start-Sleep -Milliseconds 300
        $gameProcess.Refresh()
        if ($gameProcess.HasExited) { throw "Game exited before startup: $($gameProcess.ExitCode)" }
        $window = [SkyCityWindowCheck]::FindWindowForProcess($gameProcess.Id)
        if ($window -ne [IntPtr]::Zero) { break }
    }
    if ($window -eq [IntPtr]::Zero) { throw 'Game window did not appear' }
    [SkyCityWindowCheck]::ShowWindow($window, 9) | Out-Null
    [SkyCityWindowCheck]::SetForegroundWindow($window) | Out-Null
    $activate = New-Object -ComObject WScript.Shell
    $activate.AppActivate($gameProcess.Id) | Out-Null
    Start-Sleep -Milliseconds 600
    Save-GameCapture $window 'packaged_startup.png'
    [SkyCityWindowCheck]::PostMessage($window, 0x10, [IntPtr]::Zero, [IntPtr]::Zero) | Out-Null
    if (-not $gameProcess.WaitForExit(5000)) { throw 'Game failed to exit normally' }
    if ($gameProcess.ExitCode -ne 0) { throw "Nonzero exit code: $($gameProcess.ExitCode)" }
    Write-Output 'Packaged fullscreen startup and window-close exit passed.'
} finally {
    $gameProcess.Refresh()
    if (-not $gameProcess.HasExited) { Stop-Process -Id $gameProcess.Id }
}
