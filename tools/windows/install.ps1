<#
  Pacote Portugues - installer for Mad Television Tycoon (Windows PowerShell 5.1, no other software).

  Does what tools/install_mod.py does, on the player's PC:
    1. finds the game (Steam libraries, or -GamePath / drag-and-drop / a typed path),
    2. plans everything and checks it BEFORE changing anything: no other mod's
       DATABASE\MOD\ItemsData.json / CastData.json, no ID clash with the game's own entries,
       gapless image numbering in each SCRN\<GENRE>\ folder,
    3. removes the files of a previous install (only files it wrote and that are unchanged, by SHA-1),
    4. writes DATABASE\MOD\ItemsData.json and CastData.json = the game's own files + our entries
       (textual merge: the game's text is kept byte for byte; nothing is re-serialised),
    5. writes the install record (DATABASE\MOD\pt_films_install.json and install_record.json here),
    6. copies the images, numbered straight after the game's own.

  The record has the same format as install_mod.py's, so either installer can remove the other's install.

  Usage (from the extracted folder):
    Install.bat                       (double-click; or drop the game folder onto it)
    Install.bat -DryRun               (from a command prompt: show what would happen)
    powershell -NoProfile -ExecutionPolicy Bypass -File install.ps1 [-GamePath PATH] [-DryRun] [-Uninstall]

  This file must stay ASCII-only: Windows PowerShell 5.1 reads a .ps1 without a BOM in the ANSI code page.
#>
[CmdletBinding()]
param(
    [Parameter(Position = 0)][string]$GamePath,
    [switch]$DryRun,
    [switch]$Uninstall,
    [switch]$Elevated
)

Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'

$ModName      = 'Pacote Portugu' + [char]0xEA + 's'
$AppId        = '3565020'
$RecordName   = 'pt_films_install.json'
$ModFiles     = @('ItemsData.json', 'CastData.json')
$Here         = $PSScriptRoot
$LocalRecord  = Join-Path $Here 'install_record.json'
$OurItems     = Join-Path $Here 'data\PacotePortugues_items.json'
$OurCast      = Join-Path $Here 'data\PacotePortugues_cast.json'
$OurImages    = Join-Path $Here 'data\images'
$Utf8NoBom    = New-Object System.Text.UTF8Encoding($false)
$Folder = @{ 0 = 'ACTION'; 1 = 'DRAMA'; 2 = 'SCIFI'; 3 = 'ROMANTIC'; 4 = 'FANTASY'; 5 = 'CRIME'; 6 = 'THRILLER';
             7 = 'HORROR'; 8 = 'MYSTERY'; 9 = 'ADVENTURE'; 10 = 'FAMILY'; 11 = 'DOCU'; 14 = 'ANTIWAR';
             15 = 'WESTERN'; 16 = 'COMEDY'; 27 = 'CARTOON'; 28 = 'EROTIC'; 29 = 'HISTORICAL' }

function Say([string]$msg) { if ($DryRun) { Write-Host "[dry-run] $msg" } else { Write-Host $msg } }
function Fail([string]$msg) { Write-Host ''; Write-Host "ERROR: $msg" -ForegroundColor Red; exit 1 }

function Get-Sha1([string]$path) { (Get-FileHash -LiteralPath $path -Algorithm SHA1).Hash.ToLowerInvariant() }
function Read-Text([string]$path) { [System.IO.File]::ReadAllText($path, $Utf8NoBom) }   # strips a BOM if there is one
function Write-Text([string]$path, [string]$text) { [System.IO.File]::WriteAllText($path, $text, $Utf8NoBom) }

# The game's files have trailing commas, which ConvertFrom-Json (5.1) rejects. Same regex as install_mod.py.
function ConvertFrom-LenientJson([string]$text) {
    ($text -replace ',(\s*[\]}])', '$1') | ConvertFrom-Json
}

# ---------------------------------------------------------------- finding the game
function Test-Extern([string]$p) {
    $p -and (Test-Path -LiteralPath (Join-Path $p 'SCRN') -PathType Container) -and
            (Test-Path -LiteralPath (Join-Path $p 'DATABASE\ItemsData.json') -PathType Leaf)
}

# Accepts the EXTERN folder, the MadTelevisionTycoon subfolder, the game folder, or the .exe.
function Resolve-Extern([string]$p) {
    if (-not $p) { return $null }
    $p = $p.Trim().Trim('"').TrimEnd('\')
    if (Test-Path -LiteralPath $p -PathType Leaf) { $p = Split-Path -Parent $p }
    foreach ($c in @($p, (Join-Path $p 'EXTERN'), (Join-Path $p 'MadTelevisionTycoon\EXTERN'))) {
        if (Test-Extern $c) { return (Resolve-Path -LiteralPath $c).ProviderPath }
    }
    return $null
}

function Find-Game {
    $steamRoots = New-Object System.Collections.Generic.List[string]
    foreach ($k in @(@('HKCU:\Software\Valve\Steam', 'SteamPath'),
                     @('HKLM:\SOFTWARE\WOW6432Node\Valve\Steam', 'InstallPath'),
                     @('HKLM:\SOFTWARE\Valve\Steam', 'InstallPath'))) {
        $v = (Get-ItemProperty -Path $k[0] -Name $k[1] -ErrorAction SilentlyContinue)
        if ($v) { $steamRoots.Add(($v.($k[1]) -replace '/', '\')) }        # SteamPath uses forward slashes
    }
    $steamRoots.Add("${env:ProgramFiles(x86)}\Steam")
    $libs = New-Object System.Collections.Generic.List[string]
    foreach ($root in $steamRoots) {
        $libs.Add($root)
        $vdf = Join-Path $root 'steamapps\libraryfolders.vdf'
        if (Test-Path -LiteralPath $vdf) {
            foreach ($m in [regex]::Matches((Read-Text $vdf), '"path"\s+"((?:[^"\\]|\\.)*)"')) {
                $libs.Add(($m.Groups[1].Value -replace '\\\\', '\'))
            }
        }
    }
    foreach ($lib in ($libs | Select-Object -Unique)) {
        $acf = Join-Path $lib "steamapps\appmanifest_$AppId.acf"
        $dir = 'Mad Television Tycoon'
        if (Test-Path -LiteralPath $acf) {
            $m = [regex]::Match((Read-Text $acf), '"installdir"\s+"([^"]+)"')
            if ($m.Success) { $dir = $m.Groups[1].Value }
        }
        $e = Resolve-Extern (Join-Path $lib "steamapps\common\$dir")
        if ($e) { return $e }
    }
    # Steam also registers an uninstall entry with the install folder
    $u = Get-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Steam App $AppId" `
                          -Name InstallLocation -ErrorAction SilentlyContinue
    if ($u) { return (Resolve-Extern $u.InstallLocation) }
    return $null
}

# ---------------------------------------------------------------- record
function Read-Record([string]$modDir, [string]$extern) {
    $p = Join-Path $modDir $RecordName
    if (Test-Path -LiteralPath $p) { return (Read-Text $p | ConvertFrom-Json) }
    if (Test-Path -LiteralPath $LocalRecord) {
        $r = Read-Text $LocalRecord | ConvertFrom-Json
        if ($r.extern -and ($r.extern.TrimEnd('\') -eq $extern.TrimEnd('\'))) {   # -eq is case-insensitive
            Write-Host "No install record in DATABASE\MOD\: using the copy beside this script."
            return $r
        }
    }
    return $null
}

function Test-Ours([string]$modDir, [string]$name, $record) {
    $p = Join-Path $modDir $name
    if (-not $record -or -not $record.mod_files) { return $false }
    $known = $record.mod_files.PSObject.Properties[$name]
    return ($known -and (Test-Path -LiteralPath $p) -and ((Get-Sha1 $p) -eq $known.Value))
}

# Works out what a previous install left that may be deleted. Changes nothing.
function Get-PreviousFiles([string]$extern, $record) {
    $modDir = Join-Path $extern 'DATABASE\MOD'
    $plan = @{ Delete = New-Object System.Collections.Generic.List[string]; Freed = @{}; Kept = 0; Left = @() }
    foreach ($img in @($record.images)) {
        $p = Join-Path $extern ("SCRN\{0}\{1}" -f $img.folder, $img.file)
        if (-not (Test-Path -LiteralPath $p)) { continue }
        if ((Get-Sha1 $p) -eq $img.sha1) {
            $plan.Delete.Add($p)
            if (-not $plan.Freed.ContainsKey($img.folder)) { $plan.Freed[$img.folder] = @{} }
            $plan.Freed[$img.folder][[int]($img.file -replace '\.png$', '')] = $true
        } else { $plan.Kept++ }   # a game update put its own image at that number: leave it alone
    }
    $names = @(); if ($record.mod_files) { $names = @($record.mod_files.PSObject.Properties | ForEach-Object Name) }
    foreach ($n in $names) {
        $p = Join-Path $modDir $n
        if (-not (Test-Path -LiteralPath $p)) { continue }
        if (Test-Ours $modDir $n $record) { $plan.Delete.Add($p) } else { $plan.Left += $n }
    }
    $p = Join-Path $modDir $RecordName
    if (Test-Path -LiteralPath $p) { $plan.Delete.Add($p) }
    return $plan
}

function Remove-Planned($plan) {
    $imgs = @($plan.Delete | Where-Object { $_ -like '*.png' }).Count
    Say ("remove $imgs images of the previous install" + $(if ($plan.Kept) { ", leave $($plan.Kept) that a game update replaced" } else { '' }))
    foreach ($p in $plan.Delete) {
        if ($p -notlike '*.png') { Say ("remove DATABASE\MOD\" + (Split-Path -Leaf $p)) }
        if (-not $DryRun) { Remove-Item -LiteralPath $p -Force }
    }
    foreach ($n in $plan.Left) { Write-Host "left DATABASE\MOD\$n : it is not the file this mod installed" }
}

# ---------------------------------------------------------------- merging
# Inserts the entries of $oursText ({"data":[...]}) before the closing ']' of $vanillaText.
function Merge-JsonText([string]$vanillaText, [string]$oursText, [string]$what) {
    $m = [regex]::Match($vanillaText, '\]\s*\}\s*$')
    if (-not $m.Success) { Fail "$what in the game folder does not end with ']}' - unexpected format, not touching it." }
    $head = $vanillaText.Substring(0, $m.Index).TrimEnd()
    $tail = $vanillaText.Substring($m.Index)
    $o = [regex]::Match($oursText, '^\s*\{\s*"data"\s*:\s*\[([\s\S]*)\]\s*\}\s*$')
    if (-not $o.Success) { Fail "data\ file for $what has an unexpected format." }
    $inner = $o.Groups[1].Value.Trim()
    $last = $head[$head.Length - 1]
    if ($last -eq ',' -or $last -eq '[') { $sep = "`n" }        # game file already ends with a trailing comma
    elseif ($last -eq '}') { $sep = ",`n" }
    else { Fail "$what in the game folder: unexpected character '$last' before the closing ']'." }
    return $head + $sep + "`t`t" + $inner + "`n`t" + $tail
}

function Get-Ids($entries) { $h = @{}; foreach ($e in $entries) { $h[[long]$e.ID] = $true }; return $h }

# ---------------------------------------------------------------- write access / elevation
function Test-Writable([string]$dir) {
    $probe = Join-Path $dir ('.ptmod_probe_' + [guid]::NewGuid().ToString('N'))
    try { [System.IO.File]::WriteAllText($probe, 'x'); Remove-Item -LiteralPath $probe -Force; return $true }
    catch [System.UnauthorizedAccessException] { return $false }
}

function Restart-Elevated([string]$extern) {
    $isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
                [Security.Principal.WindowsBuiltInRole]::Administrator)
    if ($isAdmin -or $Elevated) { Fail "No permission to write in $extern, even as administrator." }
    Write-Host 'The game folder is write-protected for your account. Asking Windows for administrator rights...'
    $a = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', "`"$PSCommandPath`"", '-GamePath', "`"$extern`"", '-Elevated')
    if ($Uninstall) { $a += '-Uninstall' }
    try { $p = Start-Process -FilePath 'powershell.exe' -ArgumentList $a -Verb RunAs -Wait -PassThru }
    catch { Fail 'Administrator rights were refused. Nothing was changed.' }
    exit $p.ExitCode
}

# ---------------------------------------------------------------- main
try {
    Write-Host "Pacote Portugues - $(if ($Uninstall) { 'uninstall' } else { 'install' })"
    Write-Host ''
    if (-not $Uninstall) {
        foreach ($p in @($OurItems, $OurCast, $OurImages)) {
            if (-not (Test-Path -LiteralPath $p)) { Fail "Missing $p. Extract the whole zip, then run Install.bat from the extracted folder." }
        }
    }

    $extern = Resolve-Extern $GamePath
    if ($GamePath -and -not $extern) { Fail "Not the game folder (no EXTERN\SCRN and EXTERN\DATABASE found under it): $GamePath" }
    if (-not $extern) { $extern = Find-Game }
    while (-not $extern) {
        Write-Host 'Could not find Mad Television Tycoon automatically.'
        Write-Host 'In Steam: right-click the game > Manage > Browse local files, copy the folder path from the address bar.'
        $typed = Read-Host 'Paste the game folder path here (or press Enter to quit)'
        if (-not $typed) { exit 1 }
        $extern = Resolve-Extern $typed
    }
    Write-Host "Game data folder: $extern"
    Write-Host ''
    $modDir = Join-Path $extern 'DATABASE\MOD'
    $db     = Join-Path $extern 'DATABASE'
    if (-not (Test-Path -LiteralPath $modDir)) { Fail "No DATABASE\MOD folder in $extern. Verify the game files in Steam." }

    if (Get-Process -Name 'MadTelevisionTycoon*' -ErrorAction SilentlyContinue) {
        Fail 'Mad Television Tycoon is running. Close the game first.'
    }
    if (-not $DryRun -and -not ((Test-Writable $modDir) -and (Test-Writable (Join-Path $extern 'SCRN')))) {
        Restart-Elevated $extern
    }

    $record = Read-Record $modDir $extern

    if ($Uninstall) {
        if (-not $record) { Fail 'No install record found: nothing to remove.' }
        Remove-Planned (Get-PreviousFiles $extern $record)
        if (Test-Path -LiteralPath $LocalRecord) {   # only if it belongs to this game folder
            $lr = Read-Text $LocalRecord | ConvertFrom-Json
            if ($lr.extern -and ($lr.extern.TrimEnd('\') -eq $extern.TrimEnd('\'))) {
                Say 'remove install_record.json (copy beside this script)'
                if (-not $DryRun) { Remove-Item -LiteralPath $LocalRecord -Force }
            }
        }
        Write-Host ''
        Write-Host $(if ($DryRun) { 'Dry run only: nothing was removed.' } else { 'Done. The game is back to its own films.' })
        exit 0
    }

    # 1. another mod's files?
    $foreign = @($ModFiles | Where-Object { (Test-Path -LiteralPath (Join-Path $modDir $_)) -and -not (Test-Ours $modDir $_ $record) })
    if ($foreign.Count) {
        Fail ("DATABASE\MOD\ already holds " + ($foreign -join ', ') + " from another mod. This installer will not overwrite it.`n" +
              "Uninstall that mod (or move those files aside), then run Install.bat again.")
    }

    # 2. what a previous install of ours left (deleted later, after all checks pass)
    $prev = $null
    if ($record) { $prev = Get-PreviousFiles $extern $record }

    # 3. our data, and the game's own
    $itemsText = Read-Text $OurItems
    $castText  = Read-Text $OurCast
    $items = @((ConvertFrom-Json $itemsText).data)
    $cast  = @((ConvertFrom-Json $castText).data)
    $vanItemsText = Read-Text (Join-Path $db 'ItemsData.json')
    $vanCastText  = Read-Text (Join-Path $db 'CastData.json')
    $vanItems = @((ConvertFrom-LenientJson $vanItemsText).data)
    $vanCast  = @((ConvertFrom-LenientJson $vanCastText).data)
    foreach ($pair in @(@('ItemsData', $vanItems, $items), @('CastData', $vanCast, $cast))) {
        $v = Get-Ids $pair[1]
        $clash = @($pair[2] | Where-Object { $v.ContainsKey([long]$_.ID) } | ForEach-Object { $_.ID })
        if ($clash.Count) { Fail ("{0}: our IDs clash with the game's IDs {1}. The game probably added entries; this mod needs an update." -f $pair[0], (($clash | Select-Object -First 10) -join ', ')) }
    }

    # 4. image numbers: straight after the game's own, which must have no gaps
    $next = @{}; $images = New-Object System.Collections.Generic.List[object]; $texture = @{}
    foreach ($it in $items) {
        $f = $Folder[[int]$it.Genre]
        if (-not $f) { Fail "Film $($it.ID): genre $($it.Genre) has no picture folder." }
        $src = Join-Path $OurImages ("{0}.png" -f $it.ID)
        if (-not (Test-Path -LiteralPath $src)) { Fail "Missing image $src. Extract the whole zip again." }
        if (-not $next.ContainsKey($f)) {
            $dir = Join-Path $extern "SCRN\$f"
            if (-not (Test-Path -LiteralPath $dir)) { Fail "The game has no SCRN\$f folder." }
            $nums = @{}
            Get-ChildItem -LiteralPath $dir -Filter '*.png' -File | Where-Object { $_.BaseName -match '^\d+$' } |
                ForEach-Object { $nums[[int]$_.BaseName] = $true }
            if ($prev -and $prev.Freed.ContainsKey($f)) { foreach ($k in $prev.Freed[$f].Keys) { $nums.Remove($k) } }
            $n = $nums.Count
            $bad = @($nums.Keys | Where-Object { $_ -lt 1 -or $_ -gt $n })
            if ($bad.Count) { Fail "SCRN\$f has gaps or extra files in its numbering ($n files, highest $(($nums.Keys | Measure-Object -Maximum).Maximum)). Verify the game files in Steam, then run again." }
            $next[$f] = $n + 1
        }
        $num = $next[$f]; $next[$f]++
        $texture[[long]$it.ID] = $num
        $images.Add([ordered]@{ id = [long]$it.ID; folder = $f; file = ('{0:D4}.png' -f $num); sha1 = (Get-Sha1 $src); src = $src })
    }

    # 5. set each film's Texture in our JSON text (no re-serialising: accents and number formats stay as they are)
    $script:hits = 0
    $itemsText = [regex]::Replace($itemsText, '("ID"\s*:\s*(\d+)\s*,(?:(?!"ID"\s*:)[\s\S])*?"Texture"\s*:\s*)-?\d+', {
        param($m)
        $id = [long]$m.Groups[2].Value
        if (-not $texture.ContainsKey($id)) { return $m.Value }
        $script:hits++
        return $m.Groups[1].Value + $texture[$id]
    })
    if ($script:hits -ne $items.Count) { Fail "Internal: set Texture on $($script:hits) of $($items.Count) films. Data file format unexpected." }

    $mergedItems = Merge-JsonText $vanItemsText $itemsText 'ItemsData.json'
    $mergedCast  = Merge-JsonText $vanCastText  $castText  'CastData.json'

    # 6. check the merged text before writing it
    foreach ($chk in @(@('ItemsData', $mergedItems, $vanItems.Count, $items), @('CastData', $mergedCast, $vanCast.Count, $cast))) {
        $d = @((ConvertFrom-LenientJson $chk[1]).data)
        $want = $chk[2] + $chk[3].Count
        if ($d.Count -ne $want) { Fail "Internal: merged $($chk[0]) has $($d.Count) entries, expected $want." }
        $tailIds = @($d[$chk[2]..($want - 1)] | ForEach-Object { [long]$_.ID })
        $ourIds  = @($chk[3] | ForEach-Object { [long]$_.ID })
        if (Compare-Object $tailIds $ourIds -SyncWindow 0) { Fail "Internal: merged $($chk[0]) does not end with our entries." }
        if ($chk[0] -eq 'ItemsData') {
            foreach ($e in $d[$chk[2]..($want - 1)]) { if ([int]$e.Texture -ne $texture[[long]$e.ID]) { Fail "Internal: wrong Texture for $($e.ID)." } }
        }
    }

    # ---- all checks passed: now change things
    if ($prev) { Remove-Planned $prev; Write-Host '' }

    Say ("write DATABASE\MOD\ItemsData.json ({0} game entries + {1} films)" -f $vanItems.Count, $items.Count)
    Say ("write DATABASE\MOD\CastData.json ({0} game entries + {1} cast)" -f $vanCast.Count, $cast.Count)
    $rec = [ordered]@{ mod = $ModName; extern = $extern; installer = 'install.ps1'; images = @(); mod_files = [ordered]@{} }
    foreach ($img in $images) { $rec.images += [ordered]@{ id = $img.id; folder = $img.folder; file = $img.file; sha1 = $img.sha1 } }
    if (-not $DryRun) {
        Write-Text (Join-Path $modDir 'ItemsData.json') $mergedItems
        Write-Text (Join-Path $modDir 'CastData.json')  $mergedCast
        foreach ($n in $ModFiles) { $rec.mod_files[$n] = Get-Sha1 (Join-Path $modDir $n) }
    }
    # The record goes in before the images, so an interrupted copy can still be undone.
    $recText = ConvertTo-Json -InputObject $rec -Depth 6
    Say "write DATABASE\MOD\$RecordName (install record)"
    if (-not $DryRun) {
        Write-Text (Join-Path $modDir $RecordName) $recText
        try { Write-Text $LocalRecord $recText } catch { Write-Host "(could not save install_record.json beside the script: $($_.Exception.Message))" }
    }

    Write-Host ''
    Say "copy $($images.Count) images:"
    foreach ($f in ($next.Keys | Sort-Object)) {
        $mine = @($images | Where-Object { $_.folder -eq $f })
        $first = $mine[0].file.Substring(0, 4); $last = '{0:D4}' -f ($next[$f] - 1)
        Write-Host ('  {0,-11} {1}' -f $f, $(if ($first -eq $last) { $first } else { "$first-$last" }))
    }
    if (-not $DryRun) {
        foreach ($img in $images) { Copy-Item -LiteralPath $img.src -Destination (Join-Path $extern ("SCRN\{0}\{1}" -f $img.folder, $img.file)) -Force }
    }
    Write-Host ''
    if ($DryRun) { Write-Host 'Dry run only: nothing was written.' }
    else {
        Write-Host 'Done.'
        Write-Host 'Start a NEW game to see the films.'
        Write-Host 'Run Install.bat again after every game update.'
    }
    exit 0
}
catch {
    Fail ($_.Exception.Message + "`n(at line " + $_.InvocationInfo.ScriptLineNumber + ')')
}
