#!/usr/bin/env python3
"""
Google Drive Downloader - Download Day One backups from Google Drive
"""

import os
import json
import logging
import datetime
from typing import Optional, Dict, Tuple
from io import BytesIO
import traceback

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# Set up logging
logger = logging.getLogger(__name__)

# Google Drive API scopes
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

class GoogleDriveDownloader:
    """
    Class for downloading Day One backups from Google Drive
    """
    def __init__(self, folder_id: str, credentials_path: str = "credentials.json"):
        """
        Initialize the GoogleDriveDownloader
        
        Args:
            folder_id: Google Drive folder ID containing Day One backups
            credentials_path: Path to the credentials.json file downloaded from Google Cloud Console
        """
        self.folder_id = folder_id
        self.credentials_path = credentials_path
        self.drive_service = None
        
        # Check if credentials file exists
        if not os.path.exists(credentials_path):
            logger.error(f"Credentials file not found: {credentials_path}")
            logger.info("Please download the credentials.json file from Google Cloud Console.")
            logger.info("See README.md for instructions on setting up Google Drive API.")
            raise FileNotFoundError(f"Credentials file not found: {credentials_path}")
        
        logger.debug(f"Initializing GoogleDriveDownloader with folder_id: {folder_id}")
        logger.debug(f"Using credentials file: {credentials_path}")
        
        self.drive_service = self._authenticate_google_drive()
    
    def _authenticate_google_drive(self):
        """
        Authenticate with Google Drive API
        
        Returns:
            Google Drive service object
        """
        creds = None
        token_path = 'token.json'
        
        logger.debug("Starting Google Drive authentication")
        
        # Load credentials from token.json if it exists
        if os.path.exists(token_path):
            try:
                logger.debug(f"Loading credentials from {token_path}")
                creds = Credentials.from_authorized_user_info(
                    json.loads(open(token_path).read()), SCOPES
                )
                logger.debug("Credentials loaded successfully")
            except Exception as e:
                logger.warning(f"Failed to load existing token: {str(e)}")
                creds = None
        else:
            logger.debug(f"Token file {token_path} not found, will need to authenticate")
        
        # If credentials don't exist or are invalid, go through auth flow
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    logger.debug("Refreshing expired credentials")
                    creds.refresh(Request())
                    logger.debug("Credentials refreshed successfully")
                except Exception as e:
                    logger.warning(f"Failed to refresh token: {str(e)}")
                    creds = None
            
            # Set up OAuth flow with credentials file
            if not creds:
                try:
                    logger.debug("Starting OAuth flow with credentials file")
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, SCOPES
                    )
                    logger.info("Opening browser for Google authentication...")
                    creds = flow.run_local_server(port=0)
                    logger.debug("Authentication successful")
                    
                    # Save the credentials for the next run
                    logger.debug(f"Saving credentials to {token_path}")
                    with open(token_path, 'w') as token:
                        token.write(creds.to_json())
                    logger.debug("Credentials saved successfully")
                except Exception as e:
                    logger.error(f"Authentication failed: {str(e)}")
                    raise
        
        logger.debug("Building Google Drive service")
        return build('drive', 'v3', credentials=creds)
    
    def get_latest_backup(self) -> Tuple[Optional[Dict], Optional[datetime.datetime]]:
        """
        Get the most recent Day One backup from Google Drive
        
        Returns:
            Tuple of (Dict or None, datetime or None): Metadata of the latest backup file and its creation time
        """
        if not self.drive_service:
            logger.error("Google Drive service not initialized")
            return None, None
            
        try:
            logger.debug(f"Searching for files in folder: {self.folder_id}")
            
            # Search for files in the specified folder, ordering by createdTime descending
            # This lets the Google API do the sorting for us
            results = self.drive_service.files().list(
                q=f"'{self.folder_id}' in parents and trashed=false and mimeType='application/zip'",
                orderBy="createdTime desc",
                pageSize=10,  # Limit to 10 results since we only need the most recent
                fields="files(id, name, createdTime, mimeType)"
            ).execute()
            
            files = results.get('files', [])
            
            if not files:
                logger.error(f"No zip files found in folder with ID: {self.folder_id}")
                return None, None
            
            # Log all files found in the folder
            logger.debug(f"Found {len(files)} zip files in the folder:")
            for file in files:
                logger.debug(f"  - {file['name']} ({file['mimeType']}) created: {file['createdTime']}")
            
            # The first file is the most recent due to our orderBy parameter
            latest_backup = files[0]
            
            # Parse the creation time
            created_time = None
            try:
                # Google Drive API returns ISO 8601 format
                created_time_str = latest_backup['createdTime']
                created_time = datetime.datetime.fromisoformat(created_time_str.replace('Z', '+00:00'))
                logger.debug(f"Parsed creation time: {created_time}")
            except Exception as e:
                logger.warning(f"Could not parse creation time: {str(e)}")
            
            logger.info(f"Selected backup: {latest_backup['name']}")
            return latest_backup, created_time
        
        except Exception as e:
            logger.error(f"Error fetching backups: {str(e)}")
            logger.debug(traceback.format_exc())
            return None, None
    
    def download_drive_file(self, file_id: str) -> Optional[BytesIO]:
        """
        Download file from Google Drive
        
        Args:
            file_id: Google Drive file ID
            
        Returns:
            BytesIO or None: Downloaded file content
        """
        if not self.drive_service:
            logger.error("Google Drive service not initialized")
            return None
            
        try:
            logger.debug(f"Downloading file with ID: {file_id}")
            
            # Download the file
            request = self.drive_service.files().get_media(fileId=file_id)
            file_content = BytesIO()
            downloader = MediaIoBaseDownload(file_content, request)
            
            done = False
            while not done:
                status, done = downloader.next_chunk()
                logger.info(f"Download {int(status.progress() * 100)}%")
            
            file_content.seek(0)
            file_size = file_content.getbuffer().nbytes
            logger.debug(f"Downloaded {file_size} bytes")
            
            return file_content
            
        except Exception as e:
            logger.error(f"Error downloading file: {str(e)}")
            logger.debug(traceback.format_exc())
            return None
    
    def download_latest_backup(self) -> Tuple[Optional[BytesIO], Optional[datetime.datetime]]:
        """
        Download the latest Day One backup from Google Drive
        
        Returns:
            Tuple of (BytesIO or None, datetime or None): Content of the latest backup file and its creation time
        """
        # Get the latest backup
        backup, created_time = self.get_latest_backup()
        if not backup:
            logger.error("Failed to get latest backup")
            return None, None
        
        # Download the file
        logger.info(f"Downloading backup: {backup['name']}")
        file_content = self.download_drive_file(backup['id'])
        if not file_content:
            logger.error("Failed to download backup")
            return None, None
        
        return file_content, created_time
