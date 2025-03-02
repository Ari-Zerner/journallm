# JournalLM

JournalLM is a Python script that provides personalized insights based on your Day One journal entries. It leverages Claude AI to analyze your journal and generate helpful observations, suggestions, and advice.

## Setup

1. Clone this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Set up Google Drive API:
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
4. Create a `.env` file based on the `.env.example` template.
5. Find your Google Drive folder ID:
   - Navigate to your Day One backups folder in Google Drive
   - The folder ID is the part of the URL after "folders/" when you open the folder
   - Example: In `https://drive.google.com/drive/folders/1a2b3c4d5e6f7g8h9i`, the folder ID is `1a2b3c4d5e6f7g8h9i`
6. Get an Anthropic API key:
   - Sign up at [Anthropic](https://www.anthropic.com/)
   - Create an API key and add it to your `.env` file

## Usage

```
python journallm.py [output_filename] [options]
```

### Command Line Options

- `output_filename`: Optional output filename (default: auto-generated)
- `--debug`: Enable debug logging
- `--extract-only`: Only extract journal entries, don't prompt Claude
- `--journal-file PATH`: Path to pre-extracted journal XML file (skips extraction)

### Examples

Full process (extract journal and get insights):
```
python journallm.py insights.md
```

Extract journal entries only:
```
python journallm.py journal.xml --extract-only
```

Get insights from a pre-extracted journal file:
```
python journallm.py insights.md --journal-file journal.xml
```

Enable debug logging:
```
python journallm.py --debug
```

## How It Works

1. The script connects to Google Drive and downloads the most recent Day One backup
2. It extracts journal entries from the backup and processes them into a structured format
3. The entries are sent to Claude AI with a carefully designed prompt
4. Claude analyzes your journal and provides personalized insights and advice
5. The response is saved as a markdown file for you to review

## Authentication

The first time you run the application, it will open a browser window asking you to authorize access to your Google Drive. After authorization, a token will be saved to `token.json` in the project directory, so you won't need to authorize again unless the token expires.

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
