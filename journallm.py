#!/usr/bin/env python3
"""
JournalLM - Get personalized insights from your Day One journal entries
using Claude AI
"""

import os
import sys
import datetime
import argparse
import logging
from typing import Optional

from dotenv import load_dotenv
from journal_extractor import JournalExtractor
from claude_prompter import ClaudePrompter

# Load environment variables
load_dotenv()

# Set up logging
logger = logging.getLogger(__name__)

class JournalLM:
    """
    Main class for JournalLM application
    """
    def __init__(self, api_key: Optional[str] = None, folder_id: Optional[str] = None, credentials_path: Optional[str] = None):
        """
        Initialize JournalLM
        
        Args:
            api_key: Anthropic API key (optional when extract_only is True)
            folder_id: Google Drive folder ID containing Day One backups (optional when using local_file)
            credentials_path: Path to the credentials.json file downloaded from Google Cloud Console
        """
        # Get credentials file path from environment if not provided
        if not credentials_path:
            credentials_path = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
        
        # Initialize journal extractor
        self.journal_extractor = JournalExtractor(folder_id, credentials_path if folder_id else None)
        
        # Initialize Claude prompter if API key is provided
        self.claude_prompter = ClaudePrompter(api_key) if api_key else None

    def extract_journal_from_drive(self):
        """
        Extract journal entries from Day One backup in Google Drive
        
        Returns:
            Tuple of (str or None, datetime or None): XML representation of the journal entries and backup creation time
        """
        logger.info("Extracting journal entries from Google Drive")
        return self.journal_extractor.extract_journal()
    
    def extract_journal_from_file(self, file_path: str):
        """
        Extract journal entries from a local file (ZIP or JSON)
        
        Args:
            file_path: Path to the local file
            
        Returns:
            str or None: XML representation of the journal entries
        """
        logger.info(f"Extracting journal entries from local file: {file_path}")
        return self.journal_extractor.extract_from_local_file(file_path)
    
    def get_insights(self, journal_xml: str) -> Optional[str]:
        """
        Get insights from Claude based on journal entries
        
        Args:
            journal_xml: XML representation of the journal entries
            
        Returns:
            str or None: Claude's response with insights
        """
        if not self.claude_prompter:
            logger.error("Claude prompter not initialized (API key not provided)")
            return None
            
        logger.info("Getting insights from Claude")
        return self.claude_prompter.get_insights(journal_xml)
    
    def save_to_file(self, content: str, output_file: Optional[str] = None, file_type: str = "advice") -> str:
        """
        Save content to a file
        
        Args:
            content: Content to save
            output_file: Optional filename for the output
            file_type: Type of file being saved (for auto-generated filename)
            
        Returns:
            str: Path to the saved file
        """
        # Generate output filename if not provided
        if not output_file:
            now = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            if file_type == "journal":
                output_file = f"journal-{now}.xml"
            else:
                output_file = f"advice-{now}.md"
        
        # Save the content to a file
        logger.info(f"Saving to {output_file}")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return output_file

    def run(self, output_file: Optional[str] = None, extract_only: bool = False, journal_file: Optional[str] = None, 
            input_file: Optional[str] = None, save_journal: Optional[str] = None, should_save_journal: bool = False) -> None:
        """
        Run the JournalLM process
        
        Args:
            output_file: Optional filename for the insights output
            extract_only: If True, only extract journal entries and don't prompt Claude
            journal_file: Optional path to a pre-extracted journal XML file
            input_file: Optional path to a local ZIP or JSON file containing journal entries
            save_journal: Optional path to save the extracted journal XML
            should_save_journal: Flag indicating whether to save journal even if save_journal is None
        """
        try:
            # Get journal entries
            journal_xml = None
            backup_time = None
            
            if journal_file:
                # Load journal entries from XML file
                logger.info(f"Loading journal entries from XML file: {journal_file}")
                try:
                    with open(journal_file, 'r', encoding='utf-8') as f:
                        journal_xml = f.read()
                    logger.debug(f"Loaded {len(journal_xml)} bytes from journal XML file")
                except Exception as e:
                    logger.error(f"Error loading journal XML file: {str(e)}")
                    return
            elif input_file:
                # Extract journal entries from local ZIP or JSON file
                logger.info(f"Processing local file: {input_file}")
                journal_xml = self.extract_journal_from_file(input_file)
                if not journal_xml:
                    logger.error("Failed to extract journal entries from local file")
                    return
            else:
                # Extract journal entries from Google Drive
                journal_xml, backup_time = self.extract_journal_from_drive()
            
            if not journal_xml:
                logger.error("Failed to get journal entries")
                return
            
            # Save the journal XML if requested or if should_save_journal flag is set
            if save_journal is not None or should_save_journal:
                self.save_to_file(journal_xml, save_journal, "journal")
                logger.info(f"Journal XML saved")
            
            # If extract_only, exit after saving (if requested)
            if extract_only:
                logger.info("Journal extraction completed successfully")
                return
            
            # Get insights from Claude
            insights = self.get_insights(journal_xml)
            if not insights:
                logger.error("Failed to get insights from Claude")
                return
            
            # Save the insights to a file
            self.save_to_file(insights, output_file, "advice")
            
            logger.info("JournalLM process completed successfully")
            
        except Exception as e:
            logger.error(f"Error in JournalLM process: {str(e)}")
            raise

