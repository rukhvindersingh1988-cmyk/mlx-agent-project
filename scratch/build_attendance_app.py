import sys, time, os
sys.path.insert(0, 'backend')
from tools import invoke_subagent

print("🚀 Launching Subagents to build the Attendance Mobile App...")
print("Goal: Build a responsive, gorgeous HTML5/JS mobile-optimized web application for attendance tracking.")
print("Requirements: Camera capture (image), geolocation (latitude/longitude), and local storage database.")

# 1. Spawn Architect to build the core mobile app index.html
invoke_subagent("Architect", 
    "Build a gorgeous mobile-optimized web application index.html for Attendance tracking. "
    "Features: Camera stream capture block, 'Take Attendance' button, Geolocation coordinate acquisition (latitude/longitude), "
    "attendance history dashboard showing captured face photo, location coordinates, and timestamps. "
    "Aesthetics: Sleek glassmorphic dark theme, purple/cyan glows, Outfit & Inter fonts, smooth animations. "
    "Save the code to user_projects/mobile_app_attendance/index.html")

# 2. Spawn DevOps to build the backend server.py to handle image uploads and store data
invoke_subagent("DevOps",
    "Build a lightweight FastAPI backend server in Python to handle the attendance submissions. "
    "Endpoints: POST /api/attendance (receives JSON payload with base64 image data, latitude, longitude, and timestamp) "
    "and GET /api/attendance (returns list of all submissions). Use a lightweight sqlite database or local JSON database. "
    "Save the code to user_projects/mobile_app_attendance/server.py")

# 3. Spawn DocWriter to document how to run the app
invoke_subagent("DocWriter",
    "Write a detailed README.md for the mobile attendance app. Explain how to run the FastAPI backend, "
    "enable camera/location permissions in Chrome/Safari on mobile devices, and run locally. "
    "Save the code to user_projects/mobile_app_attendance/README.md")

print("✅ Subagents spawned and running in parallel! Monitoring directory user_projects/mobile_app_attendance/")
