from flask import Flask, render_template, request, send_file, flash, redirect, url_for, Response
import re
import os
import json
import uuid
import logging
from datetime import datetime
from config import (
    PORT_NUMBER,
    TITLE,
)
from utils import (
    append_datetime,
    generate_sitrep_document_with_progress
)

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this to a random secret key

# Configure logging
def setup_logging():
    """Configure comprehensive logging for the Flask application"""
    
    # Create logs directory if it doesn't exist
    logs_dir = 'logs'
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    
    # Configure the main application logger
    app_logger = logging.getLogger('sitrep_app')
    app_logger.setLevel(logging.INFO)
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    request_formatter = logging.Formatter(
        '%(asctime)s - %(remote_addr)s - %(method)s %(url)s - %(status_code)s - %(response_time)sms'
    )
    
    # File handler for general application logs
    app_handler = logging.FileHandler(f'{logs_dir}/app.log')
    app_handler.setLevel(logging.INFO)
    app_handler.setFormatter(detailed_formatter)
    
    # File handler for request logs
    request_handler = logging.FileHandler(f'{logs_dir}/requests.log')
    request_handler.setLevel(logging.INFO)
    request_handler.setFormatter(detailed_formatter)
    
    # Console handler for development
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(detailed_formatter)
    
    # Add handlers to loggers
    app_logger.addHandler(app_handler)
    app_logger.addHandler(console_handler)
    
    # Create separate request logger
    request_logger = logging.getLogger('sitrep_requests')
    request_logger.setLevel(logging.INFO)
    request_logger.addHandler(request_handler)
    request_logger.addHandler(console_handler)
    
    return app_logger, request_logger

# Set up logging
app_logger, request_logger = setup_logging()

@app.before_request
def log_request_info():
    """Log incoming request details"""
    request.start_time = datetime.now()
    
    # Log basic request info
    request_logger.info(
        f"Incoming Request - {request.method} {request.url} - "
        f"Remote: {request.remote_addr} - "
        f"User-Agent: {request.headers.get('User-Agent', 'Unknown')}"
    )
    
    # Log form data for POST requests (excluding sensitive data)
    if request.method == 'POST' and request.form:
        form_data = {}
        for key, value in request.form.items():
            # Log form fields but truncate long values
            if len(str(value)) > 100:
                form_data[key] = str(value)[:100] + "..."
            else:
                form_data[key] = value
        request_logger.info(f"Form Data: {form_data}")
    
    # Log query parameters
    if request.args:
        request_logger.info(f"Query Parameters: {dict(request.args)}")

@app.after_request
def log_response_info(response):
    """Log response details and timing"""
    try:
        response_time = (datetime.now() - request.start_time).total_seconds() * 1000
        
        request_logger.info(
            f"Response - {request.method} {request.url} - "
            f"Status: {response.status_code} - "
            f"Time: {response_time:.2f}ms - "
            f"Size: {response.content_length or 'Unknown'} bytes"
        )
        
        # Log slow requests
        if response_time > 5000:  # More than 5 seconds
            app_logger.warning(f"Slow request detected: {request.url} took {response_time:.2f}ms")
            
    except Exception as e:
        app_logger.error(f"Error logging response: {str(e)}")
    
    return response

# Store for tracking generation progress
generation_progress = {}

@app.route('/')
def index():
    app_logger.info("Home page accessed")
    return render_template('index.html', app_title=TITLE)

@app.route('/generate', methods=['POST'])
def generate_report():
    try:
        label1_value = request.form.get('label1', '').strip()
        
        # Generate unique task ID for this generation
        task_id = str(uuid.uuid4())
        
        app_logger.info(f"Report generation started - Task ID: {task_id}, Label: '{label1_value}', Remote IP: {request.remote_addr}")
        
        # Initialize progress tracking
        generation_progress[task_id] = {
            'status': 'starting',
            'progress': 0,
            'message': 'Initializing...',
            'file_path': None,
            'filename': None,
            'error': None,
            'created_at': datetime.now().isoformat(),
            'remote_addr': request.remote_addr,
            'label': label1_value
        }
        
        return render_template('progress.html', 
                             app_title=TITLE, 
                             task_id=task_id,
                             label1_value=label1_value)
        
    except Exception as e:
        app_logger.error(f"Error starting report generation: {str(e)}", exc_info=True)
        flash(f'Error starting report generation: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/progress/<task_id>')
