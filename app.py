# requirements.txt
# flask google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client PyPDF2

from flask import Flask, redirect, url_for, session, request, jsonify, send_from_directory
from flask_cors import CORS
from flask import request
from flask import abort
import os
import io
from dotenv import load_dotenv
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from google.cloud import storage
import PyPDF2
import base64
import re
import hashlib
from datetime import datetime
import json
from werkzeug.middleware.proxy_fix import ProxyFix


# Load environment variables
load_dotenv()

# Allow insecure transport for local development
if os.environ.get('FLASK_ENV') == 'development':
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

app = Flask(
    __name__,
    static_folder=os.path.join("frontend", "dist"),
    template_folder=os.path.join("frontend", "dist")
)

app.config.update(
    SESSION_COOKIE_SAMESITE='None',  # allow cross-site cookie on XHR/fetch
    SESSION_COOKIE_SECURE=True       # required by Chrome when SameSite=None
)

# Use ProxyFix to force HTTPS headers in production
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Update CORS for both local and production
allowed_origins = ["http://localhost:5173"]
if os.environ.get("FLASK_ENV") != "development":
    # Add your Cloud Run URL - replace with your actual URL
    cloud_run_url = os.environ.get("CLOUD_RUN_URL", "https://....")
    allowed_origins.append(cloud_run_url)

CORS(app, supports_credentials=True, origins=allowed_origins, allow_headers=["Content-Type"])  # Enable CORS for all routes
app.secret_key = os.environ.get('SECRET_KEY', 'fallback_secret_for_dev')

# Set your CLIENT_SECRETS_FILE to the path to your credentials.json file
CLIENT_SECRETS_FILE = os.environ.get("GOOGLE_CLIENT_SECRETS_FILE", "/app/credentials.prod.json")
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']


#Logging middleware to log requests and responses  
# @app.after_request
# def after_request(response):
#     print(f"{request.method} {request.pAath} - {response.status}")
#     return response

# Set the path to the paid invoices file now using GCS bucket for JSON file
GCS_BUCKET = os.environ.get("GCS_BUCKET_NAME", "invoice-status")
GCS_BLOB = "paid_invoices.json"

def _load_oauth_client():
    # Load client_id / client_secret from the same file you already mount
    with open(CLIENT_SECRETS_FILE, "r") as f:
        data = json.load(f)
    info = data.get("web") or data.get("installed") or {}
    return info.get("client_id"), info.get("client_secret")

def get_gcs_client():
    return storage.Client()

def load_paid_invoices():
    client = get_gcs_client()
    bucket = client.bucket(GCS_BUCKET)
    blob = bucket.blob(GCS_BLOB)
    if not blob.exists():
        return set()
    content = blob.download_as_text().strip()
    if not content:
        return set()
    return set(json.loads(content))

def save_paid_invoices(paid_invoices):
    client = get_gcs_client()
    bucket = client.bucket(GCS_BUCKET)
    blob = bucket.blob(GCS_BLOB)
    blob.upload_from_string(json.dumps(list(paid_invoices)), content_type='application/json')

# The old route before containerization
# @app.route("/")
# def index():
#     if 'credentials' not in session:
#         return redirect(url_for('authorize'))
#     return "Connected! <a href='/scan_invoices'>Scan for invoices</a>"

#Debugging print statement to check the CLIENT_SECRETS_FILE path
#print("CLIENT_SECRETS_FILE =", CLIENT_SECRETS_FILE)

@app.route("/authorize")
def authorize():
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, scopes=SCOPES,
        redirect_uri=url_for('oauth2callback', _external=True))
    authorization_url, state = flow.authorization_url(
        access_type='offline', include_granted_scopes='true', prompt='consent')
    session['state'] = state
    return redirect(authorization_url)

@app.route("/oauth2callback")
def oauth2callback():
    if request.args.get('state') != session.get('state'):
        abort(400, description="Invalid OAuth state")
    session.pop('state', None) 
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, scopes=SCOPES,
        redirect_uri=url_for('oauth2callback', _external=True))
    flow.fetch_token(authorization_response=request.url)
    creds = flow.credentials
    if not creds.refresh_token:
        # Ask for consent again to obtain a refresh token
        return redirect(url_for('authorize'))
    session['credentials'] = {
        'token': creds.token,
        'refresh_token': creds.refresh_token,
        'token_uri': creds.token_uri,
        'client_id': creds.client_id,
        # 'client_secret': creds.client_secret, #reducing cookie size
         'scopes': creds.scopes 
    }
    return redirect(url_for('serve_react', path=''))

