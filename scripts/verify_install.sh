#!/usr/bin/env bash
# Auto-B Linux Installation Verifier

echo "========================================================="
echo "Auto-B Environment Verifier (Linux)"
echo "========================================================="

TOOLS=(
    "subfinder"
    "assetfinder"
    "amass"
    "github-subdomains"
    "dnsx"
    "shuffledns"
    "httpx"
    "katana"
    "gau"
    "waybackurls"
    "unfurl"
    "uro"
)

export PATH=$PATH:$(go env GOPATH)/bin:$HOME/.local/bin

installed_count=0
missing_count=0

printf "%-20s | %-10s | %s\n" "Tool" "Status" "Version"
echo "---------------------------------------------------------"

for tool in "${TOOLS[@]}"; do
    if command -v "$tool" &> /dev/null; then
        ((installed_count++))
        status="Installed"
        
        # Fallback sequence for version detection
        version=""
        
        if output=$("$tool" --version 2>&1 | grep -iv "error" | head -n 1); then
            version=$(echo "$output" | sed -E 's/[^a-zA-Z0-9.\-]//g' | grep -Eo '[0-9]+\.[0-9]+\.[0-9]+' | head -n 1)
        fi
        
        if [ -z "$version" ]; then
            if output=$("$tool" -version 2>&1 | grep -iv "error" | head -n 1); then
                version=$(echo "$output" | sed -E 's/[^a-zA-Z0-9.\-]//g' | grep -Eo '[0-9]+\.[0-9]+\.[0-9]+' | head -n 1)
            fi
        fi
        
        if [ -z "$version" ]; then
            if output=$("$tool" -h 2>&1 | head -n 3); then
                version=$(echo "$output" | grep -Eo '[0-9]+\.[0-9]+\.[0-9]+' | head -n 1)
            fi
        fi
        
        if [ -z "$version" ]; then
            version="Unknown"
        fi
        
        printf "%-20s | \e[32m%-10s\e[0m | %s\n" "$tool" "$status" "$version"
    else
        ((missing_count++))
        status="Missing"
        printf "%-20s | \e[31m%-10s\e[0m | %s\n" "$tool" "$status" "N/A"
    fi
done

echo "========================================================="
echo "Total Installed : $installed_count"
echo "Total Missing   : $missing_count"
echo "========================================================="

if [ $missing_count -eq 0 ]; then
    echo "Environment is fully verified and ready!"
    exit 0
else
    echo "Environment is missing required tools."
    exit 1
fi
