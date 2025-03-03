# JournalLM

JournalLM is a Python script that provides personalized insights based on your Day One journal entries. It leverages Claude AI to analyze your journal and generate helpful observations, suggestions, and advice.

## Setup

1. Clone this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Create a `.env` file based on the `.env.example` template.
4. Get an Anthropic API key:
   - Sign up at [Anthropic](https://www.anthropic.com/)
   - Create an API key and add it to your `.env` file

### Optional: Google Drive Setup
If you want to automatically download Day One backups from Google Drive:

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
3. Add the folder ID and credentials file path to your `.env` file

## Usage

```
python journallm.py [input_file] [options]
```

### Command Line Options

- `input_file`: Path to a local ZIP or JSON file containing journal entries (optional)
- `--google-drive`: Download the latest backup from Google Drive instead of using a local file
- `--output PATH`: Output filename for advice (default: auto-generated)
- `--save-journal [PATH]`: Output extracted journal (without this flag, the journal is not saved. If given without a path, the journal is saved with a default filename in the current directory.)
- `--extract-only`: Only extract journal entries, don't prompt Claude
- `--journal PATH`: Path to pre-extracted journal XML file (skips extraction)
- `--debug`: Enable debug logging

### Examples

Process a local Day One backup ZIP file:
```
python journallm.py DayOneBackup.zip
```

Process a single JSON journal file:
```
python journallm.py journal.json
```

Download and process the latest backup from Google Drive:
```
python journallm.py --google-drive
```

Extract journal entries only from a local file:
```
python journallm.py DayOneBackup.zip --extract-only --save-journal journal.xml
```

Extract journal entries from Google Drive with auto-generated filename:
```
python journallm.py --google-drive --extract-only --save-journal
```

Get insights from a pre-extracted journal file:
```
python journallm.py --journal journal.xml --output insights.md
```

Enable debug logging:
```
python journallm.py --debug
```

## How It Works

1. The script can:
   - Process a local Day One backup ZIP file
   - Process a single JSON journal file
   - Connect to Google Drive and download the most recent Day One backup
   - Use a pre-extracted journal XML file
2. It extracts journal entries and processes them into a structured XML format
3. The entries are sent to Claude AI with a carefully designed prompt
4. Claude analyzes your journal and provides personalized insights and advice
5. The response is saved as a markdown file for you to review

## XML Format

When processing journal entries, JournalLM creates an XML structure with the following format:

```xml
<journals>
  <journal name="journal-name-1">
    <entry>
      <created>2023-01-01T12:00:00Z</created>
      <modified>2023-01-01T12:00:00Z</modified>
      <loc>Location information</loc>
      <text>Journal entry text</text>
    </entry>
    <!-- More entries -->
  </journal>
  <journal name="journal-name-2">
    <!-- Entries for second journal -->
  </journal>
</journals>
```

The journal name is derived from the JSON filename (without extension).

## Authentication

The first time you run the application with Google Drive, it will open a browser window asking you to authorize access to your Google Drive. After authorization, a token will be saved to `token.json` in the project directory, so you won't need to authorize again unless the token expires.

## Troubleshooting

### Missing credentials.json file
If you see an error like `Credentials file not found: credentials.json`, you need to:
1. Make sure your credentials file exists at the path specified in the `GOOGLE_CREDENTIALS_FILE` environment variable
2. If you don't have a credentials file, go to the Google Cloud Console and create one as described in the Setup section

### Missing or invalid environment variables
If you see an error about missing environment variables, check that:
1. You have created a `.env` file in the project directory
2. The file contains the required variables (FOLDER_ID, GOOGLE_CREDENTIALS_FILE, and API_KEY)
3. The values are correct (no extra spaces or quotes)

### Authentication errors
If you encounter authentication errors:
1. Delete the `token.json` file if it exists
2. Run the script again to go through the authentication flow
3. Make sure you grant the necessary permissions when prompted

### No Day One backup files found
If you see an error like `No Day One backup files found in the folder`:
1. Check that your FOLDER_ID is correct
2. Verify that the folder contains Day One backup files (they should have "Day One" in the name and end with ".zip")
3. Run with `--debug` flag to see more detailed information about the files in the folder

### Invalid local file
If you see an error processing a local file:
1. Make sure the file exists and is readable
2. Verify that it's a valid ZIP file containing JSON files or a valid JSON file
3. Check that the JSON structure matches the expected Day One format
4. Run with `--debug` flag to see more detailed error information
