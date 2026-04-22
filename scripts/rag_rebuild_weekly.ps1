param(
    [string]$NewExcelPath,
    [string]$ApiBase = "http://127.0.0.1:8000",
    [string]$DataDir = "database/data",
    [string]$MainExcelName = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Step([string]$Message) {
    Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Message"
}

function Ensure-Path([string]$Path) {
    if (-not (Test-Path -Path $Path)) {
        throw "Path does not exist: $Path"
    }
}

$repoRoot = (Resolve-Path ".").Path
$fullDataDir = Join-Path $repoRoot $DataDir
Ensure-Path $fullDataDir

$preferredNames = @()
if ($MainExcelName) {
    $preferredNames += $MainExcelName
}
$preferredNames += @("业绩JL.xlsx", "yejiJL.xlsx")

$resolvedName = $null
foreach ($name in $preferredNames) {
    $candidate = Join-Path $fullDataDir $name
    if (Test-Path $candidate) {
        $resolvedName = $name
        break
    }
}
if (-not $resolvedName) {
    $firstExcel = Get-ChildItem -Path $fullDataDir -File | Where-Object { $_.Extension -in @(".xls", ".xlsx") } | Select-Object -First 1
    if ($firstExcel) {
        $resolvedName = $firstExcel.Name
    } else {
        $resolvedName = if ($MainExcelName) { $MainExcelName } else { "业绩JL.xlsx" }
    }
}

$mainExcelPath = Join-Path $fullDataDir $resolvedName
$backupDir = Join-Path $fullDataDir "backups"
$recordDir = Join-Path $repoRoot "docs"
$recordFile = Join-Path $recordDir "rag-rebuild-history.md"
$sampleDir = Join-Path $fullDataDir "samples"

if (-not (Test-Path $backupDir)) {
    New-Item -ItemType Directory -Path $backupDir | Out-Null
}
if (-not (Test-Path $recordDir)) {
    New-Item -ItemType Directory -Path $recordDir | Out-Null
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backupPath = $null

if (Test-Path $mainExcelPath) {
    $backupPath = Join-Path $backupDir ("{0}.{1}.bak.xlsx" -f [IO.Path]::GetFileNameWithoutExtension($resolvedName), $timestamp)
    Copy-Item -Path $mainExcelPath -Destination $backupPath -Force
    Write-Step "Backed up old Excel: $backupPath"
}

if ($NewExcelPath) {
    Ensure-Path $NewExcelPath
    Copy-Item -Path $NewExcelPath -Destination $mainExcelPath -Force
    Write-Step "Replaced main data file: $mainExcelPath"
}

$sampleInfo = "Sample check not executed"
if (Test-Path $sampleDir) {
    $sampleFiles = Get-ChildItem -Path $sampleDir -Filter "*.txt" -File
    if ($sampleFiles.Count -gt 0) {
        $sampleInfo = "Found $($sampleFiles.Count) sample query file(s) in $sampleDir"
    }
}

Write-Step "Calling RAG rebuild endpoint..."
$resp = Invoke-RestMethod -Method Post -Uri "$ApiBase/api/v1/rag/rebuild"
if (-not $resp.ok) {
    throw "RAG rebuild failed: $($resp | ConvertTo-Json -Depth 5)"
}
Write-Step "RAG rebuild succeeded, document_count=$($resp.document_count)"

if (-not (Test-Path $recordFile)) {
    @(
        "# RAG Rebuild History"
        ""
        "| Time | Excel | Backup | Document Count | Sample Check | Operator |"
        "| --- | --- | --- | ---: | --- | --- |"
    ) | Out-File -FilePath $recordFile -Encoding utf8
}

$operator = $env:USERNAME
$excelName = [IO.Path]::GetFileName($mainExcelPath)
$backupName = if ($backupPath) { [IO.Path]::GetFileName($backupPath) } else { "N/A" }
$line = "| $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') | $excelName | $backupName | $($resp.document_count) | $sampleInfo | $operator |"
Add-Content -Path $recordFile -Value $line -Encoding utf8

Write-Step "Wrote rebuild record: $recordFile"
Write-Step "Done."
