<#
.SYNOPSIS
  agyc v1.6 - Instalador para Windows 10/11 (Google Antigravity CLI 1.5.10+)
  Multi-account switcher (Google AI Pro & Ultra) con perfiles HOME aislados y NTFS Junctions.
#>
[CmdletBinding()]
param(
    [switch]$SkipPath,
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

$RepoDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)

function Resolve-RealHome {
    $candidates = @($env:AGYC_REAL_HOME, $env:REAL_HOME, $env:USERPROFILE)
    foreach ($raw in $candidates) {
        if ([string]::IsNullOrWhiteSpace($raw)) { continue }
        $norm = $raw.Trim().Replace("\", "/")
        $idx = $norm.IndexOf("/.agyc_homes/", [System.StringComparison]::OrdinalIgnoreCase)
        if ($idx -ge 0) {
            $cleaned = $raw.Trim().Substring(0, $idx)
        } elseif ($norm.TrimEnd("/").EndsWith("/.agyc_homes", [System.StringComparison]::OrdinalIgnoreCase)) {
            $cut = $norm.TrimEnd("/").Length - "/.agyc_homes".Length
            $cleaned = $raw.Trim().Substring(0, $cut)
        } else {
            $cleaned = $raw.Trim()
        }
        $cleaned = $cleaned.TrimEnd("\", "/")
        if ($cleaned -match "^[A-Za-z]:$") { $cleaned = "$cleaned\" }
        if ($cleaned -and (Test-Path -LiteralPath $cleaned -PathType Container)) {
            return $cleaned
        }
    }
    return $env:USERPROFILE
}

function Write-CmdWrapper {
    param(
        [string]$Path,
        [string]$Content
    )
    $crlf = ($Content -replace "`r`n", "`n") -replace "`n", "`r`n"
    $parent = Split-Path -Parent $Path
    if (-not (Test-Path -LiteralPath $parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }
    [System.IO.File]::WriteAllText($Path, $crlf, $Utf8NoBom)
}

function New-PyCmdWrapperContent {
    param(
        [string]$PythonExe,
        [string]$ScriptName,
        [string]$ExtraFlags = "",
        [string]$InvokedAs = ""
    )
    $lines = @(
        "@echo off",
        "setlocal",
        'set "PYTHONIOENCODING=utf-8"'
    )
    if (-not [string]::IsNullOrWhiteSpace($InvokedAs)) {
        $lines += "set `"AGYC_INVOKED_AS=$InvokedAs`""
    }
    $flagPart = if ([string]::IsNullOrWhiteSpace($ExtraFlags)) { "" } else { "$ExtraFlags " }
    $lines += @(
        "set `"AGYC_PY=$PythonExe`"",
        'if not exist "%AGYC_PY%" set "AGYC_PY=python"',
        "set `"AGYC_SCRIPT=%USERPROFILE%\\.gemini\\antigravity-cli\\bin\\$ScriptName`"",
        "if not exist `"%AGYC_SCRIPT%`" set `"AGYC_SCRIPT=%~dp0$ScriptName`"",
        "`"%AGYC_PY%`" ${flagPart}`"%AGYC_SCRIPT%`" %*",
        "exit /b %ERRORLEVEL%"
    )
    return ($lines -join "`n") + "`n"
}

function Find-Python310Plus {
    param([string]$RealHome = $env:USERPROFILE)
    $probeCode = "import os, sys; assert sys.version_info >= (3, 10); exe = sys.executable if os.path.exists(sys.executable) else ''; print(exe); print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')"
    $nativeSpecs = [System.Collections.Generic.List[object]]::new()
    $msixSpecs = [System.Collections.Generic.List[object]]::new()
    $seen = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)

    $addSpec = {
        param([string]$ExePath, [string[]]$PreArgs = @())
        if ([string]::IsNullOrWhiteSpace($ExePath)) { return }
        $key = "$ExePath|$($PreArgs -join ' ')"
        if (-not $seen.Add($key)) { return }
        if ($ExePath -match '(?i)\\WindowsApps\\') {
            $msixSpecs.Add(@{ Exe = $ExePath; PreArgs = $PreArgs })
        } else {
            $nativeSpecs.Add(@{ Exe = $ExePath; PreArgs = $PreArgs })
        }
    }

    if (-not [string]::IsNullOrWhiteSpace($RealHome)) {
        Get-ChildItem -Path (Join-Path $RealHome ".local\bin\python*.exe") -File -ErrorAction SilentlyContinue |
            Sort-Object Name -Descending | ForEach-Object { & $addSpec $_.FullName }
    }
    if (-not [string]::IsNullOrWhiteSpace($env:APPDATA)) {
        Get-ChildItem -Path (Join-Path $env:APPDATA "uv\python\cpython-*\python.exe") -File -ErrorAction SilentlyContinue |
            Sort-Object FullName -Descending | ForEach-Object { & $addSpec $_.FullName }
    }
    if (-not [string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)) {
        Get-ChildItem -Path (Join-Path $env:LOCALAPPDATA "Programs\Python\Python*\python.exe") -File -ErrorAction SilentlyContinue |
            Sort-Object FullName -Descending | ForEach-Object { & $addSpec $_.FullName }
    }
    foreach ($pat in @("C:\Python*\python.exe", "C:\Program Files\Python*\python.exe")) {
        Get-ChildItem -Path $pat -File -ErrorAction SilentlyContinue |
            Sort-Object FullName -Descending | ForEach-Object { & $addSpec $_.FullName }
    }
    foreach ($candName in @("python", "python3", "py")) {
        $cmds = Get-Command $candName -All -ErrorAction SilentlyContinue
        foreach ($c in $cmds) {
            if (-not $c.Source) { continue }
            $pre = if ($candName -eq "py") { @("-3") } else { @() }
            & $addSpec $c.Source $pre
        }
    }

    $msixFallback = $null
    foreach ($spec in (@($nativeSpecs) + @($msixSpecs))) {
        try {
            $probeArgs = $spec.PreArgs + @("-S", "-c", $probeCode)
            $out = & $spec.Exe @probeArgs 2>$null
            if ($LASTEXITCODE -eq 0 -and $out.Count -ge 2) {
                $resolvedExe = "$($out[0])".Trim()
                if (-not $resolvedExe) { $resolvedExe = $spec.Exe }
                $info = @{
                    Cmd = $resolvedExe
                    PreArgs = @()
                    Executable = $resolvedExe
                    Version = "$($out[1])".Trim()
                    IsMsix = ($resolvedExe -match '(?i)\\WindowsApps\\')
                }
                if ($info.IsMsix) {
                    if (-not $msixFallback) { $msixFallback = $info }
                    continue
                }
                return $info
            }
        } catch {
            continue
        }
    }
    return $msixFallback
}

function Invoke-AgycPython {
    param([string[]]$PyArgs)
    $allArgs = @()
    if ($PyInfo.PreArgs) { $allArgs += $PyInfo.PreArgs }
    $allArgs += $PyArgs
    & $PyInfo.Cmd @allArgs
}

$RealHome = Resolve-RealHome
$LocalAppData = $env:LOCALAPPDATA
if ([string]::IsNullOrWhiteSpace($LocalAppData)) {
    $LocalAppData = Join-Path $RealHome "AppData\Local"
}

$AgyBaseDir = Join-Path $RealHome ".gemini\antigravity-cli"
$AgyBinDir = Join-Path $AgyBaseDir "bin"
$AgyLibDir = Join-Path $AgyBaseDir "lib"
$AgyAccountsDir = Join-Path $AgyBaseDir "accounts"

$LocalAgycDir = Join-Path $LocalAppData "agyc"
$LocalAgycBin = Join-Path $LocalAgycDir "bin"
$LocalAgycLib = Join-Path $LocalAgycDir "lib"
$CacheDir = Join-Path $LocalAgycDir "cache"
$LocksDir = Join-Path $CacheDir "locks"
$RunDir = Join-Path $CacheDir "run"
$HomesDir = Join-Path $RealHome ".agyc_homes"

Write-Host ""
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "       agyc v1.6 - Instalador Windows Multi-Cuenta      " -ForegroundColor Cyan
Write-Host "   Google Antigravity 1.5.10+ (AI Pro & AI Ultra)       " -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

# -- Paso 1: Verificar requisitos ---------------------------------------------
Write-Host "[1/7] Verificando requisitos..." -ForegroundColor White

$PyInfo = Find-Python310Plus -RealHome $RealHome
if (-not $PyInfo) {
    Write-Host "X Python 3.10+ no encontrado. Instala Python 3.10+ desde python.org o winget." -ForegroundColor Red
    exit 1
}
$PythonExe = $PyInfo.Executable
Write-Host "  Python $($PyInfo.Version): $PythonExe" -ForegroundColor DarkGray
if ($PyInfo.IsMsix) {
    Write-Host "! Advertencia: Microsoft Store Python (WindowsApps) usa un contenedor AppX compartido." -ForegroundColor Yellow
    Write-Host "  Se recomienda instalar Python nativo (uv python install o python.org) para sesiones largas." -ForegroundColor DarkGray
}

$AgyRealCandidates = @(
    (Join-Path $AgyBinDir "agy-real.exe"),
    (Join-Path $LocalAgycBin "agy-real.exe"),
    (Join-Path $LocalAppData "agy\bin\agy-real.exe"),
    (Join-Path $LocalAppData "agy\bin\agy.exe")
)
$AgyReal = $null
foreach ($p in $AgyRealCandidates) {
    if (Test-Path -LiteralPath $p -PathType Leaf) {
        $AgyReal = $p
        break
    }
}

if (-not $AgyReal) {
    Write-Host "! Binario agy.exe no encontrado en $LocalAppData\agy\bin ni en $AgyBinDir." -ForegroundColor Yellow
    Write-Host "  Asegurate de tener instalado Google Antigravity CLI (o ejecuta luego 'agyc update')." -ForegroundColor DarkGray
    Write-Host "  El instalador continuara preparando los wrappers y lanzadores." -ForegroundColor DarkGray
} else {
    Write-Host "  Motor Antigravity detectado: $AgyReal" -ForegroundColor DarkGray
}

Write-Host "OK Requisitos verificados" -ForegroundColor Green
Write-Host ""

# -- Paso 2: Crear directorios y endurecer ACLs NTFS --------------------------
Write-Host "[2/7] Creando directorios y endureciendo seguridad NTFS..." -ForegroundColor White

$DirsToCreate = @(
    $AgyBaseDir, $AgyBinDir, $AgyLibDir, $AgyAccountsDir,
    $LocalAgycDir, $LocalAgycBin, $LocalAgycLib,
    $CacheDir, $LocksDir, $RunDir, $HomesDir
)
foreach ($d in $DirsToCreate) {
    New-Item -ItemType Directory -Path $d -Force | Out-Null
}

# Deduplicar .npm en perfiles aislados existentes via NTFS Junction
$RealNpm = Join-Path $RealHome ".npm"
if (Test-Path -LiteralPath $RealNpm -PathType Container) {
    Get-ChildItem -LiteralPath $HomesDir -Directory -ErrorAction SilentlyContinue | ForEach-Object {
        $isoNpm = Join-Path $_.FullName ".npm"
        if (-not (Test-Path -LiteralPath $isoNpm)) {
            cmd /c mklink /J "`"$isoNpm`"" "`"$RealNpm`"" 2>$null | Out-Null
        }
    }
}

# Endurecer ACLs NTFS para carpetas privadas usando lib/platform/win32.py
try {
    $env:AGYC_ACL_REPO = $RepoDir
    $env:AGYC_ACL_TARGETS = (@($AgyAccountsDir, $HomesDir, $CacheDir, $LocksDir, $RunDir) -join ";")
    $aclScript = @'
import os, sys
sys.path.insert(0, os.environ["AGYC_ACL_REPO"])
from lib import platform as p
for path in os.environ["AGYC_ACL_TARGETS"].split(";"):
    if path:
        p.harden_ntfs_acl(path)
'@
    $env:AGYC_INLINE_PY = $aclScript
    Invoke-AgycPython -PyArgs @("-S", "-c", "import os; exec(os.environ['AGYC_INLINE_PY'])") 2>$null | Out-Null
    Remove-Item Env:AGYC_ACL_REPO, Env:AGYC_ACL_TARGETS, Env:AGYC_INLINE_PY -ErrorAction SilentlyContinue
} catch {
}

Write-Host "OK Directorios creados" -ForegroundColor Green
Write-Host ""

# -- Paso 3: Instalar lib/ (incl. lib/platform/), binarios y wrappers .cmd ----
Write-Host "[3/7] Instalando lib/, binarios, wrappers .cmd y hooks settings.json..." -ForegroundColor White

$LibRelFiles = @(
    "__init__.py",
    "agyc_core.py",
    "platform\__init__.py",
    "platform\linux.py",
    "platform\win32.py"
)
foreach ($tLib in @($AgyLibDir, $LocalAgycLib)) {
    foreach ($rel in $LibRelFiles) {
        $srcF = Join-Path $RepoDir "lib\$rel"
        $dstF = Join-Path $tLib $rel
        if (Test-Path -LiteralPath $srcF -PathType Leaf) {
            $dstParent = Split-Path -Parent $dstF
            if (-not (Test-Path -LiteralPath $dstParent)) {
                New-Item -ItemType Directory -Path $dstParent -Force | Out-Null
            }
            Copy-Item -LiteralPath $srcF -Destination $dstF -Force
        }
    }
    Write-Host "  -> $tLib (agyc_core.py + platform/*)" -ForegroundColor DarkGray
}

# Enlazar lib/ en perfiles aislados existentes via NTFS Junction
Get-ChildItem -LiteralPath $HomesDir -Directory -ErrorAction SilentlyContinue | ForEach-Object {
    $isoGem = Join-Path $_.FullName ".gemini\antigravity-cli"
    if (Test-Path -LiteralPath $isoGem -PathType Container) {
        $isoLib = Join-Path $isoGem "lib"
        if (-not (Test-Path -LiteralPath $isoLib)) {
            cmd /c mklink /J "`"$isoLib`"" "`"$AgyLibDir`"" 2>$null | Out-Null
        }
    }
}

$AgyCmdSrc = Join-Path $RepoDir "bin\agy.cmd"
$AgyCmdContent = [System.IO.File]::ReadAllText($AgyCmdSrc, $Utf8NoBom)

foreach ($bDir in @($LocalAgycBin, $AgyBinDir)) {
    foreach ($pyName in @("agyc", "agyc-statusline", "agyc-topbar")) {
        $srcP = Join-Path $RepoDir "bin\$pyName"
        $dstP = Join-Path $bDir $pyName
        if (Test-Path -LiteralPath $srcP -PathType Leaf) {
            Copy-Item -LiteralPath $srcP -Destination $dstP -Force
        }
    }

    Write-CmdWrapper -Path (Join-Path $bDir "agyc.cmd") -Content (New-PyCmdWrapperContent -PythonExe $PythonExe -ScriptName "agyc")
    Write-CmdWrapper -Path (Join-Path $bDir "agy.cmd") -Content $AgyCmdContent
    Write-CmdWrapper -Path (Join-Path $bDir "agi.cmd") -Content "@echo off`nsetlocal`ncall `"%~dp0agy.cmd`" %*`nexit /b %ERRORLEVEL%`n"
    Write-CmdWrapper -Path (Join-Path $bDir "agyc-statusline.cmd") -Content (New-PyCmdWrapperContent -PythonExe $PythonExe -ScriptName "agyc-statusline" -ExtraFlags "-S")
    Write-CmdWrapper -Path (Join-Path $bDir "agyc-titleline.cmd") -Content (New-PyCmdWrapperContent -PythonExe $PythonExe -ScriptName "agyc-statusline" -ExtraFlags "-S" -InvokedAs "agyc-titleline")
    Write-CmdWrapper -Path (Join-Path $bDir "agyc-topbar.cmd") -Content (New-PyCmdWrapperContent -PythonExe $PythonExe -ScriptName "agyc-topbar" -ExtraFlags "-S")
    Write-Host "  -> $bDir\*.cmd" -ForegroundColor DarkGray
}

# Preconfigurar statusLine (agyc-statusline.cmd), title (agyc-titleline.cmd) y Herdr config.toml
$env:AGYC_INSTALL_REAL_HOME = $RealHome
$env:AGYC_INSTALL_APPDATA = $env:APPDATA
$settingsScript = @'
import glob, json, os, re

real_home = os.environ["AGYC_INSTALL_REAL_HOME"]
main_settings = os.path.join(real_home, ".gemini", "antigravity-cli", "settings.json")
os.makedirs(os.path.dirname(main_settings), exist_ok=True)
if not os.path.exists(main_settings):
    with open(main_settings, "w", encoding="utf-8") as f:
        f.write("{}\n")

configs = glob.glob(os.path.join(real_home, ".agyc_homes", "*", ".gemini", "antigravity-cli", "settings.json")) + [main_settings]
seen = set()
for p in configs:
    if not os.path.exists(p):
        continue
    rp = os.path.normcase(os.path.realpath(p))
    if rp in seen:
        continue
    seen.add(rp)
    try:
        with open(p, "r", encoding="utf-8") as f:
            d = json.load(f)
        if not isinstance(d, dict):
            d = {}
    except Exception:
        d = {}
    d["statusLine"] = {"type": "command", "command": "agyc-statusline.cmd", "enabled": True}
    d["title"] = {"type": "command", "command": "agyc-titleline.cmd", "enabled": True}
    tmp = f"{p}.tmp.{os.getpid()}"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)
    os.replace(tmp, p)

appdata = (os.environ.get("AGYC_INSTALL_APPDATA") or "").strip()
herdr_toml = os.path.join(appdata, "herdr", "config.toml") if appdata else os.path.join(real_home, "AppData", "Roaming", "herdr", "config.toml")
if os.path.isfile(herdr_toml):
    try:
        with open(herdr_toml, "r", encoding="utf-8", errors="ignore") as f:
            toml_txt = f.read()
        has_topbar = "agyc-topbar" in toml_txt
        has_borders = bool(re.search(r"(?m)^\s*show_agent_labels_on_pane_borders\s*=\s*true\b", toml_txt))
        has_toast = "[ui.toast]" in toml_txt
        if not has_topbar or not has_borders:
            new_txt = toml_txt
            if not has_borders:
                if re.search(r"(?m)^\s*show_agent_labels_on_pane_borders\s*=", new_txt):
                    new_txt = re.sub(r"(?m)^\s*show_agent_labels_on_pane_borders\s*=.*$", "show_agent_labels_on_pane_borders = true", new_txt, count=1)
                elif re.search(r"(?m)^\[ui\]\s*$", new_txt):
                    new_txt = re.sub(r"(?m)^(\[ui\]\s*)$", "\\1\nshow_agent_labels_on_pane_borders = true", new_txt, count=1)
                else:
                    if new_txt and not new_txt.endswith("\n"):
                        new_txt += "\n"
                    new_txt += '\n[ui]\nshow_agent_labels_on_pane_borders = true\ntab_bar_position = "top"\n'
            if not has_topbar:
                topbar_cmd = os.path.join(real_home, ".gemini", "antigravity-cli", "bin", "agyc-topbar.cmd")
                if new_txt and not new_txt.endswith("\n"):
                    new_txt += "\n"
                new_txt += (
                    "\n[[ui.tab_bar_right]]\n"
                    'type = "command"\n'
                    f"command = {json.dumps(topbar_cmd)}\n"
                    "interval_seconds = 10\n"
                    "timeout_seconds = 2\n"
                )
            if not has_toast:
                if new_txt and not new_txt.endswith("\n"):
                    new_txt += "\n"
                new_txt += '\n[ui.toast]\ndelivery = "herdr"\n'
            import tomllib
            tomllib.loads(new_txt)
            tmp_t = f"{herdr_toml}.tmp.{os.getpid()}"
            with open(tmp_t, "w", encoding="utf-8") as tf:
                tf.write(new_txt)
            os.replace(tmp_t, herdr_toml)
    except Exception:
        pass
'@
$env:AGYC_INLINE_PY = $settingsScript
Invoke-AgycPython -PyArgs @("-S", "-c", "import os; exec(os.environ['AGYC_INLINE_PY'])")
if ($LASTEXITCODE -ne 0) {
    Write-Host "X Error configurando settings.json" -ForegroundColor Red
    exit $LASTEXITCODE
}
Remove-Item Env:AGYC_INSTALL_REAL_HOME, Env:AGYC_INSTALL_APPDATA, Env:AGYC_INLINE_PY -ErrorAction SilentlyContinue

$HerdrExe = $null
foreach ($hc in @($env:HERDR_BIN_PATH, "herdr.exe", "herdr")) {
    if ([string]::IsNullOrWhiteSpace($hc)) { continue }
    if (Test-Path -LiteralPath $hc -PathType Leaf) { $HerdrExe = $hc; break }
    $cmdH = Get-Command $hc -ErrorAction SilentlyContinue
    if ($cmdH) { $HerdrExe = $cmdH.Source; break }
}
if ($HerdrExe) {
    try {
        & $HerdrExe server reload-config 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  -> Herdr config.toml recargado (herdr server reload-config)" -ForegroundColor DarkGray
        }
    } catch {
    }
}

Write-Host "OK Wrappers .cmd, librerias y hooks configurados" -ForegroundColor Green
Write-Host ""

# -- Paso 4: Crear lanzadores directos agy01.cmd..agy15.cmd y agi01.cmd..15.cmd
Write-Host "[4/7] Creando lanzadores directos agy01.cmd..agy15.cmd..." -ForegroundColor White

$LauncherAliases = New-Object System.Collections.Generic.HashSet[string]([System.StringComparer]::OrdinalIgnoreCase)
for ($i = 1; $i -le 15; $i++) {
    $num = $i.ToString("00")
    [void]$LauncherAliases.Add("agy$num")
    [void]$LauncherAliases.Add("agi$num")
}
Get-ChildItem -LiteralPath $AgyAccountsDir -Filter "*.json" -ErrorAction SilentlyContinue | ForEach-Object {
    if ($_.Name -ne "config.json") {
        [void]$LauncherAliases.Add($_.BaseName)
    }
}

foreach ($bDir in @($LocalAgycBin, $AgyBinDir)) {
    foreach ($al in $LauncherAliases) {
        Write-CmdWrapper -Path (Join-Path $bDir "$al.cmd") -Content (New-PyCmdWrapperContent -PythonExe $PythonExe -ScriptName "agyc" -InvokedAs $al)
    }
}
Write-Host "OK Lanzadores .cmd creados en $LocalAgycBin y $AgyBinDir" -ForegroundColor Green
Write-Host ""

# -- Paso 5: Configurar User PATH ---------------------------------------------
Write-Host "[5/7] Configurando User PATH..." -ForegroundColor White

if (-not $SkipPath) {
    $curUserPath = [Environment]::GetEnvironmentVariable("Path", "User")
    if ($null -eq $curUserPath) { $curUserPath = "" }
    $rawEntries = $curUserPath -split ";" | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
    $normLocalBin = $LocalAgycBin.TrimEnd("\").ToLowerInvariant()
    $normAgyExeBin = (Join-Path $LocalAppData "agy\bin").TrimEnd("\").ToLowerInvariant()

    $filtered = New-Object System.Collections.Generic.List[string]
    $seenEntries = New-Object System.Collections.Generic.HashSet[string]([System.StringComparer]::OrdinalIgnoreCase)
    foreach ($entry in $rawEntries) {
        $clean = $entry.Trim()
        $key = $clean.TrimEnd("\")
        if ($key -eq $normLocalBin) { continue }
        if ($seenEntries.Add($key)) {
            $filtered.Add($clean)
        }
    }

    # Colocar %LOCALAPPDATA%\agyc\bin al inicio para que agy.cmd preceda a agy\bin\agy.exe
    $newEntries = New-Object System.Collections.Generic.List[string]
    $newEntries.Add($LocalAgycBin)
    foreach ($e in $filtered) { $newEntries.Add($e) }
    $newUserPath = ($newEntries -join ";")
    [Environment]::SetEnvironmentVariable("Path", $newUserPath, "User")

    $envParts = $env:PATH -split ";" | Where-Object { $_.Trim().TrimEnd("\") -ine $LocalAgycBin.TrimEnd("\") }
    $env:PATH = ($LocalAgycBin + ";" + ($envParts -join ";"))
    Write-Host "  User PATH actualizado con: $LocalAgycBin" -ForegroundColor DarkGray
} else {
    Write-Host "  User PATH omitido (-SkipPath)" -ForegroundColor DarkGray
}

Write-Host "OK PATH configurado" -ForegroundColor Green
Write-Host ""

# -- Paso 6: Instalar skill de agente -----------------------------------------
Write-Host "[6/7] Instalando skill de agente..." -ForegroundColor White

$SkillSrc = Join-Path $RepoDir "skills\agyc\SKILL.md"
$SkillTargets = @(
    (Join-Path $RealHome "proyectos\.agents\skills"),
    (Join-Path $RealHome ".agents\skills")
)
$SkillInstalled = $false
if (Test-Path -LiteralPath $SkillSrc -PathType Leaf) {
    foreach ($sRoot in $SkillTargets) {
        if (Test-Path -LiteralPath $sRoot -PathType Container) {
            $sDstDir = Join-Path $sRoot "agyc"
            New-Item -ItemType Directory -Path $sDstDir -Force | Out-Null
            Copy-Item -LiteralPath $SkillSrc -Destination (Join-Path $sDstDir "SKILL.md") -Force
            Write-Host "  -> $sDstDir\SKILL.md" -ForegroundColor DarkGray
            $SkillInstalled = $true
        }
    }
}
if ($SkillInstalled) {
    Write-Host "OK Skill instalado" -ForegroundColor Green
} else {
    Write-Host "! Directorio .agents\skills no encontrado. Skill omitido." -ForegroundColor Yellow
}
Write-Host ""

# -- Paso 7: Verificacion final -----------------------------------------------
Write-Host "[7/7] Verificacion final..." -ForegroundColor White

$env:PYTHONDONTWRITEBYTECODE = "1"
$FilesToCompile = @(
    (Join-Path $RepoDir "lib\__init__.py"),
    (Join-Path $RepoDir "lib\agyc_core.py"),
    (Join-Path $RepoDir "lib\platform\__init__.py"),
    (Join-Path $RepoDir "lib\platform\linux.py"),
    (Join-Path $RepoDir "lib\platform\win32.py"),
    (Join-Path $LocalAgycBin "agyc"),
    (Join-Path $LocalAgycBin "agyc-statusline"),
    (Join-Path $LocalAgycBin "agyc-topbar")
)
foreach ($fc in $FilesToCompile) {
    if (Test-Path -LiteralPath $fc -PathType Leaf) {
        Invoke-AgycPython -PyArgs @("-m", "py_compile", $fc)
        if ($LASTEXITCODE -ne 0) {
            Write-Host "X Error de sintaxis en $fc" -ForegroundColor Red
            exit $LASTEXITCODE
        }
    }
}
Write-Host "  OK Sintaxis Python verificada (lib/ + bin/)" -ForegroundColor Green

if (-not $SkipTests -and (Test-Path -LiteralPath (Join-Path $RepoDir "tests\test_agyc.py"))) {
    Invoke-AgycPython -PyArgs @("-m", "unittest", "discover", "-s", (Join-Path $RepoDir "tests"))
    if ($LASTEXITCODE -ne 0) {
        Write-Host "X Fallo la suite de tests unitarios" -ForegroundColor Red
        exit $LASTEXITCODE
    }
    Write-Host "  OK Suite de tests unitarios superada (tests/)" -ForegroundColor Green
}

Write-Host ""
Write-Host "========================================================" -ForegroundColor Green
Write-Host "        agyc v1.6 instalado correctamente               " -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Proximos pasos:" -ForegroundColor White
Write-Host "  1. Abre una nueva terminal para cargar el User PATH actualizado"
Write-Host "  2. Registra tu cuenta Google AI Pro / Ultra:  agyc add"
Write-Host "  3. Entra a Antigravity con tu cuenta:         agy01"
Write-Host "  4. Revisa el estado de todas tus cuentas:     agyc"
Write-Host "  5. Si usas Herdr y la barra/bordes no aparecen aun: herdr server reload-config (o cierra y vuelve a abrir la ventana de Herdr)"
Write-Host ""
