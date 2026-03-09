param(
    [string]$ProjectRoot = $env:CI_PROJECT_DIR,
    [string]$E2Studio = $env:E2STUDIO,
    [string]$Workspace = $env:PHASE8B_WORKSPACE,
    [string]$Phase8bProjectsPath = $(if ($env:PHASE8B_E2STUDIO_PROJECTS) { $env:PHASE8B_E2STUDIO_PROJECTS } else { "phase8b\\Projects" }),
    [string]$LogFile = $(if ($env:CI_PROJECT_DIR) { Join-Path $env:CI_PROJECT_DIR "phase8b_e2studio_build.log" } else { Join-Path (Get-Location) "phase8b_e2studio_build.log" })
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
$phase8bProjectsPath = $Phase8bProjectsPath -replace "/", "\"
$logFile = [System.IO.Path]::GetFullPath($LogFile)
$shortRoot = "C:\rx72n-phase8b-src"
$projectNames = @(
    "boot_loader_rx72n_envision_kit",
    "aws_ether_rx72n_envision_kit"
)
$rcpcSnapshots = @{}

if (Test-Path $workspace) {
    Remove-Item -Recurse -Force $workspace
}

foreach ($projectName in $projectNames) {
    $hardwareDebug = Join-Path $projectRoot "$phase8bProjectsPath\$projectName\e2studio_ccrx\HardwareDebug"
    if (Test-Path $hardwareDebug) {
        Remove-Item -Recurse -Force $hardwareDebug
        Write-Host "Cleared: $hardwareDebug"
    }

    $rcpcPath = Join-Path $projectRoot "$phase8bProjectsPath\$projectName\e2studio_ccrx\$projectName.rcpc"
    if (Test-Path $rcpcPath) {
        $rcpcSnapshots[$rcpcPath] = Get-Content $rcpcPath -Raw
    }
}

if (Test-Path $shortRoot) {
    cmd /c "rmdir `"$shortRoot`"" 2>$null
}

New-Item -ItemType Junction -Path $shortRoot -Target $projectRoot | Out-Null
Write-Host "Junction: $shortRoot -> $projectRoot"

$imports = @()
foreach ($projectName in $projectNames) {
    $imports += @("-import", (Join-Path $shortRoot "$phase8bProjectsPath\$projectName\e2studio_ccrx"))
}

$e2base = @(
    "--launcher.suppressErrors",
    "-nosplash",
    "-application", "org.eclipse.cdt.managedbuilder.core.headlessbuild",
    "-data", $workspace
)

Write-Host "=== Phase 8b import + cleanBuild all ==="
Write-Host "Workspace: $workspace"
Write-Host "Log file:  $logFile"
foreach ($projectName in $projectNames) {
    Write-Host "Import:    $(Join-Path $shortRoot "$phase8bProjectsPath\$projectName\e2studio_ccrx")"
}

function Find-Artifacts {
    param(
        [string]$RelativePattern
    )

    $primary = Join-Path $projectRoot $RelativePattern
    $short = Join-Path $shortRoot $RelativePattern

    $items = Get-ChildItem $primary -ErrorAction SilentlyContinue
    if ($items) {
        return $items
    }

    return Get-ChildItem $short -ErrorAction SilentlyContinue
}

try {
    & $E2Studio @e2base @imports -cleanBuild all 2>&1 | Tee-Object -FilePath $logFile | Out-Null
    $e2exit = $LASTEXITCODE

    Write-Host "e2studio exit code: $e2exit"
    Write-Host "--- Build log tail ---"
    Get-Content $logFile -Tail 30 -ErrorAction SilentlyContinue | ForEach-Object { Write-Host "  $_" }

    $bootMot = Find-Artifacts "$phase8bProjectsPath\boot_loader_rx72n_envision_kit\e2studio_ccrx\HardwareDebug\*.mot"
    $appMot = Find-Artifacts "$phase8bProjectsPath\aws_ether_rx72n_envision_kit\e2studio_ccrx\HardwareDebug\*.mot"
    $appAbs = Find-Artifacts "$phase8bProjectsPath\aws_ether_rx72n_envision_kit\e2studio_ccrx\HardwareDebug\*.abs"
    $appX = Find-Artifacts "$phase8bProjectsPath\aws_ether_rx72n_envision_kit\e2studio_ccrx\HardwareDebug\*.x"

    Write-Host ""
    Write-Host "--- Phase 8b artifact search ---"
    Write-Host "  boot_loader .mot: $(if ($bootMot) { $bootMot.FullName } else { 'NOT FOUND' })"
    Write-Host "  aws_ether   .mot: $(if ($appMot) { $appMot.FullName } else { 'NOT FOUND' })"
    Write-Host "  aws_ether   .abs: $(if ($appAbs) { $appAbs.FullName } else { 'NOT FOUND' })"
    Write-Host "  aws_ether     .x: $(if ($appX) { $appX.FullName } else { 'NOT FOUND' })"

    $missing = @()
    if (-not $bootMot) { $missing += "boot_loader_rx72n_envision_kit .mot" }
    if (-not $appMot) { $missing += "aws_ether_rx72n_envision_kit .mot" }
    if (-not $appAbs) { $missing += "aws_ether_rx72n_envision_kit .abs" }
    if (-not $appX) { $missing += "aws_ether_rx72n_envision_kit .x" }

    if ($e2exit -ne 0) {
        throw "e2studio failed with exit code $e2exit. See $logFile"
    }

    if ($missing.Count -gt 0) {
        throw "Phase 8b build artifacts missing: $($missing -join ', ')"
    }

    Write-Host ""
    Write-Host "Phase 8b headless build succeeded."
}
finally {
    foreach ($rcpcPath in $rcpcSnapshots.Keys) {
        [System.IO.File]::WriteAllText($rcpcPath, $rcpcSnapshots[$rcpcPath], [System.Text.UTF8Encoding]::new($false))
    }

    if (Test-Path $shortRoot) {
        cmd /c "rmdir `"$shortRoot`"" 2>$null
    }
}
