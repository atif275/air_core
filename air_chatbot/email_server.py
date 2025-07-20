from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import os
import imaplib
import smtplib
from email.mime.text import MIMEText

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Store credentials in memory (in production, use a secure database)
credentials_store = {}

@app.route('/')
def root():
    """Root endpoint that indicates the email server is running"""
    return jsonify({
        "status": "success",
        "message": "Email server is running at 5004 port",
        "version": "1.0.0",
        "endpoints": {
            "save_credentials": "/api/email/save-credentials",
            "validate_credentials": "/api/email/validate-credentials"
        }
    })

def validate_email_credentials(email, app_password):
    """Validate email credentials by attempting to connect to Gmail's IMAP server"""
    try:
        # Try to connect to Gmail's IMAP server
        imap_server = imaplib.IMAP4_SSL('imap.gmail.com')
        imap_server.login(email, app_password)
        imap_server.logout()
        return True
    except Exception as e:
        print(f"Validation error: {str(e)}")
        return False

@app.route('/api/email/save-credentials', methods=['POST'])
def save_credentials():
    try:
        data = request.get_json()
        
        # Validate required fields
        if not all(key in data for key in ['email', 'app_password', 'device_id']):
            return jsonify({
                'status': 'error',
                'message': 'Missing required fields'
            }), 400

        email = data['email']
        app_password = data['app_password']
        device_id = data['device_id']

        # Validate credentials
        if not validate_email_credentials(email, app_password):
            return jsonify({
                'status': 'error',
                'message': 'Invalid email credentials'
            }), 401

        # Store credentials
        credentials_store[device_id] = {
            'email': email,
            'app_password': app_password
        }

        # Update .env file - preserve existing content
        env_lines = []
        email_updated = False
        app_password_updated = False
        
        # Read existing .env file if it exists
        if os.path.exists('.env'):
            with open('.env', 'r') as env_file:
                env_lines = env_file.readlines()
        
        # Update or add EMAIL field
        for i, line in enumerate(env_lines):
            if line.strip().startswith('EMAIL='):
                env_lines[i] = f'EMAIL={email}\n'
                email_updated = True
                break
        
        # Update or add APP_PASSWORD field
        for i, line in enumerate(env_lines):
            if line.strip().startswith('APP_PASSWORD='):
                env_lines[i] = f'APP_PASSWORD={app_password}\n'
                app_password_updated = True
                break
        
        # Add new fields if they don't exist
        if not email_updated:
            env_lines.append(f'EMAIL={email}\n')
        if not app_password_updated:
            env_lines.append(f'APP_PASSWORD={app_password}\n')
        
        # Write back to .env file
        with open('.env', 'w') as env_file:
            env_file.writelines(env_lines)

        return jsonify({
            'status': 'success',
            'message': 'Credentials saved successfully'
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/email/validate-credentials', methods=['POST'])
def validate_credentials():
    try:
        data = request.get_json()
        
        # Validate required fields
        if not all(key in data for key in ['email', 'app_password']):
            return jsonify({
                'status': 'error',
                'message': 'Missing required fields'
            }), 400

        email = data['email']
        app_password = data['app_password']

        # Validate credentials
        is_valid = validate_email_credentials(email, app_password)

        return jsonify({
            'status': 'success',
            'valid': is_valid,
            'message': 'Credentials are valid' if is_valid else 'Invalid credentials'
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5004, debug=True)