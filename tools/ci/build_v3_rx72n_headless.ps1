param(
    [string]$ProjectRoot = $(Split-Path (Split-Path $PSScriptRoot -Parent) -Parent),
    [string]$E2Studio = "C:\Renesas\e2_studio_2025_12\eclipse\e2studioc.exe",
    [string]$Workspace = "C:\rx72n-v3-ws",
    [string]$ProjectsPath = "Projects",
    [string]$LogFile = $(Join-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) "rx72n_v3_e2studio_build.log"),
    [string]$SigningKey = "sample_keys/secp256r1.privatekey",
    [string]$BoardAppTasks = $env:RX72N_BOARD_APP_TASKS,
    [switch]$SkipRsu
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if (-not (Test-Path $E2Studio)) {
    throw "e2studio executable not found: $E2Studio"
}

$projectRoot = (Resolve-Path $ProjectRoot).Path
$workspace = $Workspace
$projectsPath = $ProjectsPath -replace "/", "\"
$logFile = [System.IO.Path]::GetFullPath($LogFile)
$projectNames = @(
    "boot_loader_rx72n_envision_kit",
    "aws_ether_rx72n_envision_kit"
)
$rcpcSnapshots = @{}
$cprojectSnapshots = @{}

if (-not (Test-Path (Join-Path $projectRoot "Middleware\FreeRTOS\FreeRTOS-Kernel\include\FreeRTOS.h"))) {
    throw "Git submodules not initialized. Run: git submodule update --init --recursive"
}

if (-not (Test-Path (Join-Path $projectRoot "Middleware\FreeRTOS\corePKCS11\source\dependency\3rdparty\pkcs11\published\2-40-errata-1\pkcs11.h"))) {
    throw "Git submodules not initialized recursively. Missing corePKCS11 pkcs11.h."
}

if (Test-Path $workspace) {
    Remove-Item -Recurse -Force $workspace
}

foreach ($projectName in $projectNames) {
    $hardwareDebug = Join-Path $projectRoot "$projectsPath\$projectName\e2studio_ccrx\HardwareDebug"
    if (Test-Path $hardwareDebug) {
        Remove-Item -Recurse -Force $hardwareDebug
        Write-Host "Cleared: $hardwareDebug"
    }

    $projectDir = Join-Path $projectRoot "$projectsPath\$projectName\e2studio_ccrx"
    $preferredRcpc = Join-Path $projectDir "$projectName.rcpc"
    if (Test-Path $preferredRcpc) {
        $rcpcPath = Get-Item $preferredRcpc
    } else {
        $rcpcPath = Get-ChildItem -Path $projectDir -Filter '*.rcpc' -File -ErrorAction SilentlyContinue | Select-Object -First 1
    }
    if ($rcpcPath) {
        $rcpcSnapshots[$rcpcPath.FullName] = Get-Content $rcpcPath.FullName -Raw
    }

    $cprojectPath = Join-Path $projectDir ".cproject"
    if (Test-Path $cprojectPath) {
        $cprojectSnapshots[[System.IO.Path]::GetFullPath($cprojectPath)] = Get-Content $cprojectPath -Raw
    }
}

$imports = @()
foreach ($projectName in $projectNames) {
    $imports += @("-import", (Join-Path $projectRoot "$projectsPath\$projectName\e2studio_ccrx"))
}

$e2base = @(
    "--launcher.suppressErrors",
    "-nosplash",
    "-application", "org.eclipse.cdt.managedbuilder.core.headlessbuild",
    "-data", $workspace
)

Write-Host "=== RX72N v3 (iot-reference-rx canonical) import + build all ==="
Write-Host "Project root: $projectRoot"
Write-Host "Workspace:    $workspace"
Write-Host "Log file:     $logFile"
foreach ($projectName in $projectNames) {
    Write-Host "Import:       $(Join-Path $projectRoot "$projectsPath\$projectName\e2studio_ccrx")"
}

function Find-Artifacts {
    param(
        [string]$RelativePattern
    )

    $primary = Join-Path $projectRoot $RelativePattern
    $items = Get-ChildItem $primary -ErrorAction SilentlyContinue
    if ($items) {
        return $items
    }
}

