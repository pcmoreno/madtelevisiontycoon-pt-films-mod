<#
  Pacote Portugues - uninstaller. Removes only the files the installer wrote and that are unchanged
  (checked by SHA-1 against the install record), so the game's own files are never touched.
  All logic lives in install.ps1; this just runs it with -Uninstall.
  Usage: Uninstall.bat [-DryRun]   or   powershell -NoProfile -ExecutionPolicy Bypass -File uninstall.ps1 [-GamePath PATH] [-DryRun]
#>
param([Parameter(Position = 0)][string]$GamePath, [switch]$DryRun, [switch]$Elevated)
$a = @{ Uninstall = $true; DryRun = $DryRun; Elevated = $Elevated }
if ($GamePath) { $a.GamePath = $GamePath }
& (Join-Path $PSScriptRoot 'install.ps1') @a
exit $LASTEXITCODE
