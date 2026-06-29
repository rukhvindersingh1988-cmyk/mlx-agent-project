from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import base64
import json
import os
import time

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Attendance(BaseModel):
    image: str
    latitude: float
    longitude: float
    timestamp: str

# Local JSON database file fallback
LOCAL_DB = "attendance_db.json"

def save_local(attendance_dict: dict):
    data = []
    if os.path.exists(LOCAL_DB):
        try:
            with open(LOCAL_DB, "r") as f:
                data = json.load(f)
        except:
            pass
    data.append(attendance_dict)
    with open(LOCAL_DB, "w") as f:
        json.dump(data, f, indent=2)

def sync_to_sheets(attendance_dict: dict):
    # If a real credentials.json exists, we try to append row to Google Sheets
    cred_path = "credentials.json"
    if not os.path.exists(cred_path) or "EXAMPLE/KEY" in open(cred_path).read():
        print("[Sheets API] Skipping cloud sheets sync (using placeholder credentials). Saved locally.")
        return False
        
    try:
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build
        
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_file(cred_path, scopes=scopes)
        service = build("sheets", "v4", credentials=creds)
        
        # Target Google Sheet ID (Must be created and shared with the client_email)
        # Shared Sheet ID should be stored in secrets.json or environment
        sheet_id = os.environ.get("GOOGLE_SHEET_ID", "1tS95ZJvL7c6X-EXAMPLE-SHEET-ID")
        
        range_name = "Sheet1!A:D"
        row_values = [
            [
                attendance_dict["timestamp"],
                attendance_dict["latitude"],
                attendance_dict["longitude"],
                attendance_dict["image"][:100] + "... (truncated)"
            ]
        ]
        
        body = {"values": row_values}
        service.spreadsheets().values().append(
            spreadsheetId=sheet_id,
            range=range_name,
            valueInputOption="USER_ENTERED",
            body=body
        ).execute()
        print("[Sheets API] Successfully appended record to Google Sheet!")
        return True
    except Exception as e:
        print(f"[Sheets API] Error syncing to sheets: {e}")
        return False

@app.post("/api/attendance")
async def submit_attendance(attendance: Attendance):
    attendance_dict = attendance.dict()
    
    # Save locally
    save_local(attendance_dict)
    
    # Try syncing to Google Sheets
    sheets_synced = sync_to_sheets(attendance_dict)
    
    return JSONResponse(content={
        "status": "success",
        "message": "Attendance recorded successfully!",
        "sheets_synced": sheets_synced
    })

@app.get("/api/attendance")
async def get_attendance():
    data = []
    if os.path.exists(LOCAL_DB):
        try:
            with open(LOCAL_DB, "r") as f:
                data = json.load(f)
        except:
            pass
    return JSONResponse(content=data)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