function Get-BoardAppDefines {
    param(
        [string]$TaskList
    )

    $defines = @()
    if ([string]::IsNullOrWhiteSpace($TaskList)) {
        $TaskList = "none"
    }

    foreach ($rawToken in ($TaskList -split '[,; ]+')) {
        $token = $rawToken.Trim().ToLowerInvariant()
        if ([string]::IsNullOrWhiteSpace($token)) {
            continue
        }

        switch ($token) {
            { $_ -in @("none", "off", "false", "0") } { break }
            "all"          { $defines += "appmainENABLE_BOARD_APPLICATION_TASKS=1"; break }
            "gui"          { $defines += "appmainENABLE_BOARD_GUI_TASK=1"; break }
            "gui_stub"     { $defines += "appmainENABLE_BOARD_GUI_TASK=1"; $defines += "appmainENABLE_BOARD_GUI_STUB_TASK=1"; break }
            "gui_init_only" { $defines += "appmainENABLE_BOARD_GUI_TASK=1"; $defines += "appmainENABLE_BOARD_GUI_INIT_ONLY_TASK=1"; break }
            "no_trace"     { $defines += "appmainENABLE_TRACEALYZER=0"; break }
            { $_ -in @("no_tcp_perf", "no_tcpperf") } { $defines += "appmainENABLE_TCP_PERF_TASKS=0"; break }
            { $_ -in @("sd", "sdcard", "sd_card") } { $defines += "appmainENABLE_BOARD_SDCARD_TASK=1"; break }
            { $_ -in @("serial", "serial_flash", "qspi") } { $defines += "appmainENABLE_BOARD_SERIAL_FLASH_TASK=1"; break }
            "audio"        { $defines += "appmainENABLE_BOARD_AUDIO_TASK=1"; break }
            default        { throw "Unknown RX72N_BOARD_APP_TASKS token '$rawToken'. Use none, all, gui, gui_stub, gui_init_only, no_trace, no_tcp_perf, sdcard, serial_flash, audio." }
        }
    }

    return @($defines | Select-Object -Unique)
}

function Add-CcrxCompilerDefines {
    param(
        [string]$CProjectPath,
        [string[]]$Defines
    )

    if (($null -eq $Defines) -or ($Defines.Count -eq 0)) {
        return
    }

    if (-not (Test-Path $CProjectPath)) {
        throw ".cproject not found: $CProjectPath"
    }

    [xml]$xml = Get-Content $CProjectPath -Raw
    $option = $xml.SelectSingleNode("//option[@superClass='com.renesas.cdt.managedbuild.renesas.ccrx.compiler.option.define']")
    if ($null -eq $option) {
        throw "CCRX compiler define option not found in $CProjectPath"
    }

    $existing = @{}
    foreach ($node in $option.SelectNodes("listOptionValue")) {
        $existing[$node.value] = $true
    }

    foreach ($define in $Defines) {
        if ($existing.ContainsKey($define)) {
            continue
        }

        $child = $xml.CreateElement("listOptionValue")
        $null = $child.SetAttribute("builtIn", "false")
        $null = $child.SetAttribute("value", $define)
        $null = $option.AppendChild($child)
    }

    $settings = [System.Xml.XmlWriterSettings]::new()
    $settings.Encoding = [System.Text.UTF8Encoding]::new($false)
    $settings.Indent = $true
    $writer = [System.Xml.XmlWriter]::Create($CProjectPath, $settings)
    try {
        $xml.Save($writer)
    } finally {
        $writer.Close()
    }
}

$boardAppDefines = @(Get-BoardAppDefines -TaskList $BoardAppTasks)
$boardAppTasksLabel = if ([string]::IsNullOrWhiteSpace($BoardAppTasks)) { "none" } else { $BoardAppTasks }
Write-Host "Board tasks:  $boardAppTasksLabel"
if ($boardAppDefines.Count -gt 0) {
    Write-Host "Board defines: $($boardAppDefines -join ', ')"
}

