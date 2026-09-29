param(
  [string]$DistPath,
  [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
if ([string]::IsNullOrWhiteSpace($DistPath)) {
  $DistPath = Join-Path $Root "dist"
}
$AppName = -join [char[]](0x6B27, 0x63D0, 0x52AA, 0x65AF, 0x684C, 0x5BA0)

& $Python -m py_compile "$Root\othinus_pet.py"
& $Python -m PyInstaller --noconfirm --clean --onefile --windowed `
  --name "$AppName" `
  --icon "$Root\assets\othinus_icon_v4_fullbody.ico" `
  --version-file "$Root\version_info.txt" `
  --add-data "$Root\assets;assets" `
  --exclude-module PySide6.QtWebEngineCore `
  --exclude-module PySide6.QtWebEngineWidgets `
  --exclude-module PySide6.QtQuick `
  --exclude-module PySide6.QtQml `
  --distpath "$DistPath" `
  --workpath "$Root\build" `
  --specpath "$Root" `
  "$Root\othinus_pet.py"

# Notify Explorer about the exact rebuilt path without restarting Explorer.
$RefreshSource = 'using System; using System.Runtime.InteropServices; public static class DesktopIconRefresh { [DllImport("shell32.dll", EntryPoint = "SHChangeNotify")] public static extern void NotifyAll(uint eventId, uint flags, IntPtr item1, IntPtr item2); [DllImport("shell32.dll", EntryPoint = "SHChangeNotify", CharSet = CharSet.Unicode)] public static extern void NotifyPath(uint eventId, uint flags, string item1, IntPtr item2); }'
Add-Type -TypeDefinition $RefreshSource
$BuiltExe = Join-Path $DistPath "$AppName.exe"
[DesktopIconRefresh]::NotifyPath(0x00002000, 0x0005, $BuiltExe, [IntPtr]::Zero)
[DesktopIconRefresh]::NotifyAll(0x08000000, 0x0000, [IntPtr]::Zero, [IntPtr]::Zero)
