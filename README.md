# JournalLM

JournalLM is a Python script that provides personalized insights based on your journal, using the Claude API.

## How It Works

1. You provide your journal as an export from Day One or as a single file
2. Your journal entries are sent to Claude AI with a carefully designed prompt
3. Claude analyzes your journal and provides personalized insights and advice
4. The response is saved as a markdown file
5. In the report, JournalLM asks you to provide additional context to improve its advice over time
6. Optional features are provided for more [advanced usage](#usage)

## Quickstart

### Setup

1. Clone this repository
   ```
   git clone https://github.com/Ari-Zerner/journallm
   cd journallm
   ```
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Get an Anthropic API key:
   - Sign up at [Anthropic](https://console.anthropic.com/settings/keys)
   - Create an API key
4. Either:
   - Create a `.env` file in the project directory with `API_KEY = <your_anthropic_api_key>`, or
   - When using the web interface, enter your API key directly if one isn't configured in the environment

### Basic Usage

1. Prepare your journal in one of these formats:
   - [Export](https://dayoneapp.com/guides/tips-and-tutorials/exporting-entries/) your Day One journal (select JSON format, provide the exported ZIP file)
   - Create a file with your journal entries in XML, JSON, MD, or TXT format
     - See the [XML Format](#xml-format) section for a recommended format
2. Run the script:
   ```
   python journallm.py [your_journal_file]
   ```
3. Your JournalLM report will be saved as a markdown file named `advice-<date>-<time>.md` in the project directory
   - Tip: You can use [md-to-pdf](https://md-to-pdf.fly.dev/) to turn the report into a nicely-formatted PDF

## Optional Setup

### Google Drive Setup
If you want to automatically download Day One backups from Google Drive rather than export manually:

1. Set up Google Drive API:
   - Go to the [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project
   - Enable the Google Drive API
   - Configure the OAuth consent screen:
     - Set the app name and user support email
     - Select "Internal" for the user type (or "External" if needed)
     - Add contact information
   - Create OAuth 2.0 Client ID credentials:
     - Select "Desktop app" as the application type
     - Download the credentials JSON file
     - Save the file as `credentials.json` in the project directory (or another location)
2. Find your Google Drive folder ID:
   - Navigate to your Day One backups folder in Google Drive
   - The folder ID is the part of the URL after "folders/" when you open the folder
   - Example: In `https://drive.google.com/drive/folders/1a2b3c4d5e6f7g8h9i`, the folder ID is `1a2b3c4d5e6f7g8h9i`
3. Add the folder ID and credentials file path to your `.env` file (see `.env.example` for reference)
4. Run the script with the `--google-drive` flag to download the latest backup from Google Drive

#### Authentication

The first time you run the application with Google Drive, it will open a browser window asking you to authorize access to your Google Drive. After authorization, a token will be saved to `token.json` in the project directory, so you won't need to authorize again unless the token expires.

### Day One CLI Setup (macOS only)
If you want to add the generated insights directly to your Day One journal:

1. Install the Day One CLI:
   ```
   sudo bash /Applications/Day\ One.app/Contents/Resources/install_cli.sh
   ```
   Note: You may need to enter your macOS device login password.
2. Verify the installation:
   ```
   dayone2 -h
   ```
3. Run the script with the `--add-to-journal` flag to add the generated insights to your Day One journal
   
## Usage

```
python journallm.py [input_file] [options]
```

### Command Line Options

- `input_file` or `--input PATH`: Path to a local file containing journal entries (ZIP, JSON, or XML)
- `--google-drive`: Download the latest backup from Google Drive instead of using a local file
- `--output PATH`: Output filename for advice (default: auto-generated)
- `--save-journal [PATH]`: Save journal entries (pre-processed to be more readable for Claude) as an XML file with a specified or automatically-generated name
- `--interactive [REPORT_FILE]`: Start an interactive session after processing. If REPORT_FILE is provided, use that report instead of generating one
- `--no-report`: Skip report generation (for use with --interactive or --save-journal)
- `--add-to-journal [JOURNAL]`: Add the generated report to Day One in the specified journal or the default journal if not specified (see Day One CLI Setup)
- `--debug`: Enable debug logging

### Examples

Process a local Day One backup ZIP file:
```
python journallm.py DayOneBackup.zip
# or
python journallm.py --input DayOneBackup.zip
```

Process a single JSON journal file:
```
python journallm.py journal.json
# or
python journallm.py --input journal.json
```

Process a pre-extracted XML file:
```
python journallm.py journal.xml
# or
python journallm.py --input journal.xml
```

Download and process the latest backup from Google Drive:
```
python journallm.py --google-drive
```

Save the report to a specific file:
```
python journallm.py DayOneBackup.zip --output report.md
```

Start an interactive session after generating a report:
```
python journallm.py DayOneBackup.zip --interactive
```

Start an interactive session to chat about your journal without generating a full report:
```
python journallm.py DayOneBackup.zip --no-report --interactive
```

Start an interactive session with a previously generated report:
```
python journallm.py DayOneBackup.zip --interactive advice.md
```

Extract journal entries from Google Drive without generating a report:
```
python journallm.py --google-drive --no-report --save-journal journal.xml
```

Get insights from a pre-extracted journal file:
```
python journallm.py --journal journal.xml
```

Add the generated insights to Day One (default journal):
```
python journallm.py DayOneBackup.zip --add-to-journal
```

Add the generated insights to a specific Day One journal:
```
python journallm.py DayOneBackup.zip --add-to-journal "JournalLM Reports"
```

Enable debug logging:
```
python journallm.py --debug
```

### XML Format

When processing a Day One export, JournalLM creates an XML structure with the following format:

```xml
<journal_entries>
  <entry>
    <created>2023-01-01T12:00:00Z</created>
    <modified>2023-01-01T12:00:00Z</modified>
    <journal>Journal Name 1</journal>  <!-- Only included if multiple journals -->
    <loc>Location information</loc>
    <text>Journal entry text</text>
  </entry>
  <entry>
    <created>2023-01-02T15:30:00Z</created>
    <modified>2023-01-02T15:30:00Z</modified>
    <journal>Journal Name 2</journal>  <!-- Only included if multiple journals -->
    <loc>Coffee Shop</loc>
    <text>Another journal entry</text>
  </entry>
  <!-- More entries, sorted by creation date -->
</journal_entries>
```

This is the output of the `--save-journal` flag, and the recommended input format for providing your own journal entries.

## Web Interface

JournalLM includes a web interface for easy file uploads and processing. To run the web app:

1. Make sure you have the required dependencies installed:
   ```
   pip install flask markdown2
   ```

2. Start the web server:
   ```
   python web_app.py
   ```

3. Open your browser to `http://localhost:5000`

The web interface provides:
- Simple drag-and-drop file upload
- Support for ZIP, JSON, and XML files
- Real-time processing status
- Nicely formatted report display
- Option to download report as markdown

Note: The web interface requires the `API_KEY` environment variable to be set, just like the command line interface.

## Troubleshooting

### Missing or invalid environment variables
If you see an error about missing environment variables, check that:
1. You have created a `.env` file in the project directory
2. The file contains the required variables

### Invalid input file
If you see an error processing a local file:
1. Make sure the file exists and is readable
2. Verify that it's a valid ZIP file containing JSON files or a valid JSON file
3. Check that the JSON structure matches the expected Day One format

### Missing credentials.json file
If you see an error like `Credentials file not found: credentials.json`, you need to:
1. Make sure your credentials file exists at the path specified in the `GOOGLE_CREDENTIALS_FILE` environment variable
2. If you don't have a credentials file, go to the Google Cloud Console and create one as described in the Setup section

### Authentication errors
If you encounter Google Drive authentication errors:
1. Delete the `token.json` file if it exists
2. Run the script again to go through the authentication flow
3. Make sure you grant the necessary permissions when prompted

### No Day One backup files found
If you see an error like `No Day One backup files found in the folder`:
1. Check that your FOLDER_ID is correct
2. Verify that the folder contains Day One backup ZIP files
3. Run with `--debug` flag to see more detailed information about the files in the folder

### Day One CLI not found
If you see an error like `Day One CLI not found` when using `--add-to-journal`:
1. Make sure Day One app is installed on your Mac
2. Install the CLI tool by running: `sudo bash /Applications/Day\ One.app/Contents/Resources/install_cli.sh`
3. Verify the installation by running: `dayone2 -h`

### Journal not found in Day One
If you see an error like `Journal not found in Day One`:
1. Make sure you've specified the correct journal name (case-sensitive)
2. Open Day One app and verify the journal exists
3. If you're unsure of the journal name, try using `--add-to-journal` without specifying a journal name to use the default journal
