# Downloads one representative image per film, listed in stills_manifest.csv.
# No API key required - the manifest already holds resolved TMDB image URLs.
# Usage:  cd to this folder, then:  powershell -ExecutionPolicy Bypass -File .\download_stills.ps1

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$csv  = Join-Path $root 'stills_manifest.csv'
$out  = Join-Path $root 'images'

if (-not (Test-Path $csv)) { throw "stills_manifest.csv not found next to this script." }
New-Item -ItemType Directory -Force -Path $out | Out-Null

$rows = Import-Csv -Path $csv -Encoding UTF8
$ok = 0; $skip = 0; $fail = @()
$i = 0

foreach ($r in $rows) {
    $i++
    $dest = Join-Path $out $r.filename
    $tag  = "[{0,2}/{1}] {2}" -f $i, $rows.Count, $r.filename

    if (Test-Path $dest) { Write-Host "$tag  (already present)" -ForegroundColor DarkGray; $skip++; continue }

    try {
        Invoke-WebRequest -Uri $r.url -OutFile $dest -UseBasicParsing -TimeoutSec 60
        $kb = [math]::Round((Get-Item $dest).Length / 1KB)
        $colour = if ($r.image_type -eq 'backdrop') { 'Green' } else { 'Yellow' }
        Write-Host "$tag  $($r.image_type), ${kb} KB" -ForegroundColor $colour
        $ok++
    } catch {
        Write-Host "$tag  FAILED: $($_.Exception.Message)" -ForegroundColor Red
        if (Test-Path $dest) { Remove-Item $dest -Force }
        $fail += $r
    }
    Start-Sleep -Milliseconds 120
}

Write-Host ""
Write-Host "Downloaded $ok, skipped $skip, failed $($fail.Count)." -ForegroundColor Cyan
Write-Host "Images: $out"
if ($fail.Count -gt 0) {
    Write-Host "`nFailed rows (re-run to retry):" -ForegroundColor Red
    $fail | ForEach-Object { Write-Host "  $($_.filename)  $($_.url)" }
}
