# pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
import os
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# --- 1. DEFINE YOUR CENTRAL AUTH FOLDER ---
# Creates a path to a folder named 'google_auth' in your user's home directory.
# This will work on Windows, macOS, and Linux.
HOME_DIR = os.path.expanduser('~')
AUTH_DIR = os.path.join(HOME_DIR, 'google_auth')

# Define the absolute paths for your files
CREDENTIALS_PATH = os.path.join(AUTH_DIR, 'credentials.json')
TOKEN_PATH = os.path.join(AUTH_DIR, 'token.json')

def get_drive_service():
    """
    Authenticates and returns an authorized Google Drive service object.
    
    This function now reads/writes credentials from a fixed
    location: (Your Home Directory)/google_auth/
    """
    SCOPES = ['https://www.googleapis.com/auth/drive']
    creds = None

    # --- 2. ENSURE THE AUTH DIRECTORY EXISTS ---
    # Create the directory if it doesn't exist
    if not os.path.exists(AUTH_DIR):
        os.makedirs(AUTH_DIR)
        print(f"Created directory: {AUTH_DIR}")

    # Check for the token file at the TOKEN_PATH
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Check if the credentials.json file exists
            if not os.path.exists(CREDENTIALS_PATH):
                print(f"Error: 'credentials.json' not found at {CREDENTIALS_PATH}")
                print("Please download it from Google Cloud Console and place it there.")
                return None
                
            # Run the flow using the CREDENTIALS_PATH
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
            
        # Save the credentials for the next run to the TOKEN_PATH
        with open(TOKEN_PATH, 'w') as token:
            token.write(creds.to_json())
            print(f"Token saved to: {TOKEN_PATH}")
    
    return build('drive', 'v3', credentials=creds)

# --- 3. Example Usage (no change here) ---
if __name__ == '__main__':
    service = get_drive_service()
    if service:
        print("Successfully authenticated Google Drive service!")
        # You can now import and use your MrcDriveHandler class
        # handler = MrcDriveHandler(service)
        # ... etc.
