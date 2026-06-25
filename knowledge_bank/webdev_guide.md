# Web Development Guide

## HTML / CSS / JavaScript Basics

### Create a modern styled page
```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>My App</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet" />
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: 'Inter', sans-serif; background: #0f0f0f; color: #e5e5e5; }
  </style>
</head>
<body>
  <h1>Hello World</h1>
  <script src="app.js"></script>
</body>
</html>
```

## Running a Local Dev Server
```bash
# Python HTTP server (no install needed)
python3 -m http.server 3000

# Node.js (with npm installed)
npx serve .

# Vite (React/Vue)
npm create vite@latest my-app -- --template react
cd my-app && npm install && npm run dev
```

## React Quick Start (Vite)
```bash
npm create vite@latest my-app -- --template react
cd my-app
npm install
npm run dev
```

## CSS Glassmorphism (Dark Theme)
```css
.card {
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 16px;
  backdrop-filter: blur(10px);
  padding: 24px;
}
```

## Fetch API (JavaScript)
```javascript
const res = await fetch('/api/endpoint', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ key: 'value' })
});
const data = await res.json();
```

## WebSocket (JavaScript)
```javascript
const ws = new WebSocket('ws://localhost:8000/ws');
ws.onopen = () => ws.send(JSON.stringify({ message: 'hello' }));
ws.onmessage = (e) => console.log(JSON.parse(e.data));
```
