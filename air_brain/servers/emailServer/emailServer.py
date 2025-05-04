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

        # Update .env file
        with open('.env', 'w') as env_file:
            env_file.write(f'EMAIL_USER={email}\n')
            env_file.write(f'EMAIL_PASSWORD={app_password}\n')

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