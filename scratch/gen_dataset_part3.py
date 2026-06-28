#!/usr/bin/env python3
"""Generate JSONL training data for MLX AI coding agent (Part 3).

Categories:
- final_answer (20 examples)
- grep_search (10 examples)
- web_search (15 examples)
- search_knowledge_bank (10 examples)

Total: 55 examples
"""

import json


def make_line(user_content: str, thought: str, tool: str, args: dict) -> str:
    """Build a single JSONL line with user/assistant messages."""
    tool_call_json = json.dumps({"tool": tool, "args": args})
    assistant_content = f"<thought>\n{thought}\n</thought>\n<tool_call>\n{tool_call_json}\n</tool_call>"
    return json.dumps({
        "messages": [
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": assistant_content},
        ]
    })


def gen_final_answer():
    """Generate 20 final_answer examples."""
    examples = [
        (
            "What is Python?",
            "The user is asking a general knowledge question about Python. I can answer this directly.",
            "Python is a high-level, interpreted programming language known for its readability and versatility. It supports multiple paradigms including procedural, object-oriented, and functional programming. Python is widely used in web development, data science, machine learning, and scripting."
        ),
        (
            "Hello",
            "The user is greeting me. I should respond with a friendly greeting.",
            "Hello! I'm your AI coding assistant. How can I help you today?"
        ),
        (
            "Thanks for your help",
            "The user is expressing gratitude. I should respond politely.",
            "You're welcome! Feel free to ask if you need anything else."
        ),
        (
            "What is a REST API?",
            "The user wants to know about REST APIs. This is a conceptual question I can answer directly.",
            "A REST API (Representational State Transfer) is an architectural style for building web services. It uses standard HTTP methods like GET, POST, PUT, and DELETE to perform operations on resources identified by URLs. REST APIs are stateless, meaning each request contains all the information needed to process it."
        ),
        (
            "Explain what JSON is",
            "The user is asking about JSON. I can explain this directly without any tool.",
            "JSON (JavaScript Object Notation) is a lightweight data-interchange format that's easy for humans to read and write. It uses key-value pairs and arrays to represent structured data. Despite its name, JSON is language-independent and is the most common format for API communication and configuration files."
        ),
        (
            "What is git branching?",
            "The user wants to understand git branching. This is a conceptual question.",
            "Git branching allows you to diverge from the main line of development and work independently without affecting other branches. Each branch is a lightweight pointer to a specific commit. Branches are commonly used for developing features, fixing bugs, or experimenting, and can later be merged back into the main branch."
        ),
        (
            "How does CSS flexbox work?",
            "The user is asking about CSS flexbox layout. I can explain this directly.",
            "CSS Flexbox is a one-dimensional layout model that distributes space among items in a container. You enable it with `display: flex` on a parent element, then control alignment with properties like `justify-content`, `align-items`, and `flex-direction`. Child items can grow, shrink, or have a fixed basis size using the `flex` shorthand property."
        ),
        (
            "What is a Docker container?",
            "The user wants to know about Docker containers. This is a general knowledge question.",
            "A Docker container is a lightweight, standalone executable package that includes everything needed to run an application: code, runtime, libraries, and system tools. Containers are isolated from each other and the host system, but share the OS kernel, making them much more efficient than virtual machines. They ensure consistent behavior across development, testing, and production environments."
        ),
        (
            "Explain async/await in JavaScript",
            "The user wants to understand async/await in JavaScript. I can answer directly.",
            "Async/await is syntactic sugar over JavaScript Promises that makes asynchronous code look synchronous. An `async` function always returns a Promise, and `await` pauses execution inside that function until the Promise resolves. This eliminates callback nesting and makes error handling with try/catch straightforward."
        ),
        (
            "What is SQL injection?",
            "The user is asking about SQL injection, a security concept. I should explain it clearly.",
            "SQL injection is a security vulnerability where an attacker inserts malicious SQL code into input fields that get executed by the database. For example, entering `' OR 1=1 --` in a login form could bypass authentication. It's prevented by using parameterized queries, prepared statements, and input validation."
        ),
        (
            "How does HTTP work?",
            "The user wants a basic explanation of HTTP. This is a conceptual question.",
            "HTTP (HyperText Transfer Protocol) is a request-response protocol used for communication between web clients and servers. A client sends an HTTP request with a method (GET, POST, etc.), headers, and optional body, and the server responds with a status code, headers, and a response body. It operates on top of TCP and is stateless by default."
        ),
        (
            "What is an API key?",
            "The user is asking about API keys. I can explain this directly.",
            "An API key is a unique identifier used to authenticate requests to an API service. It acts like a password that identifies the calling application or user. API keys should be kept secret, stored in environment variables, and never committed to version control."
        ),
        (
            "Explain recursion",
            "The user wants to understand recursion. I should explain it with an example.",
            "Recursion is when a function calls itself to solve a problem by breaking it into smaller sub-problems. Every recursive function needs a base case to stop the recursion. For example, calculating factorial: `def factorial(n): return 1 if n <= 1 else n * factorial(n - 1)`. The call stack unwinds once the base case is reached."
        ),
        (
            "What's the difference between let and const?",
            "The user wants to know the difference between let and const in JavaScript.",
            "Both `let` and `const` are block-scoped variable declarations in JavaScript introduced in ES6. `let` allows reassignment after declaration, while `const` creates a read-only reference that cannot be reassigned. However, `const` objects and arrays can still have their contents mutated — only the binding is immutable."
        ),
        (
            "How do environment variables work?",
            "The user is asking about environment variables. I can explain this directly.",
            "Environment variables are key-value pairs stored in the operating system's environment that processes can read at runtime. They're commonly used to store configuration like API keys, database URLs, and feature flags. In Python you access them via `os.environ`, and in Node.js via `process.env`."
        ),
        (
            "What is a webhook?",
            "The user wants to know about webhooks. This is a conceptual question.",
            "A webhook is an HTTP callback that sends real-time data to a specified URL when an event occurs. Unlike polling, where you repeatedly check for updates, webhooks push data to your server automatically. Common examples include GitHub notifying your CI server of new commits, or Stripe alerting your app of a payment."
        ),
        (
            "Explain OAuth",
            "The user wants to understand OAuth. I can explain this directly.",
            "OAuth is an authorization framework that lets third-party applications access a user's resources without exposing their credentials. It works by issuing access tokens after the user grants permission through the resource owner's authorization server. OAuth 2.0 is the current standard, commonly seen as 'Sign in with Google/GitHub' buttons."
        ),
        (
            "What's a load balancer?",
            "The user is asking about load balancers. This is an infrastructure concept.",
            "A load balancer distributes incoming network traffic across multiple servers to ensure no single server is overwhelmed. It improves application availability, reliability, and performance. Common algorithms include round-robin, least connections, and weighted distribution. Popular load balancers include Nginx, HAProxy, and cloud-native options like AWS ALB."
        ),
        (
            "How does DNS work?",
            "The user wants to understand DNS. I can explain the basics.",
            "DNS (Domain Name System) translates human-readable domain names like `example.com` into IP addresses that computers use to identify each other. When you type a URL, your browser queries DNS resolvers, which check a hierarchy of servers (root, TLD, authoritative) to find the corresponding IP address. Results are cached at multiple levels to speed up future lookups."
        ),
        (
            "What is WebSocket?",
            "The user is asking about WebSocket. This is a web technology question.",
            "WebSocket is a communication protocol that provides full-duplex, persistent connections between a client and server over a single TCP connection. Unlike HTTP's request-response model, WebSocket allows both sides to send data at any time without re-establishing the connection. It's commonly used for real-time applications like chat, live notifications, and collaborative editing."
        ),
    ]
    for user_msg, thought, answer in examples:
        yield make_line(user_msg, thought, "final_answer", {"message": answer})


