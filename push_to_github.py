import json
import subprocess
import sys

def main():
    print("Reading secrets.json...")
    try:
        with open("secrets.json", "r") as f:
            data = json.load(f)
            token = data.get("github_token")
    except Exception as e:
        print(f"Error reading secrets.json: {e}")
        sys.exit(1)

    if not token:
        print("github_token not found in secrets.json")
        sys.exit(1)

    print("Authenticating with GitHub CLI...")
    p1 = subprocess.run(
        ["gh", "auth", "login", "--with-token"],
        input=token,
        text=True,
        capture_output=True
    )
    
    if p1.returncode != 0:
        print(f"Auth failed: {p1.stderr}")
        sys.exit(1)
        
    print("Authentication successful!")
    print("Creating repository and pushing...")
    
    p2 = subprocess.run([
        "gh", "repo", "create", 
        "mlx-agent-project", 
        "--public", 
        "--source=.", 
        "--remote=origin", 
        "--push"
    ], text=True)
    
    if p2.returncode == 0:
        print("\nSuccessfully created repository and pushed code!")
    else:
        print("\nFailed to create/push repository.")

if __name__ == "__main__":
    main()
