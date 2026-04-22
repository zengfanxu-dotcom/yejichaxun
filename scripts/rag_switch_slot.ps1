param(
    [string]$TargetSlot = "",
    [string]$RagRootDir = "chroma_db"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Step([string]$Message) {
    Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Message"
}

function Resolve-Slot([string]$Raw) {
    if ($null -eq $Raw) {
        $value = ""
    } else {
        $value = $Raw.Trim().ToUpper()
    }
    if ($value -in @("A", "B")) {
        return $value
    }
    return ""
}

$repoRoot = (Resolve-Path ".").Path
$ragRoot = Join-Path $repoRoot $RagRootDir
$slotsDir = Join-Path $ragRoot "slots"
$activeFile = Join-Path $ragRoot "active_slot.txt"

if (-not (Test-Path $slotsDir)) {
    Write-Step "Slots directory not found: $slotsDir"
    Write-Step "Hint: run one RAG rebuild first to initialize A/B slots."
    exit 0
}

$slotAPath = Join-Path $slotsDir "A"
$slotBPath = Join-Path $slotsDir "B"
if (-not (Test-Path $slotAPath) -or -not (Test-Path $slotBPath)) {
    throw "Both slot directories are required: $slotAPath and $slotBPath"
}

$currentSlot = ""
if (Test-Path $activeFile) {
    $currentSlot = Resolve-Slot (Get-Content -Path $activeFile -Raw)
}

$target = Resolve-Slot $TargetSlot
if (-not $target) {
    if ($currentSlot -eq "A") {
        $target = "B"
    } else {
        $target = "A"
    }
}

$tmpFile = "$activeFile.tmp"
Set-Content -Path $tmpFile -Value $target -Encoding utf8
Move-Item -Path $tmpFile -Destination $activeFile -Force

Write-Step "Active slot switched: '$currentSlot' -> '$target'"
Write-Step "Tip: restart backend process or call RAG rebuild endpoint if needed."