def main():
    """Main entry point for the script"""
    parser = argparse.ArgumentParser(description="JournalLM - Get insights from your journal")
    
    # Update command line options to match README
    parser.add_argument("--output", help="Output filename for advice (default: auto-generated)")
    parser.add_argument("--input", help="Path to a local ZIP or JSON file containing journal entries (default: download from Google Drive)")
    parser.add_argument("--save-journal", nargs='?', const=True, help="Output filename for journal (default: auto-generated if flag is given without a value)")
    parser.add_argument("--extract-only", action="store_true", help="Only extract journal entries, don't prompt Claude")
    parser.add_argument("--journal", help="Path to pre-extracted journal XML file (skips extraction)")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    args = parser.parse_args()
    
    # Set up logging based on debug flag
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    
    try:
        # Check if .env file exists
        if not os.path.exists(".env"):
            if os.path.exists(".env.example"):
                logger.error(".env file not found")
                logger.info("Please create a .env file based on the .env.example template")
                return 1
            else:
                logger.error("Neither .env nor .env.example files found")
                logger.info("Please create a .env file with the following content:")
                logger.info("FOLDER_ID=your_google_drive_folder_id_containing_dayone_backups")
                logger.info("GOOGLE_CREDENTIALS_FILE=path/to/credentials.json")
                logger.info("API_KEY=your_anthropic_api_key")
                return 1
        
        # Determine API key requirement
        api_key = os.getenv("API_KEY") if not args.extract_only else None
        if not api_key and not args.extract_only:
            logger.error("API_KEY environment variable is required when not using --extract-only")
            return 1
        
        # Determine folder ID requirement
        folder_id = os.getenv("FOLDER_ID")
        if not folder_id and not args.journal and not args.input:
            logger.error("FOLDER_ID environment variable is required when not using --journal or --input")
            return 1
        
        # Get credentials file path from environment
        credentials_path = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
        
        # Check if credentials file exists when needed
        if not args.journal and not args.input and not os.path.exists(credentials_path):
            logger.error(f"Credentials file not found: {credentials_path}")
            logger.info("Please follow these steps to get your credentials.json file:")
            logger.info("1. Go to https://console.cloud.google.com/")
            logger.info("2. Create a project and enable the Google Drive API")
            logger.info("3. Configure the OAuth consent screen")
            logger.info("4. Create OAuth 2.0 Client ID credentials (Desktop app)")
            logger.info("5. Download the credentials JSON file")
            logger.info("6. Save it at the path specified in GOOGLE_CREDENTIALS_FILE env var")
            return 1
        
        # Initialize JournalLM
        journallm = JournalLM(
            api_key=api_key,
            folder_id=folder_id if not (args.journal or args.input) else None,
            credentials_path=credentials_path if not (args.journal or args.input) else None
        )
        
        # Handle the save_journal argument
        save_journal_path = None
        should_save_journal = False
        
        if args.save_journal:
            if args.save_journal is True:  # Flag was given without a value
                should_save_journal = True
                save_journal_path = None
            else:  # Flag was given with a value
                save_journal_path = args.save_journal
        
        # Run the process
        journallm.run(
            output_file=args.output,
            extract_only=args.extract_only,
            journal_file=args.journal,
            input_file=args.input,
            save_journal=save_journal_path,
            should_save_journal=should_save_journal
        )
        
        return 0
    
    except FileNotFoundError as e:
        # Already logged above
        return 1
    except ValueError as e:
        logger.error(str(e))
        logger.info("Please check your .env file and ensure all required variables are set")
        return 1
    except Exception as e:
        logger.error(f"JournalLM failed: {str(e)}")
        if args.debug:
            import traceback
            logger.debug(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main())
