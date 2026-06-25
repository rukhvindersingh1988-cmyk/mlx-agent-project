# Python & Coding Guide

## Python Best Practices
- Always use virtual environments: `python3 -m venv .venv && source .venv/bin/activate`
- Install packages: `pip install <package>` or from file: `pip install -r requirements.txt`
- Run a script: `python3 script.py`
- Check Python version: `python3 --version`

## Debugging Python
- Show traceback: `python3 -u script.py 2>&1`
- Check if a module exists: `python3 -c "import <module>; print('OK')"`
- List installed packages: `pip list` or `pip show <package>`

## Common Python Patterns
```python
# Read a file
with open("file.txt", "r") as f:
    content = f.read()

# Write a file
with open("file.txt", "w") as f:
    f.write("Hello World")

# JSON
import json
data = json.loads('{"key": "value"}')
json.dumps(data, indent=2)

# Run subprocess
import subprocess
result = subprocess.run(["git", "status"], capture_output=True, text=True)
print(result.stdout)
```

## FastAPI Quick Start
```python
from fastapi import FastAPI
app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}
```
Run with: `uvicorn main:app --reload`

## Pip Requirements
```bash
pip freeze > requirements.txt       # Save dependencies
pip install -r requirements.txt     # Install from file
pip install --upgrade <package>     # Upgrade package
```
