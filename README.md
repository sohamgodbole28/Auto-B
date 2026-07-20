# Auto-B: Automated Bug Bounty Workflow Engine

Auto-B is a highly extensible workflow orchestration engine built to string together industry-standard bug bounty and reconnaissance tools into reusable, robust, production-quality pipelines.

**Note:** This project is an orchestrator, not a vulnerability scanner or a replacement for your existing toolset.

## Prerequisites

Before installing the Auto-B tools, your system must have the following prerequisites installed and accessible in your `PATH`:
- **Go** (for compiling projectdiscovery and tomnomnom utilities)
- **Git** (for cloning repositories)
- **Python 3** and **pip** (for installing `uro`)

The bootstrap system will explicitly check for these before attempting any installations. If any are missing, it will abort gracefully and ask you to install them manually.

## Installation

Auto-B provides a completely independent, idempotent bootstrap system to seamlessly install or update all required tools on both Linux and Windows. 

The installers will automatically configure the required Go utilities (subfinder, assetfinder, amass, github-subdomains, dnsx, shuffledns, httpx, katana, gau, waybackurls, unfurl) and Python utilities (uro).

### Linux Installation
1. Ensure your scripts are executable:
   ```bash
   chmod +x scripts/install_linux.sh scripts/verify_install.sh
   ```
2. Run the installer:
   ```bash
   ./scripts/install_linux.sh
   ```

### Windows Installation
1. Open PowerShell and ensure script execution is allowed:
   ```powershell
   Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
   ```
2. Run the installer:
   ```powershell
   .\scripts\install_windows.ps1
   ```

## Verifying the Environment

Once installation finishes, you can use the verification scripts to assert that every tool is correctly installed, added to the `PATH`, and accessible to Auto-B.

- **Linux:** `./scripts/verify_install.sh`
- **Windows:** `.\scripts\verify_install.ps1`

The verifier checks each binary, extracts its version, and outputs a table. It exits with a `0` status code only if the environment is fully verified.

## PATH Troubleshooting

Auto-B's installation system **never** overwrites or dynamically modifies your system's `PATH` configuration file. 
If the Go binary folder isn't in your `PATH`, the script will issue a warning and display instructions on exactly what to add. 
- **Linux:** Usually `export PATH=$PATH:$(go env GOPATH)/bin` in your `~/.bashrc` or `~/.zshrc`.
- **Windows:** Edit your System Environment Variables to add your `%USERPROFILE%\go\bin` path.

## Shuffledns and MassDNS

The tool `shuffledns` is heavily reliant on `massdns` for underlying DNS resolution. 

- **Linux:** The `install_linux.sh` script will attempt to clone and compile `massdns` from source automatically if `gcc` and `make` are installed.
- **Windows:** The installer will **not** attempt to compile `massdns`. Instead, you will see a warning prompting you to download a pre-compiled Windows binary or build it manually from the official repository, then place it in your `PATH`.

### Resolver File Requirements
The `shuffledns` stage also requires a list of valid DNS resolvers to function correctly. 
Place a file named `resolvers.txt` in the root directory of the Auto-B project. If this file or `massdns` is missing, the `shuffledns` stage will be safely skipped during execution without crashing the workflow.

## Expected Output Directory Structure

Auto-B manages all filesystem operations securely. You will never need to create directories yourself.

All output is stored centrally inside the `output/` directory in the following structure:
```text
output/
    <target>/
        recon/
            subfinder.txt
            assetfinder.txt
            amass.txt
            github_subdomains.txt
            subdomains.txt           # Merged & Deduplicated
            resolved_dnsx.txt
            resolved_shuffledns.txt
            resolved.txt             # Merged & Deduplicated
            alive.txt
            katana_urls.txt
            gau_urls.txt
            waybackurls.txt
            all_urls.txt             # Merged & Deduplicated
            clean_urls.txt
            domains.txt
            paths.txt
            parameters.txt
```

Every stage produces its own independent artifact. Auto-B never overwrites intermediate files, giving you full access to the raw data at any step.

## Example Execution

1. Start the main CLI application:
   ```bash
   python main.py
   ```
2. The interactive menu will appear. Select `[1] Recon Workflow`.
3. Auto-B will load the `recon.yaml` workflow metadata and ask for confirmation. Press `Y`.
4. Enter your target domain, for example: `example.com`.
5. The engine will sequentially execute the tools, passing output intelligently between stages and merging files natively in Python. The terminal will display progress indicators distinguishing between `SUCCESS`, `EMPTY OUTPUT`, `FAILED`, and `SKIPPED`.
6. Once complete, a Professional Summary will be presented detailing runtime, tool execution stats, and the output directory location.
