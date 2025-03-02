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
    def __init__(self, folder_id: str, api_key: str, credentials_path: Optional[str] = None):
        """
        Initialize JournalLM
        
        Args:
            folder_id: Google Drive folder ID containing Day One backups
            api_key: Anthropic API key
            credentials_path: Path to the credentials.json file downloaded from Google Cloud Console
        """
        # Get credentials file path from environment if not provided
        if not credentials_path:
            credentials_path = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
        
        # Check if credentials file exists
        if not os.path.exists(credentials_path):
            logger.error(f"Credentials file not found: {credentials_path}")
            raise FileNotFoundError(f"Credentials file not found: {credentials_path}")
        
        logger.debug(f"Using credentials file: {credentials_path}")
        logger.debug(f"Using folder ID: {folder_id}")
        
        # Initialize components
        self.journal_extractor = JournalExtractor(folder_id, credentials_path)
        self.claude_prompter = ClaudePrompter(api_key)

    def extract_journal(self):
        """
        Extract journal entries from Day One backup
        
        Returns:
            Tuple of (str or None, datetime or None): XML representation of the journal entries and backup creation time
        """
        logger.info("Extracting journal entries")
        return self.journal_extractor.extract_journal()
    
    def get_insights(self, journal_xml: str) -> Optional[str]:
        """
        Get insights from Claude based on journal entries
        
        Args:
            journal_xml: XML representation of the journal entries
            
        Returns:
            str or None: Claude's response with insights
        """
        logger.info("Getting insights from Claude")
        return self.claude_prompter.get_insights(journal_xml)
    
    def save_to_file(self, content: str, output_file: Optional[str] = None) -> str:
        """
        Save content to a file
        
        Args:
            content: Content to save
            output_file: Optional filename for the output
            
        Returns:
            str: Path to the saved file
        """
        # Generate output filename if not provided
        if not output_file:
            now = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            output_file = f"advice-{now}.md"
        
        # Save the content to a file
        logger.info(f"Saving to {output_file}")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return output_file

    def run(self, output_file: Optional[str] = None, extract_only: bool = False, journal_file: Optional[str] = None) -> None:
        """
        Run the JournalLM process
        
        Args:
            output_file: Optional filename for the output
            extract_only: If True, only extract journal entries and don't prompt Claude
            journal_file: Optional path to a pre-extracted journal XML file
        """
        try:
            # Get journal entries
            journal_xml = None
            backup_time = None
            
            if journal_file:
                # Load journal entries from file
                logger.info(f"Loading journal entries from {journal_file}")
                try:
                    with open(journal_file, 'r', encoding='utf-8') as f:
                        journal_xml = f.read()
                    logger.debug(f"Loaded {len(journal_xml)} bytes from journal file")
                except Exception as e:
                    logger.error(f"Error loading journal file: {str(e)}")
                    return
            else:
                # Extract journal entries
                journal_xml, backup_time = self.extract_journal()
            
            if not journal_xml:
                logger.error("Failed to get journal entries")
                return
            
            # If extract_only, save the XML and exit
            if extract_only:
                # Use backup time for filename if available
                if backup_time:
                    backup_time_str = backup_time.strftime("%Y%m%d-%H%M%S")
                    xml_file = output_file if output_file else f"journal-{backup_time_str}.xml"
                else:
                    now = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
                    xml_file = output_file if output_file else f"journal-{now}.xml"
                
                self.save_to_file(journal_xml, xml_file)
                logger.info("Journal extraction completed successfully")
                return
            
            # Get insights from Claude
            insights = self.get_insights(journal_xml)
            if not insights:
                logger.error("Failed to get insights from Claude")
                return
            
            # Save the insights to a file
            self.save_to_file(insights, output_file)
            
            logger.info("JournalLM process completed successfully")
            
        except Exception as e:
            logger.error(f"Error in JournalLM process: {str(e)}")
            raise

def main():
    """Main entry point for the script"""
    parser = argparse.ArgumentParser(description="JournalLM - Get insights from your journal")
    parser.add_argument("output_file", nargs="?", help="Output filename (default: auto-generated)")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    # Add flow control flags
    parser.add_argument("--extract-only", action="store_true", help="Only extract journal entries, don't prompt Claude")
    parser.add_argument("--journal-file", help="Path to pre-extracted journal XML file (skips extraction)")
    
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
        
        # Get environment variables
        folder_id = os.getenv("FOLDER_ID")
        if not folder_id and not args.journal_file:
            logger.error("FOLDER_ID environment variable is required when not using --journal-file")
            return 1
        
        api_key = os.getenv("API_KEY")
        if not api_key and not args.extract_only:
            logger.error("API_KEY environment variable is required when not using --extract-only")
            return 1
        
        # Get credentials file path from environment
        credentials_path = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
        
        # Check if credentials file exists when needed
        if not args.journal_file and not os.path.exists(credentials_path):
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
            folder_id=folder_id if not args.journal_file else "not_used",
            api_key=api_key if not args.extract_only else "not_used",
            credentials_path=credentials_path if not args.journal_file else None
        )
        
        # Run the process
        journallm.run(
            output_file=args.output_file,
            extract_only=args.extract_only,
            journal_file=args.journal_file
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
