param(
    [string]$ProjectRoot = $env:CI_PROJECT_DIR,
    [string]$E2Studio = $env:E2STUDIO,
    [string]$Workspace = $(if ($env:V3_OTA_WORKSPACE) { $env:V3_OTA_WORKSPACE } else { "C:\rx72n-v3-ota-ws" }),
    [string]$V3ProjectsPath = $(if ($env:V3_E2STUDIO_PROJECTS) { $env:V3_E2STUDIO_PROJECTS } else { "Projects" }),
    [string]$LogFileV1 = $(if ($env:CI_PROJECT_DIR) { Join-Path $env:CI_PROJECT_DIR "rx72n_v3_ota_build_v1.log" } else { Join-Path (Get-Location) "rx72n_v3_ota_build_v1.log" }),
    [string]$LogFileV2 = $(if ($env:CI_PROJECT_DIR) { Join-Path $env:CI_PROJECT_DIR "rx72n_v3_ota_build_v2.log" } else { Join-Path (Get-Location) "rx72n_v3_ota_build_v2.log" }),
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
$v3ProjectsPath = $V3ProjectsPath -replace "/", "\"
$logFileV1 = [System.IO.Path]::GetFullPath($LogFileV1)
$logFileV2 = [System.IO.Path]::GetFullPath($LogFileV2)
$shortRoot = "C:\rx72n-v3-ota-src"
$projectNames = @(
    "boot_loader_rx72n_envision_kit",
    "aws_ether_rx72n_envision_kit"
)
$rcpcSnapshots = @{}
$textSnapshots = @{}
$demoConfigPath = Join-Path $projectRoot "$v3ProjectsPath\aws_ether_rx72n_envision_kit\e2studio_ccrx\src\frtos_config\demo_config.h"
$prmPath = Join-Path $projectRoot "$v3ProjectsPath\aws_ether_rx72n_envision_kit\e2studio_ccrx\src\smc_gen\r_fwup\tool\RX72N_DualBank_ImageGenerator_PRM.csv"
$builderPath = Join-Path $projectRoot "tools\build_fwup_v2_rsu.py"
$keyPath = Join-Path $projectRoot "sample_keys\secp256r1.privatekey"
$otaV1Path = Join-Path $projectRoot "rx72n_v3_ota_v1.rsu"
$otaV2Path = Join-Path $projectRoot "rx72n_v3_ota_v2.rsu"
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

function Clear-V3HardwareDebug {
    foreach ($projectName in $projectNames) {
        $hardwareDebug = Join-Path $projectRoot "$v3ProjectsPath\$projectName\e2studio_ccrx\HardwareDebug"
        if (Test-Path $hardwareDebug) {
            Remove-Item -Recurse -Force $hardwareDebug
            Write-Host "Cleared: $hardwareDebug"
        }
    }
}

function Invoke-V3Build {
    param(
        [string]$Label,
        [string]$LogFile
    )

    $imports = @()
    foreach ($projectName in $projectNames) {
        $imports += @("-import", (Join-Path $shortRoot "$v3ProjectsPath\$projectName\e2studio_ccrx"))
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

    $bootMot = Find-Artifacts "$v3ProjectsPath\boot_loader_rx72n_envision_kit\e2studio_ccrx\HardwareDebug\*.mot"
    $appMot = Find-Artifacts "$v3ProjectsPath\aws_ether_rx72n_envision_kit\e2studio_ccrx\HardwareDebug\*.mot"
    $appAbs = Find-Artifacts "$v3ProjectsPath\aws_ether_rx72n_envision_kit\e2studio_ccrx\HardwareDebug\*.abs"
    $appX = Find-Artifacts "$v3ProjectsPath\aws_ether_rx72n_envision_kit\e2studio_ccrx\HardwareDebug\*.x"

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

function New-V3Rsu {
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
        $rcpcPath = Join-Path $projectRoot "$v3ProjectsPath\$projectName\e2studio_ccrx\$projectName.rcpc"
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

    Clear-V3HardwareDebug
    Set-AppVersionBuild -BuildVersion $versions.v1
    $v1Artifacts = Invoke-V3Build -Label "v3 OTA v1 (APP_VERSION_BUILD=$($versions.v1))" -LogFile $logFileV1
    New-V3Rsu -MotPath $v1Artifacts.AppMot -OutputPath $otaV1Path

    Clear-V3HardwareDebug
    Set-AppVersionBuild -BuildVersion $versions.v2
    $v2Artifacts = Invoke-V3Build -Label "v3 OTA v2 (APP_VERSION_BUILD=$($versions.v2))" -LogFile $logFileV2
    New-V3Rsu -MotPath $v2Artifacts.AppMot -OutputPath $otaV2Path

    # Generate bank1 boot_loader .mot (shift -0x200000), same as build_v3_rx72n_headless.ps1
    $toolsV3 = Join-Path $projectRoot "tools\v3"
    $bootDbg = Split-Path $v2Artifacts.BootMot
    $bank0Mot = $v2Artifacts.BootMot
    $bank1Mot = Join-Path $bootDbg "boot_loader_rx72n_envision_kit_bank1.mot"
    Write-Host ""
    Write-Host "=== Generate bank1 boot_loader .mot (shift -0x200000) ==="
    & python (Join-Path $toolsV3 "shift_srec_addresses.py") `
        --input $bank0Mot `
        --output $bank1Mot `
        --range-start 0xFFE00000 `
        --range-end 0xFFFFFFFF `
        --shift -0x200000 `
        --drop-out-of-range
    if ($LASTEXITCODE -ne 0) { throw "shift_srec_addresses.py exit $LASTEXITCODE" }
    if (-not (Test-Path $bank1Mot)) { throw "bank1 .mot missing: $bank1Mot" }
    Write-Host "OK: $bank1Mot"

    # Generate code signer cert (public key) for provisioning
    $certOut = Join-Path $projectRoot "rx72n_codesign_cert.pem"
    Write-Host ""
    Write-Host "=== Generate code signer cert (public key) ==="
    & python (Join-Path $toolsV3 "generate_signer_cert.py") `
        --key $keyPath `
        --out $certOut
    if ($LASTEXITCODE -ne 0) { throw "generate_signer_cert.py exit $LASTEXITCODE" }
    if (-not (Test-Path $certOut)) { throw "rx72n_codesign_cert.pem missing: $certOut" }
    Write-Host "OK: $certOut"

    Write-Host ""
    Write-Host "=== RX72N v3 OTA Build Summary ==="
    Write-Host "  boot_loader .mot (bank0): $($v2Artifacts.BootMot)"
    Write-Host "  boot_loader .mot (bank1): $bank1Mot"
    Write-Host "  code signer cert:         $certOut"
    Write-Host "  v1 RSU:                   $otaV1Path (APP_VERSION_BUILD=$($versions.v1))"
    Write-Host "  v2 RSU:                   $otaV2Path (APP_VERSION_BUILD=$($versions.v2))"
    if (Test-Path $otaV1Path) {
        Write-Host "  v1 size:                  $((Get-Item $otaV1Path).Length) bytes"
    }
    if (Test-Path $otaV2Path) {
        Write-Host "  v2 size:                  $((Get-Item $otaV2Path).Length) bytes"
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
