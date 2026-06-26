# GitHub Integration Knowledge Sheet

**CRITICAL RULE FOR AI AGENT:**
Whenever you are asked to connect to Git or GitHub, NEVER execute commands using placeholder values like `username`, `owner`, `repo`, `your-repo-name`, or `your_email@example.com`.
If the user hasn't explicitly told you their actual GitHub username, repo name, or the exact Git URL, you MUST stop and ask them for it before running ANY `git remote` or `gh repo` commands!

---

## 1. SSH Key Setup

### 1.1 Check for Existing SSH Keys

```bash
ls -la ~/.ssh/id_*
```

If files like `id_ed25519` and `id_ed25519.pub` (or `id_rsa` / `id_rsa.pub`) exist, you already have a key pair.

### 1.2 Generate a New SSH Key

```bash
ssh-keygen -t ed25519 -C "your_email@example.com" -f ~/.ssh/id_ed25519 -N ""
```

* `-t ed25519` — Uses the Ed25519 algorithm (recommended; fast and secure).
* `-C "your_email@example.com"` — Attaches a label (use your GitHub email).
* `-f ~/.ssh/id_ed25519` — Specifies the output file path.
* `-N ""` — Sets an empty passphrase (for automation; use a passphrase for extra security if desired).

For legacy systems that don't support Ed25519:

```bash
ssh-keygen -t rsa -b 4096 -C "your_email@example.com" -f ~/.ssh/id_rsa -N ""
```

### 1.3 Start the SSH Agent and Add Your Key

```bash
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519
```

On macOS, to persist across reboots, add to `~/.ssh/config`:

```bash
cat >> ~/.ssh/config << 'EOF'
Host github.com
  AddKeysToAgent yes
  UseKeychain yes
  IdentityFile ~/.ssh/id_ed25519
EOF
```

Then add with Keychain support:

```bash
ssh-add --apple-use-keychain ~/.ssh/id_ed25519
```

### 1.4 Copy the Public Key

```bash
cat ~/.ssh/id_ed25519.pub
```

Or copy directly to clipboard:

```bash
# macOS
pbcopy < ~/.ssh/id_ed25519.pub

# Linux (requires xclip)
xclip -selection clipboard < ~/.ssh/id_ed25519.pub
```

### 1.5 Add the Key to Your GitHub Account

1. Go to **GitHub → Settings → SSH and GPG keys → New SSH key**.
2. Paste the public key content.
3. Give it a descriptive **Title** (e.g., "MacBook Pro 2024").
4. Click **Add SSH key**.

Or use the GitHub CLI:

```bash
gh ssh-key add ~/.ssh/id_ed25519.pub --title "My Machine"
```

### 1.6 Verify the SSH Connection

```bash
ssh -T git@github.com
```

Expected success output:

```
Hi username! You've successfully authenticated, but GitHub does not provide shell access.
```

If you get `Host key verification failed`, add GitHub to known hosts first:

```bash
mkdir -p ~/.ssh && ssh-keyscan github.com >> ~/.ssh/known_hosts
```

---

## 2. Git Basics

### 2.1 Configure Git (First-Time Setup)

```bash
git config --global user.name "Your Name"
git config --global user.email "your_email@example.com"

# Verify config
git config --list --global
```

### 2.2 Initialize a New Repository

```bash
git init
git branch -M main
```

### 2.3 Clone an Existing Repository

```bash
# Via SSH (recommended)
git clone git@github.com:owner/repo.git

# Via HTTPS
git clone https://github.com/owner/repo.git

# Clone into a specific directory
git clone git@github.com:owner/repo.git my-project
```

### 2.4 Stage and Commit Changes

```bash
# Check status of working directory
git status

# Stage specific files
git add file1.txt file2.py

# Stage all changes
git add .

# Stage interactively (choose hunks)
git add -p

# Commit with a message
git commit -m "feat: add user authentication module"

# Amend the last commit (e.g., fix message or add forgotten files)
git add forgotten_file.py
git commit --amend -m "feat: add user authentication module with tests"
```

### 2.5 Push and Pull

