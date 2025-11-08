import os
import io
import mrcfile
import numpy as np
import DriveHandler

# Create a dummy file to upload
LOCAL_FILE = 'my_test_data.mrc'
if not os.path.exists(LOCAL_FILE):
    # Create a 5x5x4 3D array
    data = np.arange(100, dtype=np.float32).reshape((5, 5, 4))
    with mrcfile.new(LOCAL_FILE, overwrite=True) as mrc:
        mrc.set_data(data)
    print(f"Created dummy file: {LOCAL_FILE}")

# --- Authenticate and set up the handler ---
service = DriveHandler.get_drive_service()
if service:
    handler = DriveHandler.DriveHandler(service)
    
    # "TomogramDenoising/tmp" folder.
    # https://drive.google.com/drive/folders/1hGHvkP46fxLCQbUlyYhAS_eVl6PollQM
    MY_SHARED_DRIVE_ID = '1hGHvkP46fxLCQbUlyYhAS_eVl6PollQM' # <-- CHANGE THIS
        
    print("\n--- UPLOADING TO SHARED DRIVE ROOT ---")
    uploaded_file_id = handler.upload(
        local_file_path=LOCAL_FILE,
        drive_file_name='test_file_in_shared_drive.mrc',
        drive_folder_id=MY_SHARED_DRIVE_ID # <-- Use Shared Drive ID as parent
    )
    print(uploaded_file_id)

    success = handler.download(
        file_id=uploaded_file_id,
        local_save_path='downloaded_file.mrc'
    )
    print(success)