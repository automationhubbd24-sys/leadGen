import os
import time
import random
import base64
import secrets
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

def run_campaign_in_background(master_sheet_id, user_creds):
    """
    Runs the multi-account campaign with advanced anti-spam techniques.
    """
    sheets_service = build('sheets', 'v4', credentials=user_creds)
    gmail_service = build('gmail', 'v1', credentials=user_creds)
    
    try:
        master_sheet = sheets_service.spreadsheets().values().get(
            spreadsheetId=master_sheet_id,
            range="A:B"
        ).execute()
        accounts = master_sheet.get('values', [])
        if not accounts or len(accounts) <= 1:
            print("Master sheet is empty or has no accounts.")
            return

        for i, account_row in enumerate(accounts):
            if i == 0: continue

            account_email, campaign_sheet_id = account_row[0], account_row[1]
            print(f"Processing account: {account_email}")
            
            campaign_sheet = sheets_service.spreadsheets().values().get(
                spreadsheetId=campaign_sheet_id,
                range="A:C"
            ).execute()
            recipients = campaign_sheet.get('values', [])
            if not recipients or len(recipients) <= 1:
                print(f"Campaign sheet for {account_email} is empty.")
                continue

            for j, recipient_row in enumerate(recipients):
                if j == 0: continue

                to_email, name, subject_template = recipient_row[0], recipient_row[1], recipient_row[2]
                
                personalized_subject = subject_template.replace("{name}", name)
                
                greetings = [f"Hi {name},", f"Hello {name},", f"Dear {name},"]
                closings = ["\n\nBest regards,", "\n\nSincerely,", "\n\nCheers,"]
                
                message_body = f"{random.choice(greetings)}\n\nThis is the main content of the email.{random.choice(closings)}"
                
                unsubscribe_link = f"\n\nTo unsubscribe, please click here: http://your-domain.com/unsubscribe?email={to_email}"
                full_message = message_body + unsubscribe_link

                message = MIMEText(full_message)
                message['to'] = to_email
                message['subject'] = personalized_subject
                raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
                
                gmail_service.users().messages().send(userId='me', body={'raw': raw_message}).execute()

                print(f"Sent email to {to_email} from {account_email}")

                time.sleep(random.randint(25, 60))

    except HttpError as error:
        print(f"An error occurred: {error}")

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
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        state=state,
        redirect_uri=url_for('oauth2callback', _external=True)
    )
    
    authorization_response = request.url
    flow.fetch_token(authorization_response=authorization_response)
    
    credentials = flow.credentials
    
    service = build('oauth2', 'v2', credentials=credentials)
    user_info = service.userinfo().get().execute()

    user = User.query.filter_by(id=user_info['id']).first()
    if not user:
        user = User(
            id=user_info['id'],
            email=user_info['email'],
            refresh_token=credentials.refresh_token
        )
        db.session.add(user)
    else:
        user.refresh_token = credentials.refresh_token
    
    db.session.commit()
    
    session['credentials'] = {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }
    
    return redirect("http://localhost:3000/dashboard")

@app.route('/api/start-multi-campaign', methods=['POST'])
def start_multi_campaign():
    if 'credentials' not in session:
        return jsonify({'error': 'User not logged in'}), 401

    master_sheet_id = request.json.get('masterSheetId')
    if not master_sheet_id:
        return jsonify({'error': 'Master Sheet ID is required'}), 400

    user_creds = Credentials(**session['credentials'])

    thread = Thread(target=run_campaign_in_background, args=(master_sheet_id, user_creds))
    thread.start()

    return jsonify({'status': 'Multi-account campaign started in the background.'})

if __name__ == '__main__':
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    app.run(port=8080, debug=True)