```bash
# Add a remote (if not already set)
git remote add origin git@github.com:owner/repo.git

# Push to remote and set upstream tracking
git push -u origin main

# Subsequent pushes (upstream already set)
git push

# Pull latest changes from remote
git pull origin main

# Pull with rebase instead of merge (cleaner history)
git pull --rebase origin main
```

### 2.6 Branching

```bash
# List all branches
git branch -a

# Create a new branch
git branch feature/login

# Create and switch to a new branch
git checkout -b feature/login
# OR (modern alternative)
git switch -c feature/login

# Switch to an existing branch
git checkout main
# OR
git switch main

# Delete a local branch (safe — won't delete unmerged work)
git branch -d feature/login

# Force-delete a local branch
git branch -D feature/login

# Delete a remote branch
git push origin --delete feature/login
```

### 2.7 Merging

```bash
# Merge a feature branch into main
git checkout main
git merge feature/login

# Merge with a merge commit (even if fast-forward is possible)
git merge --no-ff feature/login

# Abort a merge in progress
git merge --abort
```

### 2.8 Rebasing

```bash
# Rebase current branch onto main
git checkout feature/login
git rebase main

# Interactive rebase — squash, reorder, or edit last N commits
git rebase -i HEAD~3

# Continue rebase after resolving conflicts
git rebase --continue

# Abort a rebase in progress
git rebase --abort

# After rebasing a pushed branch, force-push with lease (safer)
git push --force-with-lease
```

### 2.9 Viewing History

```bash
# View commit log
git log --oneline --graph --decorate -20

# View changes in a commit
git show <commit-hash>

# View diff of unstaged changes
git diff

# View diff of staged changes
git diff --staged
```

### 2.10 Stashing Changes

```bash
# Stash current changes
git stash

# Stash with a message
git stash push -m "WIP: login form styling"

# List stashes
git stash list

# Apply the most recent stash
git stash pop

# Apply a specific stash
git stash apply stash@{2}

# Drop a stash
git stash drop stash@{0}
```

### 2.11 Resetting and Reverting

```bash
# Undo last commit, keep changes staged
git reset --soft HEAD~1

# Undo last commit, keep changes unstaged
git reset --mixed HEAD~1

# Undo last commit, DISCARD all changes (destructive!)
git reset --hard HEAD~1

# Revert a specific commit (creates a new commit that undoes it — safe for shared branches)
git revert <commit-hash>

# Discard changes in a specific file
git checkout -- filename
# OR (modern)
git restore filename

# Unstage a file
git restore --staged filename
```

---

## 3. GitHub CLI (`gh`)

### 3.1 Install GitHub CLI

```bash
# macOS (Homebrew)
brew install gh

# Ubuntu / Debian
sudo apt install gh

# Verify installation
gh --version
```

### 3.2 Authenticate

```bash
# Interactive login (opens browser for OAuth)
gh auth login

# Login with a token
gh auth login --with-token < token.txt

# Check authentication status
gh auth status

# Switch between accounts
gh auth switch

# Logout
gh auth logout
```

### 3.3 Repository Operations

```bash
# Create a new public repo from current directory
gh repo create my-repo --public --source=. --remote=origin --push

# Create a new private repo
gh repo create my-repo --private --source=. --remote=origin --push

# Clone a repo
gh repo clone owner/repo

# Fork a repo
gh repo fork owner/repo --clone

# View repo info
gh repo view owner/repo

# List your repos
gh repo list --limit 20
```

### 3.4 Pull Requests

```bash
# Create a PR (interactive)
gh pr create

# Create a PR with title and body
gh pr create --title "Add login feature" --body "Implements OAuth2 login flow"

# Create a draft PR
gh pr create --draft --title "WIP: Dashboard redesign"

# List open PRs
gh pr list

# View a specific PR
gh pr view 42

# Check out a PR locally
gh pr checkout 42

# Merge a PR
gh pr merge 42 --merge
gh pr merge 42 --squash
gh pr merge 42 --rebase

# Review a PR
gh pr review 42 --approve
gh pr review 42 --request-changes --body "Please fix the tests"
```

### 3.5 Issues

```bash
# List open issues
gh issue list

# Create an issue
gh issue create --title "Bug: login fails on Safari" --body "Steps to reproduce..."

# View an issue
gh issue view 15

# Close an issue
gh issue close 15

# Reopen an issue
gh issue reopen 15

# Add labels
gh issue edit 15 --add-label "bug,priority:high"
```