def gen_grep_search():
    """Generate 10 grep_search examples."""
    examples = [
        (
            "Find where we define load_model",
            "The user wants to find the definition of load_model. I should search for the function definition pattern.",
            {"query": "def load_model", "search_path": "."}
        ),
        (
            "Search for TODO comments",
            "The user wants to find all TODO comments in the codebase. I'll search broadly.",
            {"query": "TODO", "search_path": "."}
        ),
        (
            "Find all import statements in agent.py",
            "The user wants to see imports in a specific file. I should search within that file.",
            {"query": "import", "search_path": "backend/agent.py"}
        ),
        (
            "Where is AGENT_STATE defined?",
            "The user is looking for where AGENT_STATE is defined. I should search in the backend directory.",
            {"query": "AGENT_STATE", "search_path": "backend"}
        ),
        (
            "Find error handling code",
            "The user wants to find exception handling patterns. I'll search for except Exception blocks.",
            {"query": "except Exception", "search_path": "."}
        ),
        (
            "Search for websocket references",
            "The user wants to find websocket-related code. I should do a case-insensitive search since it could be WebSocket or websocket.",
            {"query": "websocket", "search_path": "backend", "case_insensitive": True}
        ),
        (
            "Find all print statements in tools",
            "The user wants to find print statements in the tools file. I'll search for the print function call pattern.",
            {"query": "print(", "search_path": "backend/tools.py"}
        ),
        (
            "Where do we use json.loads?",
            "The user wants to find usages of json.loads in the backend. I'll search for that exact string.",
            {"query": "json.loads", "search_path": "backend"}
        ),
        (
            "Find the main function",
            "The user is looking for the main function entry point. I should search for def main across the project.",
            {"query": "def main", "search_path": "."}
        ),
        (
            "Search for API key references",
            "The user wants to find all references to API keys. I should search case-insensitively since it could appear as api_key, API_KEY, etc.",
            {"query": "api_key", "search_path": ".", "case_insensitive": True}
        ),
    ]
    for user_msg, thought, args in examples:
        yield make_line(user_msg, thought, "grep_search", args)


