# Vercel Deployment Knowledge Sheet

Vercel provides a CLI to log in, link, configure, and deploy static frontend assets and serverless backends directly.

## Vercel CLI Commands

* **Login to Vercel:**
  ```bash
  vercel login
  ```
* **Link project to Vercel account:**
  ```bash
  vercel link
  ```
* **Run local development server:**
  ```bash
  vercel dev
  ```
* **Trigger a preview deploy:**
  ```bash
  vercel
  ```
* **Deploy to production:**
  ```bash
  vercel --prod
  ```
* **Inspect environment variables:**
  ```bash
  vercel env pull .env.local
  ```

## Serverless Configuration (`vercel.json`)
For projects requiring custom routing, headers, or serverless functions:
```json
{
  "version": 2,
  "builds": [
    { "src": "api/**/*.py", "use": "@vercel/python" },
    { "src": "package.json", "use": "@vercel/next" }
  ],
  "routes": [
    { "src": "/api/(.*)", "dest": "api/$1.py" }
  ]
}
```
Ensure Python functions inside `api/` expose a WSGI/ASGI handler or a Flask `app` instance.