$postgenPatch = Join-Path $PSScriptRoot "sc_postgen_patch.py"
if (Test-Path $postgenPatch) {
    Write-Host "=== sc_postgen_patch (BSP_CFG_MCU_PART_* string -> integer) ==="
    & python $postgenPatch
    if ($LASTEXITCODE -ne 0) {
        throw "sc_postgen_patch.py failed with exit code $LASTEXITCODE"
    }
}

try {
    $appCProject = Join-Path $projectRoot "$projectsPath\aws_ether_rx72n_envision_kit\e2studio_ccrx\.cproject"
    Add-CcrxCompilerDefines -CProjectPath $appCProject -Defines $boardAppDefines

    & $E2Studio @e2base @imports -build all 2>&1 | Tee-Object -FilePath $logFile | Out-Null
    $e2exit = $LASTEXITCODE

    Write-Host "e2studio exit code: $e2exit"
    $logLines = Get-Content $logFile -ErrorAction SilentlyContinue
    $logLineCount = if ($logLines) { $logLines.Count } else { 0 }
    Write-Host "Build log: $logLineCount lines"

    if ($e2exit -ne 0) {
        Write-Host "--- Build log (first 100 lines) ---"
        $logLines | Select-Object -First 100 | ForEach-Object { Write-Host "  $_" }
        Write-Host "--- Build log (error lines) ---"
        $logLines | Where-Object { $_ -match '(?i)(error|fatal|cannot|failed|undefined)' } | Select-Object -First 50 | ForEach-Object { Write-Host "  $_" }
    }
    Write-Host "--- Build log tail ---"
    Get-Content $logFile -Tail 30 -ErrorAction SilentlyContinue | ForEach-Object { Write-Host "  $_" }

    $bootMot = Find-Artifacts "$projectsPath\boot_loader_rx72n_envision_kit\e2studio_ccrx\HardwareDebug\*.mot"
    $appMot = Find-Artifacts "$projectsPath\aws_ether_rx72n_envision_kit\e2studio_ccrx\HardwareDebug\*.mot"
    $appAbs = Find-Artifacts "$projectsPath\aws_ether_rx72n_envision_kit\e2studio_ccrx\HardwareDebug\*.abs"
    $appX = Find-Artifacts "$projectsPath\aws_ether_rx72n_envision_kit\e2studio_ccrx\HardwareDebug\*.x"
    $appMap = Find-Artifacts "$projectsPath\aws_ether_rx72n_envision_kit\e2studio_ccrx\HardwareDebug\*.map"

    Write-Host ""
    Write-Host "--- RX72N v3 artifact search ---"
    Write-Host "  boot_loader .mot: $(if ($bootMot) { $bootMot.FullName } else { 'NOT FOUND' })"
    Write-Host "  aws_ether   .mot: $(if ($appMot) { $appMot.FullName } else { 'NOT FOUND' })"
    Write-Host "  aws_ether   .abs: $(if ($appAbs) { $appAbs.FullName } else { 'NOT FOUND' })"
    Write-Host "  aws_ether     .x: $(if ($appX) { $appX.FullName } else { 'NOT FOUND' })"
    Write-Host "  aws_ether   .map: $(if ($appMap) { $appMap.FullName } else { 'NOT FOUND' })"

    Write-Host ""
    Write-Host "--- RX72N v3 artifact sizes ---"
    foreach ($artifactSet in @($bootMot, $appMot, $appAbs, $appX, $appMap)) {
        if ($artifactSet) {
            foreach ($artifact in @($artifactSet)) {
                Write-Host ("  {0}: {1:N0} bytes" -f $artifact.Name, $artifact.Length)
            }
        }
    }

    $missing = @()
    if (-not $bootMot) { $missing += "boot_loader_rx72n_envision_kit .mot" }
    if (-not $appMot) { $missing += "aws_ether_rx72n_envision_kit .mot" }
    if (-not $appAbs) { $missing += "aws_ether_rx72n_envision_kit .abs" }
    if (-not $appX) { $missing += "aws_ether_rx72n_envision_kit .x" }

    if ($e2exit -ne 0) {
        throw "e2studio failed with exit code $e2exit. See $logFile"
    }

    if ($missing.Count -gt 0) {
        throw "RX72N v3 build artifacts missing: $($missing -join ', ')"
    }

    Write-Host ""
    Write-Host "RX72N v3 headless build succeeded."

    if ($SkipRsu) {
        Write-Host "[INFO] -SkipRsu specified; skipping bank1 shift / RSU generation / signer cert."
        return
    }

    # --- Stage 2 additions: bank1 boot_loader mot + rx72n_app.rsu + signer cert ---
    $pythonExe = "python"
    $toolsV3   = Join-Path $projectRoot "tools\v3"
    $bootDbg   = Join-Path $projectRoot "$projectsPath\boot_loader_rx72n_envision_kit\e2studio_ccrx\HardwareDebug"
    $appDbg    = Join-Path $projectRoot "$projectsPath\aws_ether_rx72n_envision_kit\e2studio_ccrx\HardwareDebug"
    $bank0Mot  = Join-Path $bootDbg "boot_loader_rx72n_envision_kit.mot"
    $bank1Mot  = Join-Path $bootDbg "boot_loader_rx72n_envision_kit_bank1.mot"
    $appMotPath = Join-Path $appDbg "aws_ether_rx72n_envision_kit.mot"
    $prmCsv    = Join-Path $projectRoot "$projectsPath\aws_ether_rx72n_envision_kit\e2studio_ccrx\src\smc_gen\r_fwup\tool\RX72N_DualBank_ImageGenerator_PRM.csv"
    $signKey   = Join-Path $projectRoot $SigningKey
    $rsuOut    = Join-Path $projectRoot "rx72n_app.rsu"
    $certOut   = Join-Path $projectRoot "rx72n_codesign_cert.pem"

    Write-Host ""
    Write-Host "=== Generate bank1 boot_loader .mot (shift -0x200000) ==="
    & $pythonExe (Join-Path $toolsV3 "shift_srec_addresses.py") `
        --input $bank0Mot `
        --output $bank1Mot `
        --range-start 0xFFE00000 `
        --range-end 0xFFFFFFFF `
        --shift -0x200000 `
        --drop-out-of-range
    if ($LASTEXITCODE -ne 0) { throw "shift_srec_addresses.py exit $LASTEXITCODE" }
    if (-not (Test-Path $bank1Mot)) { throw "bank1 .mot missing: $bank1Mot" }
    Write-Host "OK: $bank1Mot"

    Write-Host ""
    Write-Host "=== Build rx72n_app.rsu (RELFWV2) ==="
    if (-not (Test-Path $prmCsv))   { throw "PRM CSV missing: $prmCsv" }
    if (-not (Test-Path $signKey))  { throw "Signing key missing: $signKey" }
    & $pythonExe (Join-Path $toolsV3 "build_fwup_v2_rsu.py") `
        --mot $appMotPath `
        --prm $prmCsv `
        --key $signKey `
        --output $rsuOut
    if ($LASTEXITCODE -ne 0) { throw "build_fwup_v2_rsu.py exit $LASTEXITCODE" }
    if (-not (Test-Path $rsuOut)) { throw "rx72n_app.rsu missing: $rsuOut" }
    Write-Host "OK: $rsuOut ($((Get-Item $rsuOut).Length) bytes)"

    Write-Host ""
    Write-Host "=== Generate code signer cert (public key) ==="
    & $pythonExe (Join-Path $toolsV3 "generate_signer_cert.py") `
        --key $signKey `
        --out $certOut
    if ($LASTEXITCODE -ne 0) { throw "generate_signer_cert.py exit $LASTEXITCODE" }
    if (-not (Test-Path $certOut)) { throw "rx72n_codesign_cert.pem missing: $certOut" }
    Write-Host "OK: $certOut"

    Write-Host ""
    Write-Host "RX72N v3 full build (bank1 + RSU + signer cert) succeeded."
}
finally {
    foreach ($rcpcPath in $rcpcSnapshots.Keys) {
        [System.IO.File]::WriteAllText($rcpcPath, $rcpcSnapshots[$rcpcPath], [System.Text.UTF8Encoding]::new($false))
    }
    foreach ($cprojectPath in $cprojectSnapshots.Keys) {
        [System.IO.File]::WriteAllText($cprojectPath, $cprojectSnapshots[$cprojectPath], [System.Text.UTF8Encoding]::new($false))
    }
}
