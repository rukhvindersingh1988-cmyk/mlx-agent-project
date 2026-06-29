# Mobile Attendance App

## Table of Contents
1. [Introduction](#introduction)
2. [Running the FastAPI Backend](#running-the-fastapi-backend)
3. [Enabling Camera/Location Permissions](#enabling-camerolocation-permissions)
4. [Running the App Locally](#running-the-app-locally)
5. [Troubleshooting](#troubleshooting)

## Introduction
The Mobile Attendance App is a web-based application designed to track attendance using mobile devices. The app utilizes the device's camera and location services to verify user presence.

## Running the FastAPI Backend
To run the FastAPI backend, follow these steps:
1. Install the required dependencies by running `pip install fastapi uvicorn`
2. Navigate to the project directory using `cd user_projects/mobile_app_attendance`
3. Run the FastAPI server using `uvicorn main:app --host 0.0.0.0 --port 8000`

## Enabling Camera/Location Permissions
To enable camera and location permissions in Chrome/Safari on mobile devices, follow these steps:
### Chrome:
1. Open Chrome and navigate to `chrome://settings/`
2. Scroll down to the 'Advanced' section and click on 'Site Settings'
3. Click on 'Camera' and select 'Allow' for the mobile attendance app
4. Repeat steps 2-3 for 'Location'
### Safari:
1. Open Safari and navigate to `safari://settings/`
2. Scroll down to the 'Privacy & Security' section and click on 'Camera'
3. Select 'Allow' for the mobile attendance app
4. Repeat steps 2-3 for 'Location'

## Running the App Locally
To run the app locally, follow these steps:
1. Connect your mobile device to the same network as your computer
2. Open a web browser on your mobile device and navigate to `http://<computer-ip>:8000`
3. Replace `<computer-ip>` with the IP address of your computer
4. The mobile attendance app should now be accessible on your mobile device

## Troubleshooting
If you encounter any issues while running the app, check the following:
* Ensure that the FastAPI backend is running and accessible
* Verify that camera and location permissions are enabled in your web browser
* Check the console logs for any error messages