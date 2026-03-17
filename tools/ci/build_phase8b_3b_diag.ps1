param(
    [string]$ProjectRoot = $env:CI_PROJECT_DIR,
    [string]$E2Studio = $env:E2STUDIO,
    [string]$Workspace = $(if ($env:PHASE8B_3B_WORKSPACE) { $env:PHASE8B_3B_WORKSPACE } else { "C:\workspace_rx72n_phase8b_3b" }),
    [string]$LegacyProjectsPath = $(if ($env:E2STUDIO_PROJECTS) { $env:E2STUDIO_PROJECTS } else { "projects\renesas\rx72n_envision_kit\e2studio" }),
    [string]$Phase8bProjectsPath = $(if ($env:PHASE8B_E2STUDIO_PROJECTS) { $env:PHASE8B_E2STUDIO_PROJECTS } else { "phase8b\Projects" }),
    [string]$LogFile = $(if ($env:CI_PROJECT_DIR) { Join-Path $env:CI_PROJECT_DIR "phase8b_3b_e2studio_build.log" } else { Join-Path (Get-Location) "phase8b_3b_e2studio_build.log" })
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if (-not $ProjectRoot) {
    throw "ProjectRoot is required."
}

if (-not $E2Studio) {
    throw "E2Studio is required."
}

if (-not (Test-Path $E2Studio)) {
    throw "e2studio executable not found: $E2Studio"
}

$projectRoot = (Resolve-Path $ProjectRoot).Path
$workspace = $Workspace
$legacyProjectsPath = $LegacyProjectsPath -replace "/", "\"
$phase8bProjectsPath = $Phase8bProjectsPath -replace "/", "\"
$logFile = [System.IO.Path]::GetFullPath($LogFile)
$shortRoot = "C:\rx72n-phase8b-3b-src"
$skipClockSetup = if ($env:PHASE8B_3B_SKIP_MCU_CLOCK_SETUP) { $env:PHASE8B_3B_SKIP_MCU_CLOCK_SETUP -eq "true" } else { $false }
$forceSoftwareResetHandoff = if ($env:PHASE8B_3B_FORCE_SOFTWARE_RESET_HANDOFF) { $env:PHASE8B_3B_FORCE_SOFTWARE_RESET_HANDOFF -eq "true" } else { $false }
$appBspConfigPath = Join-Path $projectRoot "$phase8bProjectsPath\aws_ether_rx72n_envision_kit\e2studio_ccrx\src\smc_gen\r_config\r_bsp_config.h"
$legacyBootBspConfigPath = Join-Path $projectRoot "$legacyProjectsPath\boot_loader\src\smc_gen\r_config\r_bsp_config.h"
$projectDefinitions = @(
    @{
        Name = "rx72n_boot_loader"
        ImportPath = "$legacyProjectsPath\boot_loader"
        HardwareDebug = "$legacyProjectsPath\boot_loader\HardwareDebug"
    },
    @{
        Name = "boot_loader_rx72n_envision_kit"
        ImportPath = "$phase8bProjectsPath\boot_loader_rx72n_envision_kit\e2studio_ccrx"
        HardwareDebug = "$phase8bProjectsPath\boot_loader_rx72n_envision_kit\e2studio_ccrx\HardwareDebug"
        RcpcPath = "$phase8bProjectsPath\boot_loader_rx72n_envision_kit\e2studio_ccrx\boot_loader_rx72n_envision_kit.rcpc"
    },
    @{
        Name = "aws_ether_rx72n_envision_kit"
        ImportPath = "$phase8bProjectsPath\aws_ether_rx72n_envision_kit\e2studio_ccrx"
        HardwareDebug = "$phase8bProjectsPath\aws_ether_rx72n_envision_kit\e2studio_ccrx\HardwareDebug"
        RcpcPath = "$phase8bProjectsPath\aws_ether_rx72n_envision_kit\e2studio_ccrx\aws_ether_rx72n_envision_kit.rcpc"
    }
)
$rcpcSnapshots = @{}
$fileSnapshots = @{}

if (Test-Path $workspace) {
    Remove-Item -Recurse -Force $workspace
}

if (-not (Test-Path $appBspConfigPath)) {
    throw "phase8b app BSP config not found: $appBspConfigPath"
}

$fileSnapshots[$legacyBootBspConfigPath] = Get-Content $legacyBootBspConfigPath -Raw
$fileSnapshots[$appBspConfigPath] = Get-Content $appBspConfigPath -Raw

$desiredAppSkipFlag = if ($skipClockSetup) { '(1)' } else { '(0)' }
if ($fileSnapshots[$appBspConfigPath] -notmatch '#define BSP_CFG_PHASE8B_3B_SKIP_MCU_CLOCK_SETUP\s+\([01]\)') {
    throw "BSP_CFG_PHASE8B_3B_SKIP_MCU_CLOCK_SETUP macro not found in $appBspConfigPath"
}
$appBspConfig = $fileSnapshots[$appBspConfigPath] -replace `
    '#define BSP_CFG_PHASE8B_3B_SKIP_MCU_CLOCK_SETUP\s+\([01]\)', `
    "#define BSP_CFG_PHASE8B_3B_SKIP_MCU_CLOCK_SETUP   $desiredAppSkipFlag"

[System.IO.File]::WriteAllText($appBspConfigPath, $appBspConfig, [System.Text.UTF8Encoding]::new($false))
Write-Host "Set 3b diag clock-setup bypass=$skipClockSetup : $appBspConfigPath"

$desiredBootHandoffFlag = if ($forceSoftwareResetHandoff) { '(1)' } else { '(0)' }
if ($fileSnapshots[$legacyBootBspConfigPath] -notmatch '#define BSP_CFG_BOOT_LOADER_SOFTWARE_RESET_HANDOFF\s+\([01]\)') {
    throw "BSP_CFG_BOOT_LOADER_SOFTWARE_RESET_HANDOFF macro not found in $legacyBootBspConfigPath"
}
$legacyBootBspConfig = $fileSnapshots[$legacyBootBspConfigPath] -replace `
    '#define BSP_CFG_BOOT_LOADER_SOFTWARE_RESET_HANDOFF\s+\([01]\)', `
    "#define BSP_CFG_BOOT_LOADER_SOFTWARE_RESET_HANDOFF   $desiredBootHandoffFlag"

[System.IO.File]::WriteAllText($legacyBootBspConfigPath, $legacyBootBspConfig, [System.Text.UTF8Encoding]::new($false))
Write-Host "Set 3b diag software-reset handoff=$forceSoftwareResetHandoff : $legacyBootBspConfigPath"

foreach ($project in $projectDefinitions) {
    $hardwareDebug = Join-Path $projectRoot $project.HardwareDebug
    if (Test-Path $hardwareDebug) {
        Remove-Item -Recurse -Force $hardwareDebug
        Write-Host "Cleared: $hardwareDebug"
    }

    if ($project.ContainsKey("RcpcPath")) {
        $rcpcPath = Join-Path $projectRoot $project.RcpcPath
        if (Test-Path $rcpcPath) {
            $rcpcSnapshots[$rcpcPath] = Get-Content $rcpcPath -Raw
        }
    }
}

if (Test-Path $shortRoot) {
    cmd /c "rmdir `"$shortRoot`"" 2>$null
}

New-Item -ItemType Junction -Path $shortRoot -Target $projectRoot | Out-Null
Write-Host "Junction: $shortRoot -> $projectRoot"

$imports = @()
foreach ($project in $projectDefinitions) {
    $imports += @("-import", (Join-Path $shortRoot $project.ImportPath))
}

$e2base = @(
    "--launcher.suppressErrors",
    "-nosplash",
    "-application", "org.eclipse.cdt.managedbuilder.core.headlessbuild",
    "-data", $workspace
)

Write-Host "=== Phase 8b 3b import + cleanBuild all ==="
Write-Host "Workspace: $workspace"
Write-Host "Log file:  $logFile"
foreach ($project in $projectDefinitions) {
    Write-Host "Import:    $(Join-Path $shortRoot $project.ImportPath)"
}

function Find-Artifacts {
    param(
        [string[]]$Patterns
    )

    foreach ($base in @($projectRoot, $shortRoot, $workspace)) {
        foreach ($pattern in $Patterns) {
            $candidate = Join-Path $base $pattern
            $items = Get-ChildItem $candidate -ErrorAction SilentlyContinue
            if ($items) {
                return $items
            }
        }
    }

    return @()
}

try {
    & $E2Studio @e2base @imports -cleanBuild all 2>&1 | Tee-Object -FilePath $logFile | Out-Null
    $e2exit = $LASTEXITCODE

    Write-Host "e2studio exit code: $e2exit"
    Write-Host "--- Build log tail ---"
    Get-Content $logFile -Tail 30 -ErrorAction SilentlyContinue | ForEach-Object { Write-Host "  $_" }

    $bootMot = Find-Artifacts @(
        "$legacyProjectsPath\boot_loader\HardwareDebug\*.mot",
        "rx72n_boot_loader\HardwareDebug\*.mot",
        "rx72n_boot\HardwareDebug\*.mot"
    )
    $appMot = Find-Artifacts @(
        "$phase8bProjectsPath\aws_ether_rx72n_envision_kit\e2studio_ccrx\HardwareDebug\*.mot",
        "aws_ether_rx72n_envision_kit\HardwareDebug\*.mot"
    )
    $appAbs = Find-Artifacts @(
        "$phase8bProjectsPath\aws_ether_rx72n_envision_kit\e2studio_ccrx\HardwareDebug\*.abs",
        "aws_ether_rx72n_envision_kit\HardwareDebug\*.abs"
    )
    $appX = Find-Artifacts @(
        "$phase8bProjectsPath\aws_ether_rx72n_envision_kit\e2studio_ccrx\HardwareDebug\*.x",
        "aws_ether_rx72n_envision_kit\HardwareDebug\*.x"
    )

    Write-Host ""
    Write-Host "--- Phase 8b 3b artifact search ---"
    Write-Host "  legacy boot_loader .mot: $(if ($bootMot) { $bootMot.FullName } else { 'NOT FOUND' })"
    Write-Host "  phase8b app      .mot: $(if ($appMot) { $appMot.FullName } else { 'NOT FOUND' })"
    Write-Host "  phase8b app      .abs: $(if ($appAbs) { $appAbs.FullName } else { 'NOT FOUND' })"
    Write-Host "  phase8b app        .x: $(if ($appX) { $appX.FullName } else { 'NOT FOUND' })"

    $missing = @()
    if (-not $bootMot) { $missing += "legacy boot_loader .mot" }
    if (-not $appMot) { $missing += "phase8b app .mot" }
    if (-not $appAbs) { $missing += "phase8b app .abs" }
    if (-not $appX) { $missing += "phase8b app .x" }

    if ($e2exit -ne 0) {
        throw "e2studio failed with exit code $e2exit. See $logFile"
    }

    if ($missing.Count -gt 0) {
        throw "Phase 8b 3b build artifacts missing: $($missing -join ', ')"
    }

    Write-Host ""
    Write-Host "Phase 8b 3b headless build succeeded."
}
finally {
    foreach ($filePath in $fileSnapshots.Keys) {
        [System.IO.File]::WriteAllText($filePath, $fileSnapshots[$filePath], [System.Text.UTF8Encoding]::new($false))
    }

    foreach ($rcpcPath in $rcpcSnapshots.Keys) {
        [System.IO.File]::WriteAllText($rcpcPath, $rcpcSnapshots[$rcpcPath], [System.Text.UTF8Encoding]::new($false))
    }

    if (Test-Path $shortRoot) {
        cmd /c "rmdir `"$shortRoot`"" 2>$null
    }
}
