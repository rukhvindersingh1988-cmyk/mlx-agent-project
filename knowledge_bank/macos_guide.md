# macOS System Guide

## CRITICAL RULE FOR AI AGENT:
When you need to open a new terminal tab, run background processes, or launch apps,
use the `run_command` tool directly. NEVER give the user commands to copy-paste manually.

## System Information
```bash
sw_vers                          # macOS version
uname -m                         # CPU architecture (arm64 = Apple Silicon)
sysctl -n hw.memsize             # Total RAM in bytes
df -h /                          # Disk space usage
top -l 1 | grep CPU              # CPU usage snapshot
```

## Process Management
```bash
ps aux | grep <name>             # Find a process by name
kill -9 <PID>                    # Force-kill a process by ID
pkill -f <name>                  # Kill process by name pattern
lsof -i :<port>                  # Find what is using a port
lsof -i :8000                    # Find what is using port 8000
```

## File System
```bash
ls -la                           # List all files with permissions
find . -name "*.py"              # Find all Python files recursively
du -sh *                         # Disk usage of each item
cp -r source/ dest/              # Copy directory recursively
rm -rf folder/                   # Delete folder (CAREFUL)
chmod +x script.sh               # Make script executable
```

## Network
```bash
curl -s https://httpbin.org/ip   # Check public IP
ping -c 3 google.com             # Ping test
netstat -an | grep LISTEN        # List all listening ports
```

## Environment Variables
```bash
echo $PATH                       # View PATH
export MY_VAR=value              # Set env var (current session)
echo 'export MY_VAR=value' >> ~/.zshrc  # Persist across sessions
source ~/.zshrc                  # Reload shell config
```

## Homebrew (Package Manager)
```bash
brew install <formula>           # Install a package
brew upgrade                     # Upgrade all packages
brew list                        # List installed packages
brew doctor                      # Diagnose issues
```

## SSH Key Management (Apple Silicon)
```bash
ssh-keygen -t ed25519 -C "email@example.com" -f ~/.ssh/id_ed25519 -N ""
cat ~/.ssh/id_ed25519.pub       # Print public key to add to GitHub/servers
ssh-add --apple-use-keychain ~/.ssh/id_ed25519  # Add to macOS keychain
ssh -T git@github.com           # Test GitHub connection
```

## Open Files and Apps
```bash
open .                           # Open current directory in Finder
open -a "TextEdit" file.txt     # Open file in specific app
open https://google.com          # Open URL in default browser
```
