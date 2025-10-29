from flask import Flask, render_template, request, send_file, flash, redirect, url_for
import re
import os
from config import (
    PORT_NUMBER,
    TITLE,
    OUTPUT_FILE_NAME,
    DELAY_MS
)
from utils import (
    append_datetime,
    generate_sitrep_document
)

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this to a random secret key

@app.route('/')
def index():
    return render_template('index.html', app_title=TITLE, delay_ms=DELAY_MS)

@app.route('/generate', methods=['POST'])
def generate_report():
    try:
        label1_value = request.form.get('label1', '').strip()
        
        # Generate the document
        file_path = generate_sitrep_document(label1_value)
        
        # Verify file exists and has content
        if not os.path.exists(file_path):
            raise Exception("Generated file does not exist")
        
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            raise Exception("Generated file is empty")
        
        # Create filename with timestamp
        base_filename = OUTPUT_FILE_NAME
        if label1_value:
            # Replace spaces and special characters for filename
            safe_label = re.sub(r'[^\w\-_]', '_', label1_value)
            base_filename = f'{base_filename}_{safe_label}'
        
        filename = append_datetime(base_filename) + '.docx'
        
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
        
        # Schedule file cleanup
        @response.call_on_close
        def cleanup():
            try:
                if os.path.exists(file_path):
                    os.unlink(file_path)
            except Exception:
                pass
        
        return response
        
    except Exception as e:
        flash(f'Error generating report: {str(e)}', 'error')
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=PORT_NUMBER)