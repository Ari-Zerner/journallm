#!/usr/bin/env python3
"""
Journal Extractor - Extract and process journal entries from Day One backups
"""

import os
import json
import zipfile
import tempfile
import logging
import xml.etree.ElementTree as ET
from xml.dom import minidom
from io import BytesIO
from typing import Dict, Optional, List, Tuple
import traceback
import datetime

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# Set up logging
logger = logging.getLogger(__name__)

# Google Drive API scopes
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

class JournalExtractor:
    """
    Class for extracting and processing journal entries from Day One backups
    """
    def __init__(self, folder_id: str, credentials_path: str = "credentials.json"):
        """
        Initialize the JournalExtractor
        
        Args:
            folder_id: Google Drive folder ID containing Day One backups
            credentials_path: Path to the credentials.json file downloaded from Google Cloud Console
        """
        self.folder_id = folder_id
        self.credentials_path = credentials_path
        
        # Check if credentials file exists
        if not os.path.exists(credentials_path):
            logger.error(f"Credentials file not found: {credentials_path}")
            logger.info("Please download the credentials.json file from Google Cloud Console.")
            logger.info("See README.md for instructions on setting up Google Drive API.")
            raise FileNotFoundError(f"Credentials file not found: {credentials_path}")
        
        logger.debug(f"Initializing JournalExtractor with folder_id: {folder_id}")
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
    
    def download_and_extract_backup(self, file_id: str) -> Optional[Dict]:
        """
        Download and extract the journal entries from a Day One backup
        
        Args:
            file_id: Google Drive file ID of the backup
            
        Returns:
            Dict or None: The parsed journal data
        """
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
            
            # Extract the zip file
            with tempfile.TemporaryDirectory() as temp_dir:
                logger.debug(f"Extracting zip file to temporary directory: {temp_dir}")
                with zipfile.ZipFile(file_content) as zip_ref:
                    zip_ref.extractall(temp_dir)
                    zip_contents = zip_ref.namelist()
                    logger.debug(f"Zip file contains {len(zip_contents)} files")
                    for item in zip_contents[:10]:  # Log first 10 files for brevity
                        logger.debug(f"  - {item}")
                    if len(zip_contents) > 10:
                        logger.debug(f"  ... and {len(zip_contents) - 10} more files")
                
                # Find the JSON file in the extracted content
                logger.debug("Searching for JSON file in extracted content")
                journal_file = None
                for root, dirs, files in os.walk(temp_dir):
                    logger.debug(f"Searching directory: {root}")
                    logger.debug(f"Contains directories: {dirs}")
                    logger.debug(f"Contains files: {files}")
                    for file in files:
                        if file.endswith('.json'):
                            journal_file = os.path.join(root, file)
                            logger.debug(f"Found JSON file: {journal_file}")
                            break
                    if journal_file:
                        break
                
                if not journal_file:
                    logger.error("No JSON file found in the backup")
                    return None
                
                # Parse the JSON file
                logger.debug(f"Parsing JSON file: {journal_file}")
                with open(journal_file, 'r', encoding='utf-8') as f:
                    journal_data = json.load(f)
                
                # Log some basic info about the journal data
                entry_count = len(journal_data.get('entries', []))
                logger.debug(f"Parsed journal data with {entry_count} entries")
                if entry_count > 0:
                    first_entry = journal_data['entries'][0]
                    logger.debug(f"First entry date: {first_entry.get('creationDate', 'unknown')}")
                    logger.debug(f"First entry length: {len(first_entry.get('text', ''))}")
                
                return journal_data
                
        except Exception as e:
            logger.error(f"Error downloading or extracting backup: {str(e)}")
            logger.debug(traceback.format_exc())
            return None
    
    def convert_to_xml(self, journal_data: Dict) -> str:
        """
        Convert journal data from JSON to XML format
        
        Args:
            journal_data: The parsed journal data
            
        Returns:
            str: XML representation of the journal data
        """
        try:
            logger.debug("Converting journal data to XML")
            
            # Create the root element
            root = ET.Element("journal")
            
            # Get entries
            entries = journal_data.get('entries', [])
            logger.debug(f"Processing {len(entries)} journal entries")
            
            # Process each entry
            for i, entry in enumerate(entries):
                if i % 100 == 0 and i > 0:
                    logger.debug(f"Processed {i} entries so far")
                
                entry_elem = ET.SubElement(root, "entry")
                
                # Add creation date
                created = ET.SubElement(entry_elem, "created")
                created.text = entry.get('creationDate', '')
                
                # Add modification date
                modified = ET.SubElement(entry_elem, "modified")
                modified.text = entry.get('modifiedDate', '')
                
                # Add location if available
                location = entry.get('location', {})
                if location and location.get('address'):
                    loc = ET.SubElement(entry_elem, "loc")
                    loc.text = location.get('address', '')
                
                # Add text content
                text = ET.SubElement(entry_elem, "text")
                text.text = entry.get('text', '')
            
            # Convert to string with pretty formatting
            logger.debug("Converting XML tree to string")
            rough_string = ET.tostring(root, 'utf-8')
            reparsed = minidom.parseString(rough_string)
            xml_string = reparsed.toprettyxml(indent="  ")
            
            logger.debug(f"XML conversion complete, size: {len(xml_string)} bytes")
            return xml_string
            
        except Exception as e:
            logger.error(f"Error converting journal to XML: {str(e)}")
            logger.debug(traceback.format_exc())
            raise
    
    def extract_journal(self) -> Tuple[Optional[str], Optional[datetime.datetime]]:
        """
        Extract journal entries and convert to XML
        
        Returns:
            Tuple of (str or None, datetime or None): XML representation of the journal entries and backup creation time
        """
        # Get the latest backup
        backup, created_time = self.get_latest_backup()
        if not backup:
            logger.error("Failed to get latest backup")
            return None, None
        
        # Download and extract the backup
        logger.info(f"Downloading backup: {backup['name']}")
        journal_data = self.download_and_extract_backup(backup['id'])
        if not journal_data:
            logger.error("Failed to extract journal data")
            return None, None
        
        # Convert to XML
        logger.info("Converting journal to XML format")
        return self.convert_to_xml(journal_data), created_time