def gen_web_search():
    """Generate 15 web_search examples."""
    examples = [
        (
            "Search how to install tensorflow on mac",
            "The user wants installation instructions for TensorFlow on macOS. I should search the web for this.",
            {"query": "how to install tensorflow on mac"}
        ),
        (
            "Look up React 19 new features",
            "The user wants to know about React 19 features. I need to search the web for the latest information.",
            {"query": "React 19 new features"}
        ),
        (
            "Search for python asyncio tutorial",
            "The user wants a tutorial on Python asyncio. Let me search the web for a good resource.",
            {"query": "python asyncio tutorial"}
        ),
        (
            "Find npm package for image processing",
            "The user needs an npm package for image processing. I should search for popular options.",
            {"query": "best npm package for image processing"}
        ),
        (
            "Search how to fix CORS error",
            "The user is dealing with a CORS error. Let me search for solutions.",
            {"query": "how to fix CORS error"}
        ),
        (
            "Look up kubernetes vs docker swarm",
            "The user wants a comparison between Kubernetes and Docker Swarm. I'll search for this.",
            {"query": "kubernetes vs docker swarm comparison"}
        ),
        (
            "Search for tailwind css documentation",
            "The user wants to find Tailwind CSS docs. I'll search the web.",
            {"query": "tailwind css documentation"}
        ),
        (
            "Find how to use SQLAlchemy",
            "The user wants to learn about SQLAlchemy. I should search for a guide or tutorial.",
            {"query": "how to use SQLAlchemy python tutorial"}
        ),
        (
            "Search apple silicon mlx benchmarks",
            "The user wants MLX benchmark results on Apple Silicon. Let me search for this.",
            {"query": "apple silicon mlx framework benchmarks"}
        ),
        (
            "Look up latest Next.js version",
            "The user wants to know the latest Next.js version. I need to search for current release info.",
            {"query": "latest Next.js version release"}
        ),
        (
            "Search for FastAPI tutorial",
            "The user wants a FastAPI tutorial. I'll search the web for one.",
            {"query": "FastAPI python tutorial getting started"}
        ),
        (
            "Find how to setup PostgreSQL on macOS",
            "The user wants to set up PostgreSQL on macOS. I should search for installation instructions.",
            {"query": "how to setup PostgreSQL on macOS"}
        ),
        (
            "Search for GraphQL vs REST comparison",
            "The user wants to compare GraphQL and REST. I'll search for a good comparison.",
            {"query": "GraphQL vs REST API comparison"}
        ),
        (
            "Look up how to use Redis caching",
            "The user wants to learn about Redis caching. Let me search for a practical guide.",
            {"query": "how to use Redis caching tutorial"}
        ),
        (
            "Search for WebAssembly getting started",
            "The user wants to get started with WebAssembly. I'll search for beginner resources.",
            {"query": "WebAssembly getting started tutorial"}
        ),
    ]
    for user_msg, thought, args in examples:
        yield make_line(user_msg, thought, "web_search", args)


def gen_search_knowledge_bank():
    """Generate 10 search_knowledge_bank examples."""
    examples = [
        (
            "What is BigQuery partitioning?",
            "The user is asking about BigQuery partitioning. Let me check the knowledge bank for relevant documentation.",
            {"query": "bigquery partitioning"}
        ),
        (
            "How to deploy to Vercel?",
            "The user wants deployment instructions for Vercel. Let me search the knowledge bank.",
            {"query": "vercel deployment"}
        ),
        (
            "Firebase security rules",
            "The user is asking about Firebase security rules. I should check the knowledge bank for guidance.",
            {"query": "firebase security rules"}
        ),
        (
            "How to setup GitHub SSH?",
            "The user needs help setting up SSH for GitHub. Let me search the knowledge bank.",
            {"query": "github ssh setup"}
        ),
        (
            "Python list comprehension",
            "The user wants to learn about Python list comprehensions. Let me check the knowledge bank.",
            {"query": "python list comprehension"}
        ),
        (
            "CSS grid layout",
            "The user is asking about CSS grid. Let me search the knowledge bank for documentation.",
            {"query": "css grid layout"}
        ),
        (
            "macOS terminal shortcuts",
            "The user wants terminal shortcuts for macOS. Let me search the knowledge bank.",
            {"query": "macos terminal shortcuts"}
        ),
        (
            "MLX model quantization",
            "The user is asking about MLX model quantization. Let me check the knowledge bank for details.",
            {"query": "mlx model quantization"}
        ),
        (
            "Node.js event loop",
            "The user wants to understand the Node.js event loop. Let me search the knowledge bank.",
            {"query": "nodejs event loop"}
        ),
        (
            "Pandas dataframe operations",
            "The user is asking about Pandas dataframe operations. Let me check the knowledge bank.",
            {"query": "pandas dataframe"}
        ),
    ]
    for user_msg, thought, args in examples:
        yield make_line(user_msg, thought, "search_knowledge_bank", args)


def main():
    generators = [
        gen_final_answer(),
        gen_grep_search(),
        gen_web_search(),
        gen_search_knowledge_bank(),
    ]
    for gen in generators:
        for line in gen:
            print(line)


if __name__ == "__main__":
    main()
