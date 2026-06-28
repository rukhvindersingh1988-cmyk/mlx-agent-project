#!/usr/bin/env python3
"""Generate JSONL training data for read_file and write_file tool calls."""

import json


def emit(user_msg: str, thought: str, tool: str, args: dict) -> None:
    """Print one JSONL line."""
    assistant = (
        f"<thought>\n{thought}\n</thought>\n"
        f"<tool_call>\n{json.dumps({'tool': tool, 'args': args})}\n</tool_call>"
    )
    print(json.dumps({
        "messages": [
            {"role": "user", "content": user_msg},
            {"role": "assistant", "content": assistant},
        ]
    }))


# ── read_file (15 examples) ────────────────────────────────────────────

emit(
    "Show me app.py",
    "The user wants to view the main application file.",
    "read_file", {"path": "app.py"},
)

emit(
    "Read the README",
    "The user wants to read the project README.",
    "read_file", {"path": "README.md"},
)

emit(
    "What's in the gitignore?",
    "The user wants to inspect the gitignore configuration.",
    "read_file", {"path": ".gitignore"},
)

emit(
    "Show me the server code",
    "The user wants to view the backend server source.",
    "read_file", {"path": "backend/server.py"},
)

emit(
    "Read the license",
    "The user wants to check the project license file.",
    "read_file", {"path": "LICENSE"},
)

emit(
    "Show the run script",
    "The user wants to see the shell script used to run the project.",
    "read_file", {"path": "run.sh"},
)

emit(
    "What does the agent map look like?",
    "The user wants to inspect the agent map configuration.",
    "read_file", {"path": "AGENT_MAP.yaml"},
)

emit(
    "Read the changelog",
    "The user wants to review the project changelog.",
    "read_file", {"path": "CHANGELOG.md"},
)

emit(
    "Show me tools.py",
    "The user wants to view the tools module in the backend.",
    "read_file", {"path": "backend/tools.py"},
)

emit(
    "What's in the security file?",
    "The user wants to read the security policy document.",
    "read_file", {"path": "SECURITY.md"},
)

emit(
    "Read the environment example",
    "The user wants to see the example environment variable configuration.",
    "read_file", {"path": ".env.example"},
)

emit(
    "Show the mlx runner code",
    "The user wants to view the MLX runner module.",
    "read_file", {"path": "backend/mlx_runner.py"},
)

emit(
    "Read the contributing guide",
    "The user wants to read the contributing guidelines.",
    "read_file", {"path": "CONTRIBUTING.md"},
)

emit(
    "What does bootstrap instructions say?",
    "The user wants to read the bootstrap instructions document.",
    "read_file", {"path": "BOOTSTRAP_INSTRUCTIONS.md"},
)

emit(
    "Show me the test suite",
    "The user wants to view the test suite file.",
    "read_file", {"path": "test_suite.py"},
)

# ── write_file (15 examples) ───────────────────────────────────────────

emit(
    "Create a hello world HTML page",
    "The user wants a basic HTML5 hello world page. I'll create one with minimal markup.",
    "write_file", {
        "path": "user_projects/hello/index.html",
        "content": (
            "<!DOCTYPE html>\n"
            "<html lang=\"en\">\n"
            "<head>\n"
            "  <meta charset=\"UTF-8\">\n"
            "  <title>Hello World</title>\n"
            "</head>\n"
            "<body>\n"
            "  <h1>Hello, World!</h1>\n"
            "</body>\n"
            "</html>"
        ),
    },
)

emit(
    "Write a python script to calculate fibonacci",
    "The user wants a Fibonacci calculator script in Python.",
    "write_file", {
        "path": "user_projects/fibonacci.py",
        "content": (
            "def fibonacci(n):\n"
            "    a, b = 0, 1\n"
            "    for _ in range(n):\n"
            "        a, b = b, a + b\n"
            "    return a\n"
            "\n"
            "if __name__ == \"__main__\":\n"
            "    for i in range(10):\n"
            "        print(f\"fib({i}) = {fibonacci(i)}\")"
        ),
    },
)

emit(
    "Create a simple CSS file",
    "The user wants a basic CSS stylesheet. I'll create one with common resets and styles.",
    "write_file", {
        "path": "user_projects/style.css",
        "content": (
            "*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }\n"
            "body { font-family: system-ui, sans-serif; line-height: 1.6; color: #333; }\n"
            "h1 { font-size: 2rem; margin-bottom: 1rem; }\n"
            "p { margin-bottom: 0.75rem; }\n"
            "a { color: #0066cc; text-decoration: none; }\n"
            "a:hover { text-decoration: underline; }"
        ),
    },
)

emit(
    "Make a bash script to backup files",
    "The user wants a shell script for backing up files to a timestamped directory.",
    "write_file", {
        "path": "user_projects/backup.sh",
        "content": (
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "SRC=\"${1:-.}\"\n"
            "DEST=\"backup_$(date +%Y%m%d_%H%M%S)\"\n"
            "mkdir -p \"$DEST\"\n"
            "cp -r \"$SRC\"/* \"$DEST/\"\n"
            "echo \"Backed up $SRC to $DEST\""
        ),
    },
)

emit(
    "Create a JSON config file",
    "The user wants a sample JSON configuration file.",
    "write_file", {
        "path": "user_projects/config.json",
        "content": json.dumps({
            "app_name": "my_app",
            "version": "1.0.0",
            "debug": False,
            "port": 8080,
            "database": {"host": "localhost", "port": 5432, "name": "app_db"},
        }, indent=2),
    },
)