### 3.6 Other Useful `gh` Commands

```bash
# View CI/CD workflow runs
gh run list
gh run view <run-id>

# Create a GitHub release
gh release create v1.0.0 --title "v1.0.0" --notes "Initial release"

# Create a gist
gh gist create file.txt --public --desc "My snippet"

# Open current repo in browser
gh browse
```

---

## 4. Common Workflows

### 4.1 Fork & Pull Request Workflow

This is the standard open-source contribution workflow.

```bash
# 1. Fork the upstream repo (creates a copy under your account)
gh repo fork upstream-owner/repo --clone
cd repo

# 2. Add the upstream remote (if not auto-added)
git remote add upstream git@github.com:upstream-owner/repo.git
git remote -v   # Verify remotes

# 3. Create a feature branch
git checkout -b fix/typo-in-readme

# 4. Make changes, stage, and commit
git add .
git commit -m "fix: correct typo in README.md"

# 5. Fetch latest upstream changes and rebase
git fetch upstream
git rebase upstream/main

# 6. Push your branch to YOUR fork
git push origin fix/typo-in-readme

# 7. Create a pull request against upstream
gh pr create --repo upstream-owner/repo \
  --title "Fix typo in README" \
  --body "Corrected a small typo in the installation section."
```

### 4.2 Branch Strategy (Git Flow Simplified)

| Branch       | Purpose                          | Merges Into |
|-------------|----------------------------------|-------------|
| `main`      | Production-ready code            | —           |
| `develop`   | Integration branch for features  | `main`      |
| `feature/*` | New features                     | `develop`   |
| `fix/*`     | Bug fixes                        | `develop`   |
| `hotfix/*`  | Urgent production fixes          | `main`      |
| `release/*` | Release preparation              | `main`      |

**Example workflow:**

```bash
# Start a feature
git checkout develop
git pull origin develop
git checkout -b feature/dark-mode

# Work on the feature...
git add .
git commit -m "feat: implement dark mode toggle"

# Merge back into develop
git checkout develop
git merge --no-ff feature/dark-mode
git push origin develop
git branch -d feature/dark-mode
```

### 4.3 Trunk-Based Development (Simpler Alternative)

```bash
# Everyone works off main with short-lived branches
git checkout main
git pull
git checkout -b short-lived/my-change

# Make small, focused changes
git add .
git commit -m "refactor: simplify auth middleware"
git push -u origin short-lived/my-change

# Create PR → get review → squash merge → delete branch
gh pr create --title "Simplify auth middleware"
```

### 4.4 Resolving Merge Conflicts

```bash
# 1. Attempt the merge
git checkout main
git merge feature/login

# 2. If conflicts occur, Git will tell you which files conflict
git status   # Look for "both modified" files

# 3. Open the conflicting file(s) — look for conflict markers:
#    <<<<<<< HEAD
#    (your changes on main)
#    =======
#    (changes from feature/login)
#    >>>>>>> feature/login

# 4. Edit the file to resolve — remove markers, keep the correct code

# 5. Stage the resolved files
git add resolved_file.py

# 6. Complete the merge
git commit -m "merge: resolve conflicts from feature/login"
```

**Resolving conflicts during rebase:**

```bash
git rebase main
# Conflict occurs...
# Edit the file to resolve
git add resolved_file.py
git rebase --continue
# Repeat for each conflicting commit
```

**Using a merge tool:**

```bash
# Configure a merge tool (e.g., VS Code)
git config --global merge.tool vscode
git config --global mergetool.vscode.cmd 'code --wait --merge $REMOTE $LOCAL $BASE $MERGED'

# Launch the merge tool
git mergetool
```

---

## 5. Troubleshooting

### 5.1 Permission Denied (publickey)

**Symptom:**

```
git@github.com: Permission denied (publickey).
fatal: Could not read from remote repository.
```

**Fix:**