def progress_stream(task_id):
    """Server-Sent Events endpoint for real-time progress updates"""
    
    # Get label1_value from query parameter at the start
    label1_value = request.args.get('label1', '').strip()
    
    app_logger.info(f"Progress stream connected - Task ID: {task_id}, Remote IP: {request.remote_addr}")
    
    def generate():
        try:
            # Generate the document with progress tracking
            # Pass the label1_value that we captured from the request context
            for progress_data in generate_sitrep_document_with_progress(label1_value, task_id):
                generation_progress[task_id] = progress_data
                
                # Log progress milestones
                if progress_data.get('status') == 'completed':
                    app_logger.info(f"Report generation completed - Task ID: {task_id}, Filename: {progress_data.get('filename')}")
                elif progress_data.get('status') == 'error':
                    app_logger.error(f"Report generation failed - Task ID: {task_id}, Error: {progress_data.get('error')}")
                elif progress_data.get('progress', 0) % 25 == 0:  # Log every 25% progress
                    app_logger.info(f"Progress update - Task ID: {task_id}, Progress: {progress_data.get('progress')}%, Step: {progress_data.get('message')}")
                
                yield f"data: {json.dumps(progress_data)}\n\n"
                
        except Exception as e:
            error_data = {
                'status': 'error',
                'progress': 0,
                'message': f'Error: {str(e)}',
                'error': str(e)
            }
            generation_progress[task_id] = error_data
            app_logger.error(f"Progress stream error - Task ID: {task_id}, Error: {str(e)}", exc_info=True)
            yield f"data: {json.dumps(error_data)}\n\n"
    
    return Response(generate(), 
                   mimetype='text/event-stream',
                   headers={
                       'Cache-Control': 'no-cache',
                       'Connection': 'keep-alive',
                       'Access-Control-Allow-Origin': '*'
                   })

@app.route('/download/<task_id>')
def download_file(task_id):
    """Download the generated file"""
    try:
        app_logger.info(f"Download requested - Task ID: {task_id}, Remote IP: {request.remote_addr}")
        
        if task_id not in generation_progress:
            app_logger.warning(f"Download failed - Task ID not found: {task_id}")
            flash('File generation session not found', 'error')
            return redirect(url_for('index'))
            
        progress_data = generation_progress[task_id]
        
        if progress_data['status'] != 'completed' or not progress_data['file_path']:
            app_logger.warning(f"Download failed - File not ready: {task_id}, Status: {progress_data['status']}")
            flash('File not ready for download', 'error')
            return redirect(url_for('index'))
            
        file_path = progress_data['file_path']
        filename = progress_data['filename']
        
        # Verify file exists and has content
        if not os.path.exists(file_path):
            app_logger.error(f"Download failed - File not found: {file_path}")
            flash('Generated file not found', 'error')
            return redirect(url_for('index'))
            
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            app_logger.error(f"Download failed - File is empty: {file_path}")
            flash('Generated file is empty', 'error')
            return redirect(url_for('index'))
        
        app_logger.info(f"Download starting - Task ID: {task_id}, Filename: {filename}, Size: {file_size} bytes")
        
        # Send file and clean up after
        response = send_file(
            file_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
        
        # Add headers to help with download detection
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
        # Schedule cleanup
        @response.call_on_close
        def cleanup():
            try:
                if os.path.exists(file_path):
                    os.unlink(file_path)
                    app_logger.info(f"Temporary file cleaned up: {file_path}")
                # Clean up progress tracking
                if task_id in generation_progress:
                    del generation_progress[task_id]
                    app_logger.info(f"Progress tracking cleaned up: {task_id}")
            except Exception as cleanup_error:
                app_logger.error(f"Cleanup error for task {task_id}: {str(cleanup_error)}")
        
        return response
        
    except Exception as e:
        app_logger.error(f"Download error - Task ID: {task_id}, Error: {str(e)}", exc_info=True)
        flash(f'Error downloading file: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/status')
def status():
    """Status endpoint showing active tasks and recent activity"""
    try:
        app_logger.info(f"Status endpoint accessed from {request.remote_addr}")
        
        # Get active tasks
        active_tasks = {}
        for task_id, data in generation_progress.items():
            active_tasks[task_id] = {
                'status': data.get('status'),
                'progress': data.get('progress'),
                'message': data.get('message'),
                'created_at': data.get('created_at'),
                'remote_addr': data.get('remote_addr'),
                'label': data.get('label')
            }
        
        status_info = {
            'server_time': datetime.now().isoformat(),
            'active_tasks_count': len(active_tasks),
            'active_tasks': active_tasks,
            'logs_available': os.path.exists('logs/app.log') and os.path.exists('logs/requests.log')
        }
        
        return render_template('status.html', 
                             app_title=TITLE,
                             status_info=status_info)
        
    except Exception as e:
        app_logger.error(f"Status endpoint error: {str(e)}", exc_info=True)
        return f"Error: {str(e)}", 500

@app.route('/logs')
def view_logs():
    """View recent log entries"""
    try:
        app_logger.info(f"Logs endpoint accessed from {request.remote_addr}")
        
        log_type = request.args.get('type', 'app')  # 'app' or 'requests'
        lines = int(request.args.get('lines', 50))  # Number of lines to show
        
        if log_type == 'requests':
            log_file = 'logs/requests.log'
        else:
            log_file = 'logs/app.log'
        
        if not os.path.exists(log_file):
            return f"Log file {log_file} not found", 404
        
        # Read last N lines from log file
        with open(log_file, 'r') as f:
            all_lines = f.readlines()
            recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
        
        return render_template('logs.html',
                             app_title=TITLE,
                             log_type=log_type,
                             log_lines=recent_lines,
                             total_lines=len(all_lines))
        
    except Exception as e:
        app_logger.error(f"Logs endpoint error: {str(e)}", exc_info=True)
        return f"Error: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=PORT_NUMBER)