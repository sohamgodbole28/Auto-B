# Auto-B Windows Bootstrap Installer

Write-Host "========================================================="
Write-Host "Auto-B Bootstrap Installer (Windows)"
Write-Host "========================================================="

$missing_prereqs = 0

# 1. Prerequisite Checks
if (-not (Get-Command "go" -ErrorAction SilentlyContinue)) {
    Write-Host "[!] Error: 'go' is not installed or not in PATH." -ForegroundColor Red
    $missing_prereqs = 1
} else {
    $go_ver = (go version).Split(" ")[2]
}

if (-not (Get-Command "git" -ErrorAction SilentlyContinue)) {
    Write-Host "[!] Error: 'git' is not installed or not in PATH." -ForegroundColor Red
    $missing_prereqs = 1
} else {
    $git_ver = (git --version).Split(" ")[2]
}

if (-not (Get-Command "python" -ErrorAction SilentlyContinue)) {
    Write-Host "[!] Error: 'python' is not installed or not in PATH." -ForegroundColor Red
    $missing_prereqs = 1
} else {
    $py_ver = (python --version).Split(" ")[1]
}

if (-not (Get-Command "pip" -ErrorAction SilentlyContinue)) {
    Write-Host "[!] Error: 'pip' is not installed." -ForegroundColor Red
    $missing_prereqs = 1
}

if ($missing_prereqs -ne 0) {
    Write-Host "========================================================="
    Write-Host "Installation Aborted. Please install missing prerequisites." -ForegroundColor Red
    exit 1
}

Write-Host "[*] Prerequisites met. Starting installation..."

# Add temporary path for current session to find newly installed go tools
$go_path = go env GOPATH
$go_bin = Join-Path $go_path "bin"
$env:PATH += ";$go_bin"

$newly_installed = 0
$updated = 0
$already_installed = 0
$failed = 0

$tools = @(
    @("subfinder", "go", "github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest"),
    @("assetfinder", "go", "github.com/tomnomnom/assetfinder@latest"),
    @("amass", "go", "github.com/owasp-amass/amass/v4/...@master"),
    @("github-subdomains", "go", "github.com/gwen001/github-subdomains@latest"),
    @("dnsx", "go", "github.com/projectdiscovery/dnsx/cmd/dnsx@latest"),
    @("shuffledns", "go", "github.com/projectdiscovery/shuffledns/cmd/shuffledns@latest"),
    @("httpx", "go", "github.com/projectdiscovery/httpx/cmd/httpx@latest"),
    @("katana", "go", "github.com/projectdiscovery/katana/cmd/katana@latest"),
    @("gau", "go", "github.com/lc/gau/v2/cmd/gau@latest"),
    @("waybackurls", "go", "github.com/tomnomnom/waybackurls@latest"),
    @("unfurl", "go", "github.com/tomnomnom/unfurl@latest"),
    @("uro", "pip", "uro")
)

foreach ($tool in $tools) {
    $tool_name = $tool[0]
    $install_type = $tool[1]
    $pkg_path = $tool[2]
    
    $is_installed = $false
    if (Get-Command $tool_name -ErrorAction SilentlyContinue) {
        $is_installed = $true
    }
    
    if ($is_installed) {
        Write-Host "[*] $tool_name is already installed. Attempting update..."
        if ($install_type -eq "go") {
            try {
                go install -v $pkg_path *>$null
                if ($LASTEXITCODE -eq 0) {
                    Write-Host "    -> Updated" -ForegroundColor Green
                    $updated++
                } else {
                    Write-Host "    -> Update Failed (Keeping existing version)" -ForegroundColor Yellow
                    $already_installed++
                }
            } catch {
                Write-Host "    -> Update Failed" -ForegroundColor Yellow
                $already_installed++
            }
        } elseif ($install_type -eq "pip") {
            try {
                pip install -U $pkg_path *>$null
                if ($LASTEXITCODE -eq 0) {
                    Write-Host "    -> Updated" -ForegroundColor Green
                    $updated++
                } else {
                    Write-Host "    -> Update Failed" -ForegroundColor Yellow
                    $already_installed++
                }
            } catch {
                Write-Host "    -> Update Failed" -ForegroundColor Yellow
                $already_installed++
            }
        }
    } else {
        Write-Host "[*] Installing $tool_name..."
        if ($install_type -eq "go") {
            go install -v $pkg_path *>$null
        } elseif ($install_type -eq "pip") {
            pip install $pkg_path *>$null
        }
        
        # Verify
        if (Get-Command $tool_name -ErrorAction SilentlyContinue) {
            Write-Host "    -> Newly Installed" -ForegroundColor Green
            $newly_installed++
        } else {
            Write-Host "    -> Failed" -ForegroundColor Red
            $failed++
        }
    }
}

# MassDNS specific handling
$massdns_status = "Missing (Not built)"
if (Get-Command "massdns" -ErrorAction SilentlyContinue) {
    $massdns_status = "Installed"
} else {
    Write-Host ""
    Write-Host "[!] WARNING: shuffledns requires massdns." -ForegroundColor Yellow
    Write-Host "    MassDNS must be built manually from source on Windows."
    Write-Host "    Please download from https://github.com/blechschmidt/massdns and add it to your PATH."
    Write-Host ""
}

# PATH Check
$path_status = "OK"
$machine_path = [Environment]::GetEnvironmentVariable("PATH", "Machine")
$user_path = [Environment]::GetEnvironmentVariable("PATH", "User")
$combined_path = $machine_path + ";" + $user_path

if ($combined_path -notmatch [regex]::Escape($go_bin)) {
    $path_status = "WARNING: Go bin not in PATH"
    Write-Host ""
    Write-Host "[!] IMPORTANT: Your Go binary directory ($go_bin) is not permanently in your PATH." -ForegroundColor Yellow
    Write-Host "    Please edit your System Environment Variables and add it."
    Write-Host ""
}

Write-Host "========================================================="
Write-Host "Auto-B Bootstrap Summary"
Write-Host "========================================================="
Write-Host "Operating System : Windows"
Write-Host "Go Version       : $go_ver"
Write-Host "Python Version   : $py_ver"
Write-Host "Git Version      : $git_ver"
Write-Host "---------------------------------------------------------"
Write-Host "PATH Status      : $path_status"
Write-Host "MassDNS Status   : $massdns_status"
Write-Host "---------------------------------------------------------"
Write-Host "Newly Installed  : $newly_installed"
Write-Host "Updated          : $updated"
Write-Host "Already Installed: $already_installed"
Write-Host "Failed           : $failed"
Write-Host "---------------------------------------------------------"
if ($failed -eq 0) {
    Write-Host "Ready for Auto-B : YES" -ForegroundColor Green
} else {
    Write-Host "Ready for Auto-B : NO" -ForegroundColor Red
}
Write-Host "========================================================="