```bash
# 1. Check if SSH agent is running and has your key
ssh-add -l

# 2. If empty, add your key
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519

# 3. Verify the key is on your GitHub account
gh ssh-key list

# 4. Test the connection
ssh -T git@github.com

# 5. If still failing, check the key matches
ssh-keygen -l -f ~/.ssh/id_ed25519.pub   # local fingerprint
# Compare with fingerprints shown at github.com/settings/keys
```

### 5.2 SSH vs. HTTPS — When to Use Which

| Aspect           | SSH                                | HTTPS                              |
|-----------------|------------------------------------|------------------------------------|
| **URL format**  | `git@github.com:owner/repo.git`   | `https://github.com/owner/repo.git`|
| **Auth method** | SSH key pair                       | Username + PAT or credential helper|
| **Setup**       | One-time SSH key setup             | Token-based, may need re-auth      |
| **Best for**    | Daily development, CI/CD          | Quick clones, firewall-restricted  |
| **Port**        | 22 (or 443 via `ssh.github.com`)  | 443                                |

**Switch a repo from HTTPS to SSH:**

```bash
git remote set-url origin git@github.com:owner/repo.git
```

**Switch a repo from SSH to HTTPS:**

```bash
git remote set-url origin https://github.com/owner/repo.git
```

**Verify current remote URL:**

```bash
git remote -v
```

### 5.3 Credential Helpers

```bash
# macOS — use Keychain
git config --global credential.helper osxkeychain

# Linux — cache credentials in memory for 1 hour
git config --global credential.helper 'cache --timeout=3600'

# Linux — store credentials in plaintext (less secure)
git config --global credential.helper store

# Windows — use Windows Credential Manager
git config --global credential.helper manager-core

# Clear cached credentials
git credential-cache exit

# Check current credential helper
git config --global credential.helper
```

### 5.4 Using SSH over Port 443 (Firewall Workaround)

If port 22 is blocked (e.g., corporate firewalls):

```bash
# Test if SSH over port 443 works
ssh -T -p 443 git@ssh.github.com

# If it works, configure it permanently
cat >> ~/.ssh/config << 'EOF'
Host github.com
  Hostname ssh.github.com
  Port 443
  User git
EOF
```

### 5.5 Common Git Errors and Fixes

**"fatal: not a git repository"**

```bash
# You're not in a Git repo. Initialize one or cd into the correct directory.
git init
```

**"error: failed to push some refs"**

```bash
# Remote has changes you don't have locally
git pull --rebase origin main
git push
```

**"fatal: refusing to merge unrelated histories"**

```bash
# Happens when merging repos with no common ancestor
git pull origin main --allow-unrelated-histories
```

**"Your branch is behind 'origin/main'"**

```bash
git pull origin main
# or
git fetch origin
git rebase origin/main
```

**Undo a `git push` (rewrite remote history — use with caution!)**

```bash
git reset --hard HEAD~1
git push --force-with-lease
```

### 5.6 Useful Diagnostic Commands

```bash
# Check Git version
git --version

# Check all remotes
git remote -v

# Check all branches (local + remote)
git branch -a

# Check tracking info
git branch -vv

# Verbose SSH connection debugging
ssh -vT git@github.com

# Check GitHub CLI auth
gh auth status

# Check SSH key fingerprint
ssh-keygen -l -f ~/.ssh/id_ed25519.pub
```

---

## Quick Reference Card

| Task                        | Command                                              |
|-----------------------------|------------------------------------------------------|
| Init repo                   | `git init && git branch -M main`                    |
| Clone repo                  | `git clone git@github.com:owner/repo.git`           |
| Stage all                   | `git add .`                                          |
| Commit                      | `git commit -m "message"`                            |
| Push                        | `git push -u origin main`                            |
| Pull                        | `git pull origin main`                               |
| New branch                  | `git checkout -b feature/name`                       |
| Merge                       | `git merge feature/name`                             |
| Rebase                      | `git rebase main`                                    |
| Stash                       | `git stash push -m "message"`                        |
| View log                    | `git log --oneline --graph -10`                      |
| Create PR                   | `gh pr create --title "Title" --body "Body"`         |
| List issues                 | `gh issue list`                                      |
| Test SSH                    | `ssh -T git@github.com`                              |
| Switch HTTPS→SSH            | `git remote set-url origin git@github.com:o/r.git`  |
