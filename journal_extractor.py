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
from typing import Dict, Optional, List, Tuple, Union
import traceback
import datetime
import pathlib

# Set up logging
logger = logging.getLogger(__name__)

class JournalExtractor:
    """
    Class for extracting and processing journal entries from Day One backups
    """
    def __init__(self):
        """
        Initialize the JournalExtractor
        """
        logger.debug("Initializing JournalExtractor")
    
    def extract_journals_from_zip(self, zip_content: Union[BytesIO, str]) -> Dict[str, Dict]:
        """
        Extract journal entries from a Day One backup zip file
        
        Args:
            zip_content: BytesIO object with zip content or path to local zip file
            
        Returns:
            Dict[str, Dict]: Dictionary mapping journal names to journal data
        """
        journals = {}
        
        try:
            # Create a temporary directory to extract files
            with tempfile.TemporaryDirectory() as temp_dir:
                logger.debug(f"Extracting zip file to temporary directory: {temp_dir}")
                
                # Open the zip file from BytesIO or local path
                try:
                    if isinstance(zip_content, BytesIO):
                        zip_file = zipfile.ZipFile(zip_content)
                    else:
                        # Validate that the file exists and is a zip file
                        if not os.path.exists(zip_content):
                            logger.error(f"ZIP file not found: {zip_content}")
                            return {}
                        
                        # Check file size (warn if over 100MB)
                        file_size_mb = os.path.getsize(zip_content) / (1024 * 1024)
                        if file_size_mb > 100:
                            logger.warning(f"ZIP file is large ({file_size_mb:.2f} MB), extraction may take some time")
                        
                        zip_file = zipfile.ZipFile(zip_content)
                except zipfile.BadZipFile:
                    logger.error(f"Invalid ZIP file: {zip_content}")
                    return {}
                except Exception as e:
                    logger.error(f"Error opening ZIP file: {str(e)}")
                    logger.debug(traceback.format_exc())
                    return {}
                
                # Extract files
                try:
                    with zip_file as zip_ref:
                        # Check for potential zip bomb (too many files or too large when extracted)
                        infolist = zip_ref.infolist()
                        total_size = sum(info.file_size for info in infolist)
                        if total_size > 1024 * 1024 * 500:  # 500MB limit
                            logger.error(f"ZIP file contents too large ({total_size / (1024 * 1024):.2f} MB when extracted)")
                            return {}
                        if len(infolist) > 10000:  # 10,000 files limit
                            logger.error(f"ZIP file contains too many files ({len(infolist)})")
                            return {}
                        
                        zip_ref.extractall(temp_dir)
                        zip_contents = zip_ref.namelist()
                        logger.debug(f"ZIP file contains {len(zip_contents)} files")
                        for item in zip_contents[:10]:  # Log first 10 files for brevity
                            logger.debug(f"  - {item}")
                        if len(zip_contents) > 10:
                            logger.debug(f"  ... and {len(zip_contents) - 10} more files")
                except Exception as e:
                    logger.error(f"Error extracting ZIP file: {str(e)}")
                    logger.debug(traceback.format_exc())
                    return {}
                
                # Find all JSON files in the extracted content
                logger.debug("Searching for JSON files in extracted content")
                journal_files = []
                for root, dirs, files in os.walk(temp_dir):
                    logger.debug(f"Searching directory: {root}")
                    logger.debug(f"Contains directories: {dirs}")
                    logger.debug(f"Contains files: {files}")
                    for file in files:
                        if file.endswith('.json'):
                            journal_files.append(os.path.join(root, file))
                            logger.debug(f"Found JSON file: {os.path.join(root, file)}")
                
                if not journal_files:
                    logger.error("No JSON files found in the backup")
                    return {}
                
                logger.info(f"Found {len(journal_files)} JSON files in the backup")
                
                # Parse each JSON file
                for journal_file in journal_files:
                    try:
                        # Get journal name from filename (without extension)
                        journal_name = os.path.splitext(os.path.basename(journal_file))[0]
                        logger.debug(f"Processing journal: {journal_name} from file {journal_file}")
                        
                        # Parse the JSON file
                        logger.debug(f"Parsing JSON file: {journal_file}")
                        with open(journal_file, 'r', encoding='utf-8') as f:
                            try:
                                journal_data = json.load(f)
                            except json.JSONDecodeError:
                                logger.error(f"Invalid JSON in file: {journal_file}")
                                continue
                        
                        # Validate journal data structure
                        if not isinstance(journal_data, dict):
                            logger.error(f"Invalid journal data format in {journal_file}: not a dictionary")
                            continue
                        
                        if 'entries' not in journal_data or not isinstance(journal_data['entries'], list):
                            logger.error(f"Invalid journal data format in {journal_file}: missing 'entries' list")
                            continue
                        
                        # Add to journals dictionary
                        journals[journal_name] = journal_data
                        
                        # Log some basic info about the journal data
                        entry_count = len(journal_data.get('entries', []))
                        logger.debug(f"Parsed journal '{journal_name}' with {entry_count} entries")
                        if entry_count > 0:
                            first_entry = journal_data['entries'][0]
                            logger.debug(f"First entry date: {first_entry.get('creationDate', 'unknown')}")
                            logger.debug(f"First entry length: {len(first_entry.get('text', ''))}")
                    
                    except Exception as e:
                        logger.error(f"Error parsing journal file {journal_file}: {str(e)}")
                        logger.debug(traceback.format_exc())
                
                return journals
                
        except Exception as e:
            logger.error(f"Error extracting journals from zip: {str(e)}")
            logger.debug(traceback.format_exc())
            return {}
    
    def load_json_file(self, json_path: str) -> Dict[str, Dict]:
        """
        Load a journal from a local JSON file
        
        Args:
            json_path: Path to the JSON file
            
        Returns:
            Dict[str, Dict]: Dictionary mapping journal name to journal data
        """
        try:
            logger.debug(f"Loading JSON file: {json_path}")
            
            # Validate file exists
            if not os.path.exists(json_path):
                logger.error(f"JSON file not found: {json_path}")
                return {}
            
            # Check file size (warn if over 50MB)
            file_size_mb = os.path.getsize(json_path) / (1024 * 1024)
            if file_size_mb > 50:
                logger.warning(f"JSON file is large ({file_size_mb:.2f} MB), processing may take some time")
            
            # Read and parse JSON
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    journal_data = json.load(f)
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON in file: {json_path}")
                return {}
            except UnicodeDecodeError:
                logger.error(f"File encoding error: {json_path} is not a valid UTF-8 text file")
                return {}
            
            # Validate journal data structure
            if not isinstance(journal_data, dict):
                logger.error(f"Invalid journal data format in {json_path}: not a dictionary")
                return {}
            
            if 'entries' not in journal_data or not isinstance(journal_data['entries'], list):
                logger.error(f"Invalid journal data format in {json_path}: missing 'entries' list")
                return {}
            
            # Get journal name from filename (without extension)
            journal_name = os.path.splitext(os.path.basename(json_path))[0]
            logger.debug(f"Using journal name from filename: {journal_name}")
            
            # Create a dictionary with the journal name as key
            journals = {journal_name: journal_data}
            
            # Log some basic info about the journal data
            entry_count = len(journal_data.get('entries', []))
            logger.debug(f"Parsed journal '{journal_name}' with {entry_count} entries")
            if entry_count > 0:
                first_entry = journal_data['entries'][0]
                logger.debug(f"First entry date: {first_entry.get('creationDate', 'unknown')}")
                logger.debug(f"First entry length: {len(first_entry.get('text', ''))}")
            
            return journals
            
        except Exception as e:
            logger.error(f"Error loading JSON file: {str(e)}")
            logger.debug(traceback.format_exc())
            return {}
    
    def convert_to_xml(self, journals: Dict[str, Dict]) -> str:
        """
        Convert journal data from JSON to XML format
        
        Args:
            journals: Dictionary mapping journal names to journal data
            
        Returns:
            str: XML representation of the journal data
        """
        try:
            logger.debug("Converting journal data to XML")
            
            # Create the root element - now it's journals (plural)
            root = ET.Element("journals")
            
            # Process each journal
            for journal_name, journal_data in journals.items():
                logger.debug(f"Processing journal: {journal_name}")
                
                # Create a journal element for this journal
                journal_elem = ET.SubElement(root, "journal")
                journal_elem.set("name", journal_name)
                
                # Get entries
                entries = journal_data.get('entries', [])
                logger.debug(f"Processing {len(entries)} entries in journal {journal_name}")
                
                # Process each entry
                for i, entry in enumerate(entries):
                    if i % 100 == 0 and i > 0:
                        logger.debug(f"Processed {i} entries so far in journal {journal_name}")
                    
                    entry_elem = ET.SubElement(journal_elem, "entry")
                    
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
            logger.error(f"Error converting journals to XML: {str(e)}")
            logger.debug(traceback.format_exc())
            raise
    
    def extract_from_file(self, file_path: str) -> Optional[str]:
        """
        Extract journal entries from a local file (ZIP or JSON) and convert to XML
        
        Args:
            file_path: Path to the local ZIP or JSON file
            
        Returns:
            str or None: XML representation of the journal entries
        """
        try:
            logger.info(f"Processing local file: {file_path}")
            file_path = os.path.abspath(file_path)
            
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return None
            
            # Determine file type
            file_ext = pathlib.Path(file_path).suffix.lower()
            
            journals = {}
            if file_ext == '.zip':
                # Process ZIP file
                logger.info("Processing ZIP file")
                journals = self.extract_journals_from_zip(file_path)
            elif file_ext == '.json':
                # Process JSON file
                logger.info("Processing JSON file")
                journals = self.load_json_file(file_path)
            else:
                logger.error(f"Unsupported file type: {file_ext}. Only .zip and .json files are supported.")
                return None
            
            if not journals:
                logger.error("No journal data extracted from file")
                return None
            
            # Convert to XML
            logger.info(f"Converting {len(journals)} journals to XML format")
            return self.convert_to_xml(journals)
            
        except Exception as e:
            logger.error(f"Error processing local file: {str(e)}")
            logger.debug(traceback.format_exc())
            return None
            
    def extract_from_bytesio(self, file_content: BytesIO) -> Optional[str]:
        """
        Extract journal entries from a BytesIO object containing a ZIP file
        
        Args:
            file_content: BytesIO object containing a ZIP file
            
        Returns:
            str or None: XML representation of the journal entries
        """
        try:
            logger.info("Processing BytesIO content")
            
            # Extract journals from the content
            journals = self.extract_journals_from_zip(file_content)
            if not journals:
                logger.error("No journal data extracted from BytesIO content")
                return None
            
            # Convert to XML
            logger.info(f"Converting {len(journals)} journals to XML format")
            return self.convert_to_xml(journals)
            
        except Exception as e:
            logger.error(f"Error processing BytesIO content: {str(e)}")
            logger.debug(traceback.format_exc())
            return None