@app.route("/scan_invoices")
def scan_invoices():
    try:
        if 'credentials' not in session:
            return jsonify({"error": "not_authenticated", "message": "Please authenticate first"}), 401

        # Load OAuth client
        try:
            client_id, client_secret = _load_oauth_client()
        except Exception as e:
            print(f"[oauth_client_load_failed] {e}")
            return jsonify({"error": "oauth_client_load_failed", "details": str(e)}), 502

        # Create credentials
        try:
            creds = Credentials(
                token=session['credentials']['token'],
                refresh_token=session['credentials']['refresh_token'],
                token_uri=session['credentials']['token_uri'],
                client_id=client_id,
                client_secret=client_secret,
                scopes=SCOPES
            )
        except Exception as e:
            print(f"[credentials_creation_failed] {e}")
            return jsonify({"error": "credentials_invalid", "details": str(e)}), 500

        # Build service
        try:
            service = build('gmail', 'v1', credentials=creds)
        except Exception as e:
            print(f"[gmail_build_failed] {e}")
            return jsonify({"error": "gmail_build_failed", "details": str(e)}), 502

        # Test with profile
        try:
            profile = service.users().getProfile(userId='me').execute()
            user_email = profile.get('emailAddress')
        except HttpError as http_err:
            print(f"[gmail_profile_failed] HTTP {http_err.resp.status}: {http_err}")
            if http_err.resp.status == 401:
                return jsonify({"error": "gmail_auth_failed", "message": "Gmail authentication failed"}), 401
            elif http_err.resp.status == 403:
                return jsonify({"error": "gmail_forbidden", "message": "Gmail access forbidden"}), 403
            else:
                return jsonify({"error": "gmail_http_error", "details": str(http_err)}), 502
        except Exception as e:
            print(f"[gmail_profile_failed] {e}")
            return jsonify({"error": "gmail_profile_failed", "details": str(e)}), 502

        # ---- Valid Gmail query (no '*@domain') ----

        # Uncomment and change the query as needed for your nursery invoices
        # query = (
        #    '(from:finance@nursery.co.uk '
        #    'OR from:notification@xxxx.co '
        #    'OR from:xxxx.co '
        #    'has:attachment filename:invoice*pdf newer_than:6m'
        # )

        # ---- List messages (surface API errors) ----
        try:
            results = service.users().messages().list(userId='me', q=query).execute()  # Process all messages
        except HttpError as e:
            print(f"[gmail_list_failed] {e}")
            return jsonify({"error": "gmail_list_failed", "details": str(e)}), 502
        except Exception as e:
            print(f"[gmail_list_failed_other] {e}")
            return jsonify({"error": "gmail_list_failed_other", "details": str(e)}), 502

        messages = results.get('messages', []) or []

        # ---- Load paid invoices; never crash on GCS ----
        try:
            paid_invoices = load_paid_invoices()
        except Exception as e:
            print(f"[gcs] load_paid_invoices failed: {e}")
            paid_invoices = set()

        invoices, seen_ids = [], set()

        # ---- Parse attachments with memory management ----
        for i, msg in enumerate(messages):  # Process all messages
            try:
                m = service.users().messages().get(userId='me', id=msg['id']).execute()
                parts = m.get('payload', {}).get('parts', []) or []
                for part in parts:
                    if not part.get('filename', '').lower().endswith('.pdf'):
                        continue
                    
                    # Check attachment size to avoid memory issues
                    attachment_size = part.get('body', {}).get('size', 0)
                    if attachment_size > 5 * 1024 * 1024:  # 5MB limit
                        print(f"Skipping large PDF: {part['filename']} ({attachment_size} bytes)")
                        continue
                    
                    att_id = part.get('body', {}).get('attachmentId')
                    if not att_id:
                        continue
                    att = service.users().messages().attachments().get(
                        userId='me', messageId=msg['id'], id=att_id
                    ).execute()
                    data_b64 = att.get('data')
                    if not data_b64:
                        continue

                    data = base64.urlsafe_b64decode(data_b64)
                    
                    # Calculate hash before processing (needed for invoice ID)
                    pdf_hash = hashlib.sha1(data).hexdigest()[:12]
                    
                    # Process PDF with memory management
                    try:
                        pdf_reader = PyPDF2.PdfReader(io.BytesIO(data))
                        # Limit to first 3 pages to avoid memory issues
                        pages_to_process = min(3, len(pdf_reader.pages))
                        text = ''.join((page.extract_text() or '') for page in pdf_reader.pages[:pages_to_process])
                        
                        # Clear PDF data from memory immediately
                        del data
                        del pdf_reader
                        
                    except Exception as pdf_error:
                        print(f"PDF processing error {part.get('filename')}: {pdf_error}")
                        continue

                    # Amount patterns
                    match = re.search(r'Payment Due[:\s]*£?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', text, re.IGNORECASE)
                    if not match:
                        for pattern in [
                            r'(?:total|amount due|balance)[\s:]*£?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
                            r'£\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
                            r'(\d+\.\d{2})'
                        ]:
                            match = re.search(pattern, text, re.IGNORECASE)
                            if match:
                                break
                    if not match:
                        continue

                    try:
                        amount = float(match.group(1).replace(',', ''))
                    except ValueError:
                        continue
                    if not (10.0 <= amount <= 10000.0):
                        continue

                    ts_ms = int(m['internalDate'])
                    readable_date = datetime.fromtimestamp(ts_ms / 1000).strftime('%Y-%m-%d')

                    # Canonical ID + legacy compat
                    mno = re.search(r'(?:invoice\s*(?:no|number)\s*[:#]?\s*)([A-Z0-9-]{4,})', text, re.IGNORECASE)
                    invoice_no = mno.group(1).upper() if mno else None
                    canonical_id = invoice_no if invoice_no else pdf_hash
                    legacy_id = f"{readable_date}-{amount:.2f}"

                    if canonical_id in seen_ids:
                        continue
                    seen_ids.add(canonical_id)

                    invoices.append({
                        'id': canonical_id,
                        'date': readable_date,
                        'amount': amount,
                        'deposit_required': round(amount * 0.8, 2),
                        'paid': (canonical_id in paid_invoices) or (legacy_id in paid_invoices)
                    })

            except Exception as e:
                print(f"Error processing message {msg.get('id')}: {e}")
                continue

        return jsonify(invoices)

    except Exception as e:
        # Final safety net so we *always* return JSON, never raw 503
        print(f"[scan_invoices_failed] {e}")
        return jsonify({"error": "scan_invoices_failed", "details": str(e)}), 502

