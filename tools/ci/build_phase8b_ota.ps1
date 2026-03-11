param(
    [string]$ProjectRoot = $env:CI_PROJECT_DIR,
    [string]$E2Studio = $env:E2STUDIO,
    [string]$Workspace = $env:PHASE8B_WORKSPACE,
    [string]$Phase8bProjectsPath = $(if ($env:PHASE8B_E2STUDIO_PROJECTS) { $env:PHASE8B_E2STUDIO_PROJECTS } else { "phase8b\Projects" }),
    [string]$LogFileV1 = $(if ($env:CI_PROJECT_DIR) { Join-Path $env:CI_PROJECT_DIR "phase8b_ota_build_v1.log" } else { Join-Path (Get-Location) "phase8b_ota_build_v1.log" }),
    [string]$LogFileV2 = $(if ($env:CI_PROJECT_DIR) { Join-Path $env:CI_PROJECT_DIR "phase8b_ota_build_v2.log" } else { Join-Path (Get-Location) "phase8b_ota_build_v2.log" }),
    [int]$PipelineIid = $(if ($env:CI_PIPELINE_IID) { [int]$env:CI_PIPELINE_IID } else { 1 })
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
$logFileV1 = [System.IO.Path]::GetFullPath($LogFileV1)
$logFileV2 = [System.IO.Path]::GetFullPath($LogFileV2)
$shortRoot = "C:\rx72n-phase8b-src"
$projectNames = @(
    "boot_loader_rx72n_envision_kit",
    "aws_ether_rx72n_envision_kit"
)
$rcpcSnapshots = @{}
$textSnapshots = @{}
$demoConfigPath = Join-Path $projectRoot "$phase8bProjectsPath\aws_ether_rx72n_envision_kit\e2studio_ccrx\src\frtos_config\demo_config.h"
$prmPath = Join-Path $projectRoot "$phase8bProjectsPath\boot_loader_rx72n_envision_kit\e2studio_ccrx\src\smc_gen\r_fwup\tool\RX72N_DualBank_ImageGenerator_PRM.csv"
$builderPath = Join-Path $projectRoot "tools\build_fwup_v2_rsu.py"
$keyPath = Join-Path $projectRoot "sample_keys\secp256r1.privatekey"
$otaV1Path = Join-Path $projectRoot "phase8b_ota_v1.rsu"
$otaV2Path = Join-Path $projectRoot "phase8b_ota_v2.rsu"
$versions = @{
    v1 = $PipelineIid * 2
    v2 = $PipelineIid * 2 + 1
}

foreach ($requiredPath in @($demoConfigPath, $prmPath, $builderPath, $keyPath)) {
    if (-not (Test-Path $requiredPath)) {
        throw "Required file not found: $requiredPath"
    }
}

if (Test-Path $workspace) {
    Remove-Item -Recurse -Force $workspace
}

function Write-Utf8NoBom {
    param(
        [string]$Path,
        [string]$Content
    )

    [System.IO.File]::WriteAllText(
        $Path,
        $Content,
        [System.Text.UTF8Encoding]::new($false)
    )
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

function Set-AppVersionBuild {
    param(
        [int]$BuildVersion
    )

    $content = Get-Content $demoConfigPath -Raw
    $updated = [System.Text.RegularExpressions.Regex]::Replace(
        $content,
        'APP_VERSION_BUILD\s+\d+',
        "APP_VERSION_BUILD    $BuildVersion"
    )

    if ($updated -eq $content) {
        throw "APP_VERSION_BUILD replacement failed in $demoConfigPath"
    }

    Write-Utf8NoBom -Path $demoConfigPath -Content $updated
}

function Clear-Phase8bHardwareDebug {
    foreach ($projectName in $projectNames) {
        $hardwareDebug = Join-Path $projectRoot "$phase8bProjectsPath\$projectName\e2studio_ccrx\HardwareDebug"
        if (Test-Path $hardwareDebug) {
            Remove-Item -Recurse -Force $hardwareDebug
            Write-Host "Cleared: $hardwareDebug"
        }
    }
}

function Invoke-Phase8bBuild {
    param(
        [string]$Label,
        [string]$LogFile
    )

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

    Write-Host "=== Build $Label ==="
    & $E2Studio @e2base @imports -cleanBuild all 2>&1 | Tee-Object -FilePath $LogFile | Out-Null
    $e2exit = $LASTEXITCODE

    Write-Host "e2studio exit code: $e2exit"
    Write-Host "--- Build log tail ($Label) ---"
    Get-Content $LogFile -Tail 30 -ErrorAction SilentlyContinue | ForEach-Object { Write-Host "  $_" }

    if ($e2exit -ne 0) {
        throw "e2studio failed for $Label with exit code $e2exit. See $LogFile"
    }

    $bootMot = Find-Artifacts "$phase8bProjectsPath\boot_loader_rx72n_envision_kit\e2studio_ccrx\HardwareDebug\*.mot"
    $appMot = Find-Artifacts "$phase8bProjectsPath\aws_ether_rx72n_envision_kit\e2studio_ccrx\HardwareDebug\*.mot"
    $appAbs = Find-Artifacts "$phase8bProjectsPath\aws_ether_rx72n_envision_kit\e2studio_ccrx\HardwareDebug\*.abs"
    $appX = Find-Artifacts "$phase8bProjectsPath\aws_ether_rx72n_envision_kit\e2studio_ccrx\HardwareDebug\*.x"

    if (-not $bootMot) { throw "boot_loader .mot not found after $Label" }
    if (-not $appMot) { throw "aws_ether .mot not found after $Label" }
    if (-not $appAbs) { throw "aws_ether .abs not found after $Label" }
    if (-not $appX) { throw "aws_ether .x not found after $Label" }

    return @{
        BootMot = $bootMot[0].FullName
        AppMot = $appMot[0].FullName
        AppAbs = $appAbs[0].FullName
        AppX = $appX[0].FullName
    }
}

function New-Phase8bRsu {
    param(
        [string]$MotPath,
        [string]$OutputPath
    )

    Write-Host "=== Generate RSU ==="
    Write-Host "  MOT: $MotPath"
    Write-Host "  PRM: $prmPath"
    Write-Host "  OUT: $OutputPath"

    & python $builderPath --mot $MotPath --prm $prmPath --key $keyPath --output $OutputPath
    if ($LASTEXITCODE -ne 0) {
        throw "RSU generation failed for $OutputPath"
    }
}

try {
    foreach ($projectName in $projectNames) {
        $rcpcPath = Join-Path $projectRoot "$phase8bProjectsPath\$projectName\e2studio_ccrx\$projectName.rcpc"
        if (Test-Path $rcpcPath) {
            $rcpcSnapshots[$rcpcPath] = Get-Content $rcpcPath -Raw
        }
    }

    $textSnapshots[$demoConfigPath] = Get-Content $demoConfigPath -Raw

    if (Test-Path $otaV1Path) {
        Remove-Item -Force $otaV1Path
    }
    if (Test-Path $otaV2Path) {
        Remove-Item -Force $otaV2Path
    }

    if (Test-Path $shortRoot) {
        cmd /c "rmdir `"$shortRoot`"" 2>$null
    }

    New-Item -ItemType Junction -Path $shortRoot -Target $projectRoot | Out-Null
    Write-Host "Junction: $shortRoot -> $projectRoot"

    Clear-Phase8bHardwareDebug
    Set-AppVersionBuild -BuildVersion $versions.v1
    $v1Artifacts = Invoke-Phase8bBuild -Label "phase8b OTA v1 (APP_VERSION_BUILD=$($versions.v1))" -LogFile $logFileV1
    New-Phase8bRsu -MotPath $v1Artifacts.AppMot -OutputPath $otaV1Path

    Clear-Phase8bHardwareDebug
    Set-AppVersionBuild -BuildVersion $versions.v2
    $v2Artifacts = Invoke-Phase8bBuild -Label "phase8b OTA v2 (APP_VERSION_BUILD=$($versions.v2))" -LogFile $logFileV2
    New-Phase8bRsu -MotPath $v2Artifacts.AppMot -OutputPath $otaV2Path

    Write-Host ""
    Write-Host "=== Phase 8b OTA Build Summary ==="
    Write-Host "  boot_loader .mot: $($v2Artifacts.BootMot)"
    Write-Host "  v1 RSU:          $otaV1Path"
    Write-Host "  v2 RSU:          $otaV2Path"
    if (Test-Path $otaV1Path) {
        Write-Host "  v1 size:         $((Get-Item $otaV1Path).Length) bytes"
    }
    if (Test-Path $otaV2Path) {
        Write-Host "  v2 size:         $((Get-Item $otaV2Path).Length) bytes"
    }
}
finally {
    foreach ($path in $textSnapshots.Keys) {
        Write-Utf8NoBom -Path $path -Content $textSnapshots[$path]
    }

    foreach ($rcpcPath in $rcpcSnapshots.Keys) {
        Write-Utf8NoBom -Path $rcpcPath -Content $rcpcSnapshots[$rcpcPath]
    }

    if (Test-Path $shortRoot) {
        cmd /c "rmdir `"$shortRoot`"" 2>$null
    }
}
