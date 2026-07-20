#!/usr/bin/env bash
# Auto-B Linux Bootstrap Installer

echo "========================================================="
echo "Auto-B Bootstrap Installer (Linux)"
echo "========================================================="

# 1. Prerequisite Checks
missing_prereqs=0

if ! command -v go &> /dev/null; then
    echo "[!] Error: 'go' is not installed or not in PATH."
    missing_prereqs=1
else
    GO_VERSION=$(go version | awk '{print $3}')
fi

if ! command -v git &> /dev/null; then
    echo "[!] Error: 'git' is not installed or not in PATH."
    missing_prereqs=1
else
    GIT_VERSION=$(git --version | awk '{print $3}')
fi

if ! command -v python3 &> /dev/null; then
    echo "[!] Error: 'python3' is not installed or not in PATH."
    missing_prereqs=1
else
    PY_VERSION=$(python3 --version | awk '{print $2}')
fi

if ! command -v pip &> /dev/null && ! command -v pip3 &> /dev/null; then
    echo "[!] Error: 'pip' or 'pip3' is not installed."
    missing_prereqs=1
fi

if [ $missing_prereqs -ne 0 ]; then
    echo "========================================================="
    echo "Installation Aborted. Please install missing prerequisites."
    exit 1
fi

echo "[*] Prerequisites met. Starting installation..."

# Tracking
newly_installed=0
updated=0
already_installed=0
failed=0

# Determine PIP command
PIP_CMD="pip"
if ! command -v pip &> /dev/null; then
    PIP_CMD="pip3"
fi

# Tools Definition (Format: "ToolName|InstallType|PackagePath")
TOOLS=(
    "subfinder|go|github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest"
    "assetfinder|go|github.com/tomnomnom/assetfinder@latest"
    "amass|go|github.com/owasp-amass/amass/v4/...@master"
    "github-subdomains|go|github.com/gwen001/github-subdomains@latest"
    "dnsx|go|github.com/projectdiscovery/dnsx/cmd/dnsx@latest"
    "shuffledns|go|github.com/projectdiscovery/shuffledns/cmd/shuffledns@latest"
    "httpx|go|github.com/projectdiscovery/httpx/cmd/httpx@latest"
    "katana|go|github.com/projectdiscovery/katana/cmd/katana@latest"
    "gau|go|github.com/lc/gau/v2/cmd/gau@latest"
    "waybackurls|go|github.com/tomnomnom/waybackurls@latest"
    "unfurl|go|github.com/tomnomnom/unfurl@latest"
    "uro|pip|uro"
)

# Set PATH explicitly for current session just in case it's not exported
export PATH=$PATH:$(go env GOPATH)/bin:$HOME/.local/bin

for entry in "${TOOLS[@]}"; do
    IFS="|" read -r tool_name install_type pkg_path <<< "$entry"
    
    is_installed=0
    if command -v "$tool_name" &> /dev/null; then
        is_installed=1
    fi
    
    if [ $is_installed -eq 1 ]; then
        echo "[*] $tool_name is already installed. Attempting update..."
        if [ "$install_type" == "go" ]; then
            go install -v "$pkg_path" &> /dev/null
            if [ $? -eq 0 ]; then
                echo "    -> Updated"
                ((updated++))
            else
                echo "    -> Update Failed (Keeping existing version)"
                ((already_installed++))
            fi
        elif [ "$install_type" == "pip" ]; then
            $PIP_CMD install -U "$pkg_path" &> /dev/null
            if [ $? -eq 0 ]; then
                echo "    -> Updated"
                ((updated++))
            else
                echo "    -> Update Failed"
                ((already_installed++))
            fi
        fi
    else
        echo "[*] Installing $tool_name..."
        if [ "$install_type" == "go" ]; then
            go install -v "$pkg_path" &> /dev/null
        elif [ "$install_type" == "pip" ]; then
            $PIP_CMD install "$pkg_path" &> /dev/null
        fi
        
        # Verify installation success
        if command -v "$tool_name" &> /dev/null; then
            echo "    -> Newly Installed"
            ((newly_installed++))
        else
            echo "    -> Failed"
            ((failed++))
        fi
    fi
done

# MassDNS specific handling
MASSDNS_STATUS="Missing (Not built)"
if command -v massdns &> /dev/null; then
    MASSDNS_STATUS="Installed"
else
    echo "[*] Attempting to build massdns from source..."
    if command -v make &> /dev/null && command -v gcc &> /dev/null; then
        TMP_DIR=$(mktemp -d)
        git clone https://github.com/blechschmidt/massdns.git "$TMP_DIR" &> /dev/null
        if [ $? -eq 0 ]; then
            cd "$TMP_DIR" || exit
            make &> /dev/null
            if [ -f "bin/massdns" ]; then
                # Try to move to a system path or user path
                cp bin/massdns /usr/local/bin/ 2>/dev/null || cp bin/massdns ~/.local/bin/ 2>/dev/null || cp bin/massdns $(go env GOPATH)/bin/ 2>/dev/null
                if command -v massdns &> /dev/null; then
                    MASSDNS_STATUS="Built and Installed"
                    echo "    -> Built massdns successfully"
                else
                    echo "    -> Built massdns but failed to copy to PATH. Manual installation required."
                fi
            else
                echo "    -> Build failed."
            fi
            cd - > /dev/null || exit
            rm -rf "$TMP_DIR"
        else
            echo "    -> Failed to clone massdns repository."
        fi
    else
        echo "    -> Build tools (make, gcc) missing. Skipping massdns build."
        echo "    [!] WARNING: shuffledns requires massdns. Please install it manually."
    fi
fi

# PATH Status Check
PATH_STATUS="OK"
if [[ ":$PATH:" != *":$(go env GOPATH)/bin:"* ]]; then
    PATH_STATUS="WARNING: Go bin not in PATH"
    echo ""
    echo "[!] IMPORTANT: Your Go binary directory is not permanently in your PATH."
    echo "    Please add the following line to your ~/.bashrc or ~/.zshrc:"
    echo "    export PATH=\$PATH:\$(go env GOPATH)/bin"
    echo ""
fi

# Calculate totals
TOTAL_INSTALLED=$((newly_installed + updated + already_installed))

echo "========================================================="
echo "Auto-B Bootstrap Summary"
echo "========================================================="
echo "Operating System : $(uname -s)"
echo "Go Version       : $GO_VERSION"
echo "Python Version   : $PY_VERSION"
echo "Git Version      : $GIT_VERSION"
echo "---------------------------------------------------------"
echo "PATH Status      : $PATH_STATUS"
echo "MassDNS Status   : $MASSDNS_STATUS"
echo "---------------------------------------------------------"
echo "Newly Installed  : $newly_installed"
echo "Updated          : $updated"
echo "Already Installed: $already_installed"
echo "Failed           : $failed"
echo "---------------------------------------------------------"
echo "Ready for Auto-B : $(if [ $failed -eq 0 ]; then echo 'YES'; else echo 'NO'; fi)"
echo "========================================================="