#Endpoint to mark an invoice as paid
@app.route("/mark_paid", methods=["POST", "OPTIONS"])
def mark_paid():
    if request.method == "OPTIONS":
        # This is the preflight request
        return '', 200
    # Existing POST logic:
    data = request.json
    invoice_id = data.get("id")
    paid_invoices = load_paid_invoices()
    paid_invoices.add(invoice_id)
    save_paid_invoices(paid_invoices)
    return jsonify({"status": "success"})

#Endpoint to mark an invoice as unpaid
@app.route("/mark_unpaid", methods=["POST", "OPTIONS"])
def mark_unpaid():
    if request.method == "OPTIONS":
        # This is the preflight request
        return '', 200
    # Remove from paid invoices:
    data = request.json
    invoice_id = data.get("id")
    paid_invoices = load_paid_invoices()
    paid_invoices.discard(invoice_id)  # discard won't raise error if not present
    save_paid_invoices(paid_invoices)
    return jsonify({"status": "success"})

# Debug route to check session state
@app.route("/debug/session")
def debug_session():
    return jsonify({
        "has_credentials": 'credentials' in session,
        "session_keys": list(session.keys()),
        "credentials_keys": list(session.get('credentials', {}).keys()) if 'credentials' in session else [],
        "user_agent": request.headers.get('User-Agent', 'Unknown'),
        "remote_addr": request.remote_addr,
        "flask_env": os.environ.get('FLASK_ENV', 'not_set')
    })

# Catch-all route for React/Vite SPA support
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_react(path):
    """
    Serve static files from the Vite 'dist' folder.
    If the file doesn't exist, serve 'index.html' (for React Router).
    """
    file_path = os.path.join(app.static_folder, path)
    if path != "" and os.path.exists(file_path):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')

if __name__ == '__main__':
    # Only enable debug if running locally
    app.run(debug=os.environ.get("FLASK_ENV") == "development")
