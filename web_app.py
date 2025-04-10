#!/usr/bin/env python3
"""
JournalLM Web App - Web interface for JournalLM
"""

import os
import uuid
import threading
import tempfile
import logging
import time
import argparse
from typing import Dict, Optional
from datetime import datetime, timedelta

from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import markdown2

from journallm import JournalLM

# Load environment variables
load_dotenv()

# Set up logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

# Configure upload settings
ALLOWED_EXTENSIONS = {'zip', 'json', 'xml'}
MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB limit

# Job storage
jobs: Dict[str, dict] = {}

# Development mode flag
DEV_MODE = False

def allowed_file(filename: str) -> bool:
    """Check if the file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def clean_old_jobs() -> None:
    """Remove jobs older than 1 hour"""
    now = datetime.now()
    expired = [job_id for job_id, job in jobs.items() 
              if now - job['timestamp'] > timedelta(hours=1)]
    for job_id in expired:
        try:
            job = jobs.pop(job_id)
            if job.get('output_file') and os.path.exists(job['output_file']):
                os.remove(job['output_file'])
        except Exception as e:
            logger.error(f"Error cleaning up job {job_id}: {e}")

def process_mock_report(job_id: str) -> None:
    """Process a mock report for development mode"""
    try:
        time.sleep(3)  # Simulate processing time
        
        # Read the mock report
        with open('mock_report.md', 'r', encoding='utf-8') as f:
            report = f.read()
        
        # Create a temporary file for output
        output_file = os.path.join(tempfile.gettempdir(), f'advice-{job_id}.md')
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        # Update job status
        jobs[job_id].update({
            'status': 'complete',
            'output_file': output_file,
            'report': report
        })
        
    except Exception as e:
        logger.error(f"Error processing mock report: {e}")
        jobs[job_id].update({
            'status': 'error',
            'error': str(e)
        })

def process_file(job_id: str, input_file: Optional[str], api_key: Optional[str] = None, use_mock: bool = False) -> None:
    """Process the uploaded file in a background thread"""
    try:
        if use_mock:
            process_mock_report(job_id)
            return
            
        # Use provided API key or get from environment
        api_key = api_key or os.getenv('API_KEY')
        if not api_key:
            raise ValueError("API key is required")
        
        journallm = JournalLM(api_key=api_key)
        
        # Create a temporary file for output
        output_file = os.path.join(tempfile.gettempdir(), f'advice-{job_id}.md')
        
        # Process the file
        jobs[job_id]['status'] = 'processing'
        journal_xml = journallm.extract_journal_from_file(input_file)
        
        if not journal_xml:
            raise Exception("Failed to extract journal entries")
        
        # Get insights from Claude
        report = journallm.claude_prompter.get_report(journal_xml)
        if not report:
            raise Exception("Failed to get insights from Claude")
        
        # Save the report
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        # Update job status
        jobs[job_id].update({
            'status': 'complete',
            'output_file': output_file,
            'report': report
        })
        
    except Exception as e:
        logger.error(f"Error processing job {job_id}: {e}")
        jobs[job_id].update({
            'status': 'error',
            'error': str(e)
        })
    finally:
        # Clean up input file
        if input_file and os.path.exists(input_file):
            try:
                os.remove(input_file)
            except Exception as e:
                logger.error(f"Error removing input file: {e}")

@app.route('/')
def index():
    """Render the main page"""
    api_key = os.getenv('API_KEY')
    return render_template('index.html', api_key=api_key, dev_mode=DEV_MODE)

@app.route('/upload', methods=['POST'])
def upload():
    """Handle file upload and start processing"""
    # Get API key from request or environment
    api_key = request.form.get('api_key') or os.getenv('API_KEY')
    use_mock = DEV_MODE and request.form.get('use_mock') == 'true'
    
    if not use_mock and not api_key:
        return jsonify({'error': 'API key is required'}), 400
    
    input_file = None
    filename = 'mock_report.md'
    
    # Handle file upload if provided (optional in mock mode)
    if 'file' in request.files:
        file = request.files['file']
        if file.filename:
            if not allowed_file(file.filename):
                return jsonify({'error': 'Invalid file type. Please upload a ZIP, JSON, or XML file.'}), 400
            
            # Generate a unique job ID early for the filename
            job_id = str(uuid.uuid4())
            
            # Save the uploaded file
            filename = secure_filename(file.filename)
            input_file = os.path.join(tempfile.gettempdir(), f'{job_id}-{filename}')
            file.save(input_file)
    elif not use_mock:
        # File is required if not in mock mode
        return jsonify({'error': 'No file uploaded'}), 400
    
    try:
        # Generate a unique job ID if not already done
        if not 'job_id' in locals():
            job_id = str(uuid.uuid4())
        
        # Create a new job
        jobs[job_id] = {
            'status': 'starting',
            'timestamp': datetime.now(),
            'filename': filename
        }
        
        # Start processing in a background thread
        thread = threading.Thread(target=process_file, args=(job_id, input_file, api_key, use_mock))
        thread.start()
        
        # Clean up old jobs
        clean_old_jobs()
        
        return jsonify({'job_id': job_id})
        
    except Exception as e:
        logger.error(f"Error handling upload: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/status/<job_id>')
def status(job_id: str):
    """Get the status of a job"""
    if job_id not in jobs:
        return jsonify({'error': 'Job not found'}), 404
    
    job = jobs[job_id]
    response = {
        'status': job['status'],
        'filename': job['filename']
    }
    
    if job['status'] == 'error':
        response['error'] = job.get('error', 'Unknown error')
    elif job['status'] == 'complete':
        response['redirect'] = url_for('show_report', job_id=job_id)
    
    return jsonify(response)

@app.route('/report/<job_id>')
def show_report(job_id: str):
    """Show the report"""
    if job_id not in jobs:
        return redirect(url_for('index'))
    
    job = jobs[job_id]
    if job['status'] != 'complete':
        return redirect(url_for('index'))
    
    # Convert markdown to HTML
    report_html = markdown2.markdown(job['report'], extras=['fenced-code-blocks'])
    
    return render_template('report.html', report=report_html, job_id=job_id)

@app.route('/download/<job_id>')
def download_report(job_id: str):
    """Download the report file"""
    if job_id not in jobs:
        return jsonify({'error': 'Job not found'}), 404
    
    job = jobs[job_id]
    if job['status'] != 'complete':
        return jsonify({'error': 'Job not complete'}), 400
    
    if not job.get('output_file') or not os.path.exists(job['output_file']):
        return jsonify({'error': 'Output file not found'}), 404
    
    try:
        return send_file(
            job['output_file'],
            as_attachment=True,
            download_name=f'journallm-advice-{datetime.now().strftime("%Y%m%d-%H%M%S")}.md'
        )
    except Exception as e:
        logger.error(f"Error sending file: {e}")
        return jsonify({'error': 'Error downloading file'}), 500

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='JournalLM Web Interface')
    parser.add_argument('--dev', action='store_true', help='Enable development mode')
    args = parser.parse_args()
    
    global DEV_MODE
    DEV_MODE = args.dev
    
    if DEV_MODE:
        logger.info("Running in development mode")
        app.debug = True
    
    app.run()

if __name__ == '__main__':
    main()