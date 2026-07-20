# Auto-B Windows Installation Verifier

Write-Host "========================================================="
Write-Host "Auto-B Environment Verifier (Windows)"
Write-Host "========================================================="

$tools = @(
    "subfinder",
    "assetfinder",
    "amass",
    "github-subdomains",
    "dnsx",
    "shuffledns",
    "httpx",
    "katana",
    "gau",
    "waybackurls",
    "unfurl",
    "uro"
)

$go_path = go env GOPATH
$go_bin = Join-Path $go_path "bin"
$env:PATH += ";$go_bin"

$installed_count = 0
$missing_count = 0

Write-Host ("{0,-20} | {1,-10} | {2}" -f "Tool", "Status", "Version")
Write-Host "---------------------------------------------------------"

foreach ($tool in $tools) {
    if (Get-Command $tool -ErrorAction SilentlyContinue) {
        $installed_count++
        $status = "Installed"
        
        # Version fallback sequence
        $version = $null
        
        try {
            $out1 = & $tool --version 2>&1
            if ($out1 -notmatch "Error|flag provided but not defined") {
                $match = [regex]::Match($out1, "[0-9]+\.[0-9]+\.[0-9]+")
                if ($match.Success) { $version = $match.Value }
            }
        } catch {}
        
        if (-not $version) {
            try {
                $out2 = & $tool -version 2>&1
                if ($out2 -notmatch "Error|flag provided but not defined") {
                    $match = [regex]::Match($out2, "[0-9]+\.[0-9]+\.[0-9]+")
                    if ($match.Success) { $version = $match.Value }
                }
            } catch {}
        }
        
        if (-not $version) {
            try {
                $out3 = & $tool -h 2>&1
                if ($out3) {
                    $match = [regex]::Match($out3, "[0-9]+\.[0-9]+\.[0-9]+")
                    if ($match.Success) { $version = $match.Value }
                }
            } catch {}
        }
        
        if (-not $version) {
            $version = "Unknown"
        }
        
        Write-Host -NoNewline ("{0,-20} | " -f $tool)
        Write-Host -NoNewline ("{0,-10}" -f $status) -ForegroundColor Green
        Write-Host (" | {0}" -f $version)
    } else {
        $missing_count++
        $status = "Missing"
        Write-Host -NoNewline ("{0,-20} | " -f $tool)
        Write-Host -NoNewline ("{0,-10}" -f $status) -ForegroundColor Red
        Write-Host (" | N/A")
    }
}

Write-Host "========================================================="
Write-Host "Total Installed : $installed_count"
Write-Host "Total Missing   : $missing_count"
Write-Host "========================================================="

if ($missing_count -eq 0) {
    Write-Host "Environment is fully verified and ready!" -ForegroundColor Green
    exit 0
} else {
    Write-Host "Environment is missing required tools." -ForegroundColor Red
    exit 1
}
