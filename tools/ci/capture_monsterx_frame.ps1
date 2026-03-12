param(
    [Parameter(Mandatory = $true)]
    [string]$OutputPath,

    [string]$DevicesLogPath = "",
    [string]$VideoDeviceName = "MonsterX U3.0R Capture 0",
    [string]$Filter = "",
    [string]$RtBufSize = "256M"
)

$ErrorActionPreference = "Stop"

$ffmpeg = Get-Command ffmpeg -ErrorAction Stop

$deviceArgs = @(
    "-hide_banner",
    "-f", "dshow",
    "-list_devices", "true",
    "-i", "dummy"
)
$deviceOutput = & $ffmpeg.Source @deviceArgs 2>&1

if ($DevicesLogPath) {
    $devicesDir = Split-Path -Parent $DevicesLogPath
    if ($devicesDir) {
        New-Item -ItemType Directory -Force -Path $devicesDir | Out-Null
    }
    $deviceOutput | Set-Content -Encoding UTF8 -Path $DevicesLogPath
}

$deviceText = ($deviceOutput | Out-String)
if ($deviceText -notmatch [regex]::Escape($VideoDeviceName)) {
    throw "Capture device not found in ffmpeg dshow list: $VideoDeviceName"
}

$outputDir = Split-Path -Parent $OutputPath
if ($outputDir) {
    New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
}

$captureArgs = @(
    "-hide_banner",
    "-y",
    "-rtbufsize", $RtBufSize,
    "-f", "dshow",
    "-i", "video=$VideoDeviceName",
    "-frames:v", "1",
    "-update", "1"
)

if ($Filter) {
    $captureArgs += @("-vf", $Filter)
}

$captureArgs += $OutputPath

& $ffmpeg.Source @captureArgs

if (-not (Test-Path $OutputPath)) {
    throw "Capture image was not created: $OutputPath"
}

Get-Item $OutputPath | Select-Object FullName, Length, LastWriteTime | Format-List
