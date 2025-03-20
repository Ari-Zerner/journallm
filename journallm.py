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
import subprocess
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
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize JournalLM
        
        Args:
            api_key: Anthropic API key (optional when extract_only is True)
        """
        # Initialize journal extractor
        self.journal_extractor = JournalExtractor()
        
        # Initialize Claude prompter if API key is provided
        self.claude_prompter = ClaudePrompter(api_key) if api_key else None

    def extract_journal_from_google_drive(self, folder_id: str, credentials_path: str):
        """
        Extract journal entries from Day One backup in Google Drive
        
        Args:
            folder_id: Google Drive folder ID containing Day One backups
            credentials_path: Path to the credentials.json file
            
        Returns:
            Tuple of (str or None, datetime or None): XML representation of the journal entries and backup creation time
        """
        try:
            # Import here to avoid requiring Google Drive dependencies when not using this feature
            from google_drive_downloader import GoogleDriveDownloader
            
            logger.info("Extracting journal entries from Google Drive")
            
            # Initialize Google Drive downloader
            downloader = GoogleDriveDownloader(folder_id, credentials_path)
            
            # Download the latest backup
            file_content, backup_time = downloader.download_latest_backup()
            if not file_content:
                logger.error("Failed to download backup from Google Drive")
                return None, None
            
            # Extract journals from the downloaded content
            journal_xml = self.journal_extractor.extract_from_bytesio(file_content)
            return journal_xml, backup_time
            
        except ImportError:
            logger.error("Google Drive dependencies not installed. Run: pip install google-auth google-auth-oauthlib google-api-python-client")
            return None, None
        except Exception as e:
            logger.error(f"Error extracting journal from Google Drive: {str(e)}")
            return None, None
    
    def extract_journal_from_file(self, file_path: str):
        """
        Extract journal entries from a local file (ZIP or JSON)
        
        Args:
            file_path: Path to the local file
            
        Returns:
            str or None: XML representation of the journal entries
        """
        logger.info(f"Extracting journal entries from local file: {file_path}")
        return self.journal_extractor.extract_from_file(file_path)
    
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

    def add_to_day_one(self, content: str, journal_name: Optional[str] = None) -> bool:
        """
        Add the content as a new entry in Day One using the CLI
        
        Args:
            content: Content to add to Day One
            journal_name: Optional name of the journal to add the entry to
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Check if the Day One CLI is installed
            try:
                subprocess.run(["dayone2", "-h"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
            except FileNotFoundError:
                logger.error("Day One CLI not found. Please install it first:")
                logger.error("sudo bash /Applications/Day\\ One.app/Contents/Resources/install_cli.sh")
                return False
            
            # Prepare the command
            cmd = ["dayone2"]
            
            # Add journal option if specified
            if journal_name:
                cmd.extend(["--journal", journal_name])
            
            # Add the new command
            cmd.append("new")
            
            # Run the command and pipe the content to stdin
            logger.info(f"Adding entry to Day One{' journal: ' + journal_name if journal_name else ''}")
            process = subprocess.run(
                cmd, 
                input=content.encode('utf-8'), 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE
            )
            
            if process.returncode != 0:
                error_msg = process.stderr.decode('utf-8').strip()
                if "journal not found" in error_msg.lower():
                    logger.error(f"Journal '{journal_name}' not found in Day One")
                else:
                    logger.error(f"Error adding entry to Day One: {error_msg}")
                return False
            
            logger.info("Successfully added entry to Day One")
            return True
            
        except Exception as e:
            logger.error(f"Error adding entry to Day One: {str(e)}")
            return False

    def run(self, input_file: Optional[str] = None, google_drive: bool = False,
            output_file: Optional[str] = None, no_report: bool = False,
            journal_file: Optional[str] = None, save_journal: Optional[str] = None,
            should_save_journal: bool = False, folder_id: Optional[str] = None,
            credentials_path: Optional[str] = None, add_to_journal: Optional[str] = None,
            interactive: bool = False, interactive_report_file: Optional[str] = None) -> None:
        """
        Run the JournalLM process
        
        Args:
            input_file: Optional path to a local ZIP or JSON file containing journal entries
            google_drive: If True, download from Google Drive instead of using a local file
            output_file: Optional filename for the insights output
            no_report: If True, skip report generation
            journal_file: Optional path to a pre-extracted journal XML file
            save_journal: Optional path to save the extracted journal XML
            should_save_journal: Flag indicating whether to save journal even if save_journal is None
            folder_id: Google Drive folder ID containing Day One backups (required if google_drive is True)
            credentials_path: Path to the credentials.json file (required if google_drive is True)
            add_to_journal: Optional name of the Day One journal to add the insights to
            interactive: If True, start an interactive session after processing
            interactive_report_file: Optional path to a report file to use in interactive mode
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
            elif google_drive:
                # Extract journal entries from Google Drive
                if not folder_id:
                    logger.error("Folder ID is required when using Google Drive")
                    return
                if not credentials_path:
                    logger.error("Credentials path is required when using Google Drive")
                    return
                    
                journal_xml, backup_time = self.extract_journal_from_google_drive(folder_id, credentials_path)
                if not journal_xml:
                    logger.error("Failed to extract journal entries from Google Drive")
                    return
            elif input_file:
                # Extract journal entries from local ZIP or JSON file
                logger.info(f"Processing local file: {input_file}")
                journal_xml = self.extract_journal_from_file(input_file)
                if not journal_xml:
                    logger.error("Failed to extract journal entries from local file")
                    return
            else:
                logger.error("No input source specified. Please provide an input file, use Google Drive, or specify a pre-extracted journal file.")
                return
            
            if not journal_xml:
                logger.error("Failed to get journal entries")
                return
            
            # Save the journal XML if requested
            if save_journal is not None or should_save_journal:
                self.save_to_file(journal_xml, save_journal, "journal")
                logger.info(f"Journal XML saved")
            
            report = None
            if interactive_report_file:
                # Load the provided report file
                try:
                    with open(interactive_report_file, 'r', encoding='utf-8') as f:
                        report = f.read()
                    logger.debug(f"Loaded {len(report)} bytes from report file")
                except Exception as e:
                    logger.error(f"Error loading report file: {str(e)}")
                    return
            elif not no_report:
                # Get insights from Claude
                report = self.claude_prompter.get_report(journal_xml, cache_for_interactive=interactive)
                if not report:
                    logger.error("Failed to get insights from Claude")
                    return
                
                # Save the insights to a file
                output_path = self.save_to_file(report, output_file, "advice")
                
                # Add to Day One if requested
                if add_to_journal is not None:
                    journal_name = None if add_to_journal is True else add_to_journal
                    if not self.add_to_day_one(report, journal_name):
                        logger.warning("Failed to add entry to Day One")
            
            # Start interactive session if requested
            if interactive:
                self.claude_prompter.start_interactive_session(journal_xml, initial_report=report)
            
            logger.info("JournalLM process completed successfully")
            
        except Exception as e:
            logger.error(f"Error in JournalLM process: {str(e)}")
            raise

def main():
    """Main entry point for the script"""
    parser = argparse.ArgumentParser(description="JournalLM - Get insights from your journal")
    
    # Input source group (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument("input_file", nargs="?", help="Path to a local ZIP or JSON file containing journal entries")
    input_group.add_argument("--google-drive", action="store_true", help="Download the latest backup from Google Drive")
    input_group.add_argument("--journal", help="Path to pre-extracted journal XML file (skips extraction)")
    
    # Other options
    parser.add_argument("--output", help="Output filename for advice (default: auto-generated)")
    parser.add_argument("--save-journal", nargs='?', const=True, help="Output filename for journal (default: auto-generated if flag is given without a value)")
    parser.add_argument("--no-report", action="store_true", help="Skip report generation")
    parser.add_argument("--interactive", nargs='?', const=True, metavar='REPORT_FILE', help="Start an interactive session after processing. If REPORT_FILE is provided, use that report instead of generating one (implies --no-report)")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--add-to-journal", nargs='?', const=True, help="Add the generated report to Day One (optionally specify journal name)")
    
    args = parser.parse_args()

    # Handle --interactive with report file
    if isinstance(args.interactive, str):
        args.no_report = True
        if not os.path.exists(args.interactive):
            logger.error(f"Report file not found: {args.interactive}")
            return 1

    # Validate arguments
    if args.no_report and not (args.interactive or args.save_journal):
        logger.error("No action specified. Use --interactive or --save-journal with --no-report")
        return 1

    # Set up logging based on debug flag
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    
    try:
        # Determine API key requirement
        api_key = os.getenv("API_KEY") if (not args.no_report or args.interactive) else None
        if not api_key and (not args.no_report or args.interactive):
            logger.error("API_KEY environment variable is required when not using --no-report or when using --interactive")
            return 1

        # Get Google Drive settings from environment if needed
        folder_id = os.getenv("FOLDER_ID")
        credentials_path = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
        
        # Validate Google Drive settings if using Google Drive
        if args.google_drive:
            if not folder_id:
                logger.error("FOLDER_ID environment variable is required when using --google-drive")
                return 1
            
            if not os.path.exists(credentials_path):
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
        journallm = JournalLM(api_key=api_key)
        
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
            input_file=args.input_file,
            google_drive=args.google_drive,
            output_file=args.output,
            no_report=args.no_report,
            journal_file=args.journal,
            save_journal=save_journal_path,
            should_save_journal=should_save_journal,
            folder_id=folder_id if args.google_drive else None,
            credentials_path=credentials_path if args.google_drive else None,
            add_to_journal=args.add_to_journal,
            interactive=bool(args.interactive),
            interactive_report_file=args.interactive if isinstance(args.interactive, str) else None
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
