import os
import time
import random
import base64
from email.mime.text import MIMEText
from threading import Thread

from flask import Flask, redirect, session, request, url_for, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
CORS(app, supports_credentials=True, origins=["http://localhost:3000"])

CLIENT_SECRETS_FILE = "credentials.json"
SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid"
]

class User(db.Model):
    id = db.Column(db.String(100), primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    refresh_token = db.Column(db.String(500), nullable=False)

with app.app_context():
    db.create_all()

def get_google_client_config():
    import json
    with open(CLIENT_SECRETS_FILE, 'r') as f:
        return json.load()['web']

def run_campaign_in_background(master_sheet_id):
    client_config = get_google_client_config()
    try:
        # Use a dummy credential to build the initial service
        dummy_creds = Credentials(
            None, token_uri=client_config['token_uri'],
            client_id=client_config['client_id'], client_secret=client_config['client_secret']
        )
        sheets_service = build('sheets', 'v4', credentials=dummy_creds)
        
        master_sheet = sheets_service.spreadsheets().values().get(
            spreadsheetId=master_sheet_id, range="A:C"
        ).execute()
        
        accounts = master_sheet.get('values', [])
        if not accounts or len(accounts) <= 1:
            print("Master sheet is empty or has no accounts.")
            return

        for i, account_row in enumerate(accounts):
            if i == 0: continue
            if len(account_row) < 3:
                print(f"Skipping incomplete row in master sheet: {account_row}")
                continue

            account_email, refresh_token, campaign_sheet_id = account_row
            print(f"Processing account: {account_email}")

            # 1. Create credentials for the current account using its refresh token
            current_creds = Credentials(
                None,
                refresh_token=refresh_token,
                token_uri=client_config['token_uri'],
                client_id=client_config['client_id'],
                client_secret=client_config['client_secret'],
                scopes=SCOPES
            )

            # 2. Build services with the new credentials
            gmail_service = build('gmail', 'v1', credentials=current_creds)
            current_sheets_service = build('sheets', 'v4', credentials=current_creds)

            # 3. Read the campaign sheet for the current account
            campaign_sheet = current_sheets_service.spreadsheets().values().get(
                spreadsheetId=campaign_sheet_id, range="A:D"
            ).execute()
            
            recipients = campaign_sheet.get('values', [])
            if not recipients or len(recipients) <= 1:
                print(f"Campaign sheet for {account_email} is empty.")
                continue

            # 4. Send emails for the current account
            for j, recipient_row in enumerate(recipients):
                if j == 0: continue
                if len(recipient_row) < 4:
                    print(f"Skipping incomplete row in campaign sheet: {recipient_row}")
                    continue
                
                recipient_email, name, subject, body = recipient_row
                
                final_subject = subject.replace('{name}', name)
                final_body = body.replace('{name}', name)

                message = MIMEText(final_body)
                message['to'] = recipient_email
                message['from'] = account_email
                message['subject'] = final_subject
                raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
                
                try:
                    gmail_service.users().messages().send(
                        userId='me', body={'raw': raw_message}
                    ).execute()
                    print(f"Email sent to {recipient_email} from {account_email}")
                except Exception as e:
                    print(f"Failed to send email to {recipient_email}: {e}")
                
                time.sleep(random.uniform(5, 15))
    except Exception as e:
        print(f"An error occurred in the background campaign: {e}")

@app.route('/api/login')
def login():
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=url_for('oauth2callback', _external=True)
    )
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        prompt='consent',
        include_granted_scopes='true'
    )
    session['state'] = state
    return jsonify({'authorization_url': authorization_url})

@app.route('/oauth2callback')
def oauth2callback():
    state = session['state']
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, scopes=SCOPES, state=state,
        redirect_uri=url_for('oauth2callback', _external=True)
    )
    flow.fetch_token(authorization_response=request.url)
    credentials = flow.credentials
    session['credentials'] = {
        'token': credentials.token, 'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri, 'client_id': credentials.client_id,
        'client_secret': credentials.client_secret, 'scopes': credentials.scopes
    }
    return redirect("http://localhost:3000/dashboard")

@app.route('/api/start-multi-campaign', methods=['POST'])
def start_multi_campaign():
    master_sheet_id = request.json.get('masterSheetId')
    if not master_sheet_id:
        return jsonify({'error': 'Master Sheet ID is required'}), 400

    thread = Thread(target=run_campaign_in_background, args=(master_sheet_id,))
    thread.start()
    return jsonify({'status': 'Campaign started. Check terminal for progress.'})

if __name__ == '__main__':
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    app.run(port=8080, debug=True)
