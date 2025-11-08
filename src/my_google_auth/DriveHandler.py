import os
import io
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

def get_drive_service():
    """Authenticates and returns an authorized Google Drive service object."""
    # Use full 'drive' scope, which covers 'drive.file'
    SCOPES = ['https://www.googleapis.com/auth/drive']
    
    # Use the centralized auth paths
    HOME_DIR = os.path.expanduser('~')
    AUTH_DIR = os.path.join(HOME_DIR, 'google_auth')
    CREDENTIALS_PATH = os.path.join(AUTH_DIR, 'credentials.json')
    TOKEN_PATH = os.path.join(AUTH_DIR, 'token.json')

    creds = None
    if not os.path.exists(AUTH_DIR):
        os.makedirs(AUTH_DIR)

    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_PATH):
                print(f"Error: 'credentials.json' not found at {CREDENTIALS_PATH}")
                return None
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, 'w') as token:
            token.write(creds.to_json())
    
    return build('drive', 'v3', credentials=creds)

class DriveHandler:
    
    def __init__(self, drive_service):
        self.service = drive_service

    def delete_file(self, file_id):
        """
        Deletes a file by its ID.
        Returns True if successful, else False.
        """
        if file_id is None:
            return False # Nothing to delete
            
        print(f"Attempting to delete file ID: {file_id}")
        try:
            self.service.files().delete(
                fileId=file_id,
                supportsAllDrives=True
            ).execute()
            
            print(f"File deleted successfully.")
            return True
        
        except HttpError as e:
            if e.resp.status == 404:
                print("File not found (it may already be deleted).")
            else:
                print(f"An error occurred during deletion: {e}")
            return False
        except Exception as e:
            print(f"An unexpected error occurred during deletion: {e}")
            return False

    def upload_file_with_duplicates(self, local_file_path, drive_file_name, drive_folder_id=None):
        """
        Uploads a local file to Google Drive (resumable).
        """
        print(f"Starting upload for: {local_file_path}")
        mimetype = 'application/octet-stream'
        
        file_metadata = {
            'name': drive_file_name
        }
        if drive_folder_id:
            file_metadata['parents'] = [drive_folder_id]
            print(f"Targeting folder ID: {drive_folder_id}")
        else:
            print("Targeting 'My Drive' (root)")

        media = MediaFileUpload(
            local_file_path,
            mimetype=mimetype,
            resumable=True
        )

        try:
            request = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, parents',
                supportsAllDrives=True
            )
            
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    print(f"Uploaded {int(status.progress() * 100)}%")
            
            file_id = response.get('id')
            print(f"File uploaded successfully! File ID: {file_id}")
            print(f"Stored in parent folder(s): {response.get('parents')}")
            return file_id

        except Exception as e:
            print(f"An error occurred during upload: {e}")
            return None

    def _find_file_id(self, drive_file_name, drive_folder_id=None):
        """
        Searches for a file by name and parent folder.
        Returns the file ID if found, else None.
        (This is still needed for the delete operation)
        """
        
        safe_name = drive_file_name.replace("'", "\\'")
        query = f"name = '{safe_name}' and trashed = false"
        
        if drive_folder_id:
            query += f" and '{drive_folder_id}' in parents"
        else:
            query += " and 'root' in parents"
            
        try:
            response = self.service.files().list(
                q=query,
                fields="files(id, name)",
                pageSize=5,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True
            ).execute()
            
            files = response.get('files', [])
            
            if len(files) == 0:
                return None
            if len(files) > 1:
                print(f"Warning: Found multiple files named '{drive_file_name}'. "
                      f"Will delete the first one found (ID: {files[0].get('id')}).")
            
            return files[0].get('id')
            
        except HttpError as e:
            print(f"An error occurred during search: {e}")
            return None

    def upload(self, local_file_path, drive_file_name, 
                   drive_folder_id=None):
        """
        Uploads a file. It ALWAYS deletes any pre-existing
        file with the same name and location before uploading.
        """
        
        # --- 1. ATTEMPT TO DELETE ---
        print(f"Searching for and deleting existing file: '{drive_file_name}'")
        existing_file_id = self._find_file_id(drive_file_name, drive_folder_id)
        
        if existing_file_id:
            self.delete_file(existing_file_id)
        else:
            print("No existing file found. Proceeding with upload.")

        # --- 2. ALWAYS CREATE ---
        print(f"Uploading '{drive_file_name}' as a new file...")
        mimetype = 'application/octet-stream'
        media = MediaFileUpload(
            local_file_path,
            mimetype=mimetype,
            resumable=True
        )
        
        file_metadata = {'name': drive_file_name}
        if drive_folder_id:
            file_metadata['parents'] = [drive_folder_id]
        else:
            print("No folder ID provided. Uploading to 'My Drive' root.")
        
        try:
            request = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, parents',
                supportsAllDrives=True
            )
            
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    print(f"Uploaded {int(status.progress() * 100)}%")
            
            file_id = response.get('id')
            print(f"Upload complete! File ID: {file_id}")
            print(f"Stored in parent folder(s): {response.get('parents')}")
            return file_id

        except Exception as e:
            print(f"An error occurred during upload: {e}")
            return None

    def download(self, file_id, local_save_path):
        """
        Downloads a file from Google Drive by its ID (resumable).
        """
        print(f"Starting download for file ID: {file_id}")
        
        try:
            request = self.service.files().get_media(
                fileId=file_id,
                supportsAllDrives=True
            )
            
            with io.FileIO(local_save_path, 'wb') as fh:
                downloader = MediaIoBaseDownload(
                    fh, 
                    request, 
                    chunksize=1024*1024*10
                )
                
                done = False
                while not done:
                    status, done = downloader.next_chunk()
                    if status:
                        print(f"Downloaded {int(status.progress() * 100)}%")
            
            print(f"File downloaded successfully to: {local_save_path}")
            return True

        except Exception as e:
            print(f"An error occurred during download: {e}")
            return False
