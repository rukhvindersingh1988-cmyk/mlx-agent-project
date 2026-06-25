# Node.js & npm Guide

## CRITICAL RULE FOR AI AGENT:
When user asks to create a web app, JS project, or install npm packages,
use your `run_command` tool to execute directly. Do NOT give instructions.

## Node.js Basics
```bash
node --version               # Check Node.js version
npm --version                # Check npm version
node script.js               # Run a JS script
```

## npm Package Management
```bash
npm init -y                  # Initialize a new project
npm install <package>        # Install a dependency
npm install -D <package>     # Install dev dependency
npm install                  # Install all from package.json
npm run <script>             # Run a script
npm run dev                  # Start dev server (most frameworks)
npm run build                # Build for production
npm start                    # Start production server
npm list                     # List installed packages
npm outdated                 # Check for outdated packages
npm update                   # Update all packages
```

## Creating Projects
```bash
# React with Vite (recommended)
npm create vite@latest my-app -- --template react
cd my-app && npm install && npm run dev

# Next.js (full-stack React)
npx create-next-app@latest my-app --yes
cd my-app && npm run dev

# Plain HTML/JS with live server
npm install -g live-server
live-server

# Express.js API server
mkdir my-api && cd my-api
npm init -y && npm install express
```

## Express.js Quick Server
```javascript
const express = require('express');
const app = express();

app.use(express.json());

app.get('/', (req, res) => {
  res.json({ message: 'Hello World!' });
});

app.listen(3000, () => console.log('Server running on http://localhost:3000'));
```

## package.json Scripts
```json
{
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "start": "node server.js",
    "test": "jest"
  }
}
```
