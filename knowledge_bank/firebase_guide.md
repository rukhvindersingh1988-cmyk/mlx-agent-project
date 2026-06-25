# Firebase Integration Knowledge Sheet

Firebase configurations are managed via the Firebase CLI (`firebase-tools`) and Python/Node SDKs.

## Firebase CLI Setup

* **Login to Google Account:**
  ```bash
  firebase login
  ```
* **Initialize a project configuration (Firestore, Functions, Hosting, etc.):**
  ```bash
  firebase init
  ```
* **List Firebase projects:**
  ```bash
  firebase projects:list
  ```
* **Deploy Firestore rules & functions:**
  ```bash
  firebase deploy
  ```
* **Deploy hosting assets only:**
  ```bash
  firebase deploy --only hosting
  ```
* **Run local emulator suite:**
  ```bash
  firebase emulators:start
  ```

## Python SDK Integration
Install dependency:
```bash
pip install firebase-admin
```

Initialize Firebase Admin:
```python
import firebase_admin
from firebase_admin import credentials, firestore

# Initialize with service account json
cred = credentials.Certificate("/path/to/firebase-key.json")
firebase_admin.initialize_app(cred)

db = firestore.client()

# Write document
doc_ref = db.collection("users").document("alovelace")
doc_ref.set({"first": "Ada", "last": "Lovelace", "born": 1815})
```
