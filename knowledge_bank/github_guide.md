# GitHub Integration Knowledge Sheet

**CRITICAL RULE FOR AI AGENT:**
Whenever you are asked to connect to Git or GitHub, NEVER execute commands using placeholder values like `username`, `owner`, `repo`, `your-repo-name`, or `your_email@example.com`. 
If the user hasn't explicitly told you their actual GitHub username, repo name, or the exact Git URL, you MUST stop and ask them for it before running ANY `git remote` or `gh repo` commands!

GitHub repositories are managed via standard Git commands or the GitHub CLI (`gh`).

## GitHub CLI (`gh`) Commands

* **Authentication:**
  ```bash
  gh auth login
  ```
* **Status check:**
  ```bash
  gh auth status
  ```
* **Create a new repository:**
  ```bash
  gh repo create your-repo-name --public --source=. --remote=origin
  ```
* **Clone a repository:**
  ```bash
  gh repo clone owner/repo
  ```
* **Create and merge Pull Requests:**
  ```bash
  gh pr create --title "Your feature" --body "Details here"
  gh pr merge --merge
  ```
* **List issues:**
  ```bash
  gh issue list
  ```

## SSH Key Management
If the user asks you to connect to Git or test SSH, use your `run_command` tool to execute these steps automatically. DO NOT give them instructions to copy-paste.

1. **Verify connection:**
   ```bash
   ssh -T git@github.com
   ```
2. **If it fails with 'Host key verification failed.':**
   Add GitHub to known_hosts to fix it:
   ```bash
   mkdir -p ~/.ssh && ssh-keyscan github.com >> ~/.ssh/known_hosts
   ```
   Then run `ssh -T git@github.com` again.
3. **If it fails with 'Permission denied (publickey).':**
   Check for existing keys:
   ```bash
   ls -la ~/.ssh/id_*
   ```
   If no keys exist, generate a new one automatically without prompting the user for a passphrase (use `-N ""`):
   ```bash
   ssh-keygen -t ed25519 -C "your_email@example.com" -f ~/.ssh/id_ed25519 -N ""
   ```
   Then read the public key and present it to the user so they can add it to their GitHub account:
   ```bash
   cat ~/.ssh/id_ed25519.pub
   ```

## Standard Git Workflow

* **Initialize Repository:**
  ```bash
  git init
  git branch -M main
  ```
* **Status Check & Staging:**
  ```bash
  git status
  git add .
  ```
* **Committing Changes:**
  ```bash
  git commit -m "Your descriptive commit message"
  ```
* **Branching & Merging:**
  ```bash
  git checkout -b feature-branch    # Create and switch to new branch
  git checkout main                 # Switch back to main
  git merge feature-branch          # Merge changes into current branch
  git branch -d feature-branch      # Safe delete local branch
  ```
* **Pushing & Pulling Code:**
  ```bash
  git remote add origin git@github.com:username/repo.git
  git push -u origin main           # Set upstream and push to origin
  git pull origin main              # Pull latest updates
  ```
* **Resetting & Reverting:**
  ```bash
  git reset --soft HEAD~1           # Undo last commit, keep changes staged
  git reset --hard HEAD~1           # Undo last commit, discard all local changes!
  git checkout -- filename          # Discard changes in a specific file
  ```
* **Conflict Resolution:**
  If conflicts occur, run `git status` to find conflicting files, open them to resolve conflict marks (<<<<<<<, =======, >>>>>>>), stage the fixed files via `git add`, and finalize the merge via `git commit`.