emit(
    "Write a todo list app",
    "The user wants a simple JavaScript todo list application.",
    "write_file", {
        "path": "user_projects/todo/app.js",
        "content": (
            "const todos = [];\n"
            "function addTodo(text) {\n"
            "  todos.push({ text, done: false });\n"
            "}\n"
            "function toggleTodo(index) {\n"
            "  todos[index].done = !todos[index].done;\n"
            "}\n"
            "function listTodos() {\n"
            "  return todos.map((t, i) => `${i}: [${t.done ? 'x' : ' '}] ${t.text}`);\n"
            "}\n"
            "module.exports = { addTodo, toggleTodo, listTodos };"
        ),
    },
)

emit(
    "Create a .env file",
    "The user wants a sample environment file with common variables.",
    "write_file", {
        "path": "user_projects/.env",
        "content": (
            "APP_ENV=development\n"
            "APP_PORT=3000\n"
            "DB_HOST=localhost\n"
            "DB_PORT=5432\n"
            "DB_NAME=myapp\n"
            "SECRET_KEY=change-me-in-production"
        ),
    },
)

emit(
    "Write a Makefile",
    "The user wants a basic Makefile for a Python project.",
    "write_file", {
        "path": "user_projects/Makefile",
        "content": (
            ".PHONY: install test lint run clean\n"
            "install:\n"
            "\tpip install -r requirements.txt\n"
            "test:\n"
            "\tpython -m pytest tests/\n"
            "lint:\n"
            "\tflake8 src/\n"
            "run:\n"
            "\tpython src/main.py\n"
            "clean:\n"
            "\tfind . -name '*.pyc' -delete"
        ),
    },
)

emit(
    "Create a Dockerfile",
    "The user wants a Dockerfile for a Python application.",
    "write_file", {
        "path": "user_projects/Dockerfile",
        "content": (
            "FROM python:3.11-slim\n"
            "WORKDIR /app\n"
            "COPY requirements.txt .\n"
            "RUN pip install --no-cache-dir -r requirements.txt\n"
            "COPY . .\n"
            "EXPOSE 8080\n"
            "CMD [\"python\", \"main.py\"]"
        ),
    },
)

emit(
    "Write a simple REST API",
    "The user wants a basic Flask REST API. I'll create a minimal server with a couple of endpoints.",
    "write_file", {
        "path": "user_projects/api/server.py",
        "content": (
            "from flask import Flask, jsonify, request\n"
            "\n"
            "app = Flask(__name__)\n"
            "items = []\n"
            "\n"
            "@app.route('/items', methods=['GET'])\n"
            "def get_items():\n"
            "    return jsonify(items)\n"
            "\n"
            "@app.route('/items', methods=['POST'])\n"
            "def add_item():\n"
            "    items.append(request.json)\n"
            "    return jsonify(request.json), 201\n"
            "\n"
            "if __name__ == '__main__':\n"
            "    app.run(port=5000)"
        ),
    },
)

emit(
    "Create a markdown readme for my project",
    "The user wants a README template for their project.",
    "write_file", {
        "path": "user_projects/my_project/README.md",
        "content": (
            "# My Project\n"
            "\n"
            "A brief description of what this project does.\n"
            "\n"
            "## Installation\n"
            "```bash\n"
            "pip install -r requirements.txt\n"
            "```\n"
            "\n"
            "## Usage\n"
            "```bash\n"
            "python main.py\n"
            "```\n"
            "\n"
            "## License\n"
            "MIT"
        ),
    },
)

emit(
    "Write a CSS dark theme",
    "The user wants a dark theme CSS stylesheet.",
    "write_file", {
        "path": "user_projects/dark_theme.css",
        "content": (
            ":root {\n"
            "  --bg: #1a1a2e;\n"
            "  --surface: #16213e;\n"
            "  --text: #e0e0e0;\n"
            "  --accent: #0f3460;\n"
            "  --highlight: #e94560;\n"
            "}\n"
            "body { background: var(--bg); color: var(--text); font-family: system-ui; }\n"
            "a { color: var(--highlight); }\n"
            ".card { background: var(--surface); padding: 1rem; border-radius: 8px; }"
        ),
    },
)

emit(
    "Create a requirements.txt",
    "The user wants a Python requirements file with common dependencies.",
    "write_file", {
        "path": "user_projects/requirements.txt",
        "content": (
            "flask>=3.0\n"
            "requests>=2.31\n"
            "python-dotenv>=1.0\n"
            "pytest>=8.0\n"
            "gunicorn>=21.2"
        ),
    },
)

emit(
    "Write a Node.js express server",
    "The user wants a basic Express.js server with a few routes.",
    "write_file", {
        "path": "user_projects/express/server.js",
        "content": (
            "const express = require('express');\n"
            "const app = express();\n"
            "app.use(express.json());\n"
            "\n"
            "app.get('/', (req, res) => res.json({ message: 'Hello!' }));\n"
            "app.get('/health', (req, res) => res.json({ status: 'ok' }));\n"
            "\n"
            "const PORT = process.env.PORT || 3000;\n"
            "app.listen(PORT, () => console.log(`Server running on port ${PORT}`));"
        ),
    },
)

emit(
    "Create a gitignore for python",
    "The user wants a .gitignore tailored for Python projects.",
    "write_file", {
        "path": "user_projects/.gitignore",
        "content": (
            "__pycache__/\n"
            "*.py[cod]\n"
            ".env\n"
            ".venv/\n"
            "dist/\n"
            "*.egg-info/\n"
            ".pytest_cache/\n"
            ".mypy_cache/"
        ),
    },
)
