# Nursery Invoice Scanner

App that saves you the hassle of having to find the latest invoice from your nursery and work out how much money to add to your government childcare account. Automatically scans your Gmail for nursery invoices and tells you how much you need to pay into your government childcare account.

## Features

- 🔍 **Automatic Gmail Scanning**: Searches your Gmail for nursery invoices from common providers
- 💰 **Smart Amount Detection**: Extracts invoice amounts using multiple pattern matching techniques
- 📊 **Payment Calculation**: Automatically calculates 80% deposit required for government childcare accounts
- ✅ **Payment Tracking**: Mark invoices as paid to keep track of what's been processed
- 🔐 **Secure OAuth**: Uses Google OAuth2 for secure Gmail access
- 📱 **Modern Web Interface**: Clean React frontend with mobile-friendly design
- ☁️ **Cloud Ready**: Deploys easily to Google Cloud Run or any Docker-compatible platform

## Supported Nursery Providers

The app is designed to work with any nursery that sends PDF invoices via email. You'll need to customize the email patterns for your specific providers. Examples include:
- Nurseries that send from `finance@nursery-name.com`
- Childcare management platforms like Famly.co
- Any provider that sends PDF invoices with consistent formatting

## Quick Start

### Prerequisites

- Google Account with Gmail access
- Node.js 16+ (for frontend development)
- Python 3.8+ (for backend)
- Docker (for containerized deployment - optional)
- Google Cloud account (for Cloud Run deployment - optional)

### 1. Clone the Repository

```bash
git clone https://github.com/YourUsername/gmail-childcare-invoices.git
cd gmail-childcare-invoices
```

### 2. Set Up Google OAuth2 Credentials

1. **Create a Google Cloud Project**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing one
   - Enable the Gmail API for your project

2. **Create OAuth2 Credentials**:
   - Navigate to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Choose "Web application"
   - Add authorized redirect URIs:
     - For local development: `http://localhost:5000/oauth2callback`
     - For production: `https://your-domain.com/oauth2callback`
   - Download the credentials JSON file

3. **Configure Credentials**:
   ```bash
   # Rename your downloaded credentials file
   cp path/to/your/downloaded/credentials.json credentials.prod.json
   
   # For development, you can also create:
   cp credentials.prod.json credentials.dev.json
   ```

### 3. Configure Email Patterns

**IMPORTANT**: You must configure the Gmail query to match your nursery's email patterns. 

1. Open `app.py` and find the commented query around line 194:

```python
# Uncomment and change the query as needed for your nursery invoices
query = (
   '(from:finance@your-nursery.com '
   'OR from:notifications@your-provider.com '
   'OR from:billing@another-nursery.com) '
   'has:attachment filename:invoice*pdf newer_than:6m'
)
```

2. Replace the email addresses with your actual nursery providers
3. Uncomment the query by removing the `#` symbols
4. Adjust the time frame (`newer_than:6m` means 6 months) as needed

**Examples of common patterns:**
- `from:finance@nurseryname.co.uk`
- `from:billing@nurserysoftware.com` 
- `from:invoices@famly.co`
- `subject:invoice` (if emails don't have specific senders)

### 4. Development Setup

#### Backend Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the Flask app
python app.py
```

#### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Visit `http://localhost:5000` to access the application.

## Deployment Options

### Option 1: Google Cloud Run (Recommended)

**First-time setup:**

1. Install the Google Cloud CLI from [cloud.google.com/sdk](https://cloud.google.com/sdk)
2. Authenticate and set up your project:
   ```bash
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   gcloud config set run/region YOUR_PREFERRED_REGION  # e.g., us-central1, europe-west1
   ```

3. Enable required APIs:
   ```bash
   gcloud services enable run.googleapis.com
   gcloud services enable artifactregistry.googleapis.com
   ```

4. Create an Artifact Registry repository:
   ```bash
   gcloud artifacts repositories create nursery-invoice-repo \
     --repository-format=docker \
     --location=YOUR_REGION
   ```

**Deploy using the provided script:**

1. Edit `deploy.sh` and update the configuration section:
   ```bash
   PROJECT_ID="your-actual-project-id"
   REGION="your-preferred-region"
   REPO="nursery-invoice-repo"
   ```

2. Deploy:
   ```bash
   chmod +x deploy.sh
   ./deploy.sh
   ```

**Manual Cloud Run Deployment:**

```bash
# Build and push to Artifact Registry
gcloud builds submit --tag REGION-docker.pkg.dev/PROJECT_ID/REPO/nursery-invoice-app

# Deploy to Cloud Run
gcloud run deploy nursery-invoice-app \
  --image REGION-docker.pkg.dev/PROJECT_ID/REPO/nursery-invoice-app \
  --platform managed \
  --region YOUR_REGION \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --allow-unauthenticated
```

### Option 2: Docker (Home Server/VPS)

```bash
# Build the Docker image
docker build -t nursery-invoice-app .

# Run the container
docker run -d \
  --name nursery-invoice-app \
  -p 5000:8080 \
  -v $(pwd)/credentials.prod.json:/app/credentials.prod.json:ro \
  -e SECRET_KEY="your-secret-key-here" \
  -e GCS_BUCKET_NAME="your-bucket-name" \
  nursery-invoice-app
```

**Note**: The container runs on port 8080 internally, mapped to port 5000 on your host.

### Option 3: Local Installation

```bash
# Install dependencies
pip install -r requirements.txt
cd frontend && npm install && npm run build && cd ..

# Set environment variables
export FLASK_ENV=production
export CLIENT_SECRETS_FILE=credentials.prod.json

# Run the application
python app.py
```

## Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `SECRET_KEY` | Flask session secret key | `fallback_secret_for_dev` | Yes (production) |
| `CLIENT_SECRETS_FILE` | Path to Google OAuth2 credentials | `credentials.prod.json` | Yes |
| `FLASK_ENV` | Environment mode | `development` | No |
| `GCS_BUCKET_NAME` | Google Cloud Storage bucket for invoice data | `invoice-status` | No |
| `CLOUD_RUN_URL` | Your Cloud Run URL (for CORS) | None | No |

### Google Cloud Storage Setup (Optional)

For persistent invoice tracking across deployments:

1. Create a GCS bucket:
   ```bash
   gsutil mb gs://your-invoice-bucket-name
   ```

2. Set the bucket name in your environment or `deploy.sh`:
   ```bash
   export GCS_BUCKET_NAME="your-invoice-bucket-name"
   ```

### Customizing for Your Nursery

### Customizing for Your Nursery

#### 1. Gmail Query Patterns

The most important customization is setting up the Gmail search query in `app.py`. Look for this section around line 194:

```python
# Uncomment and modify this query for your nursery
query = (
    '(from:finance@your-nursery.com '
    'OR from:billing@nursery-software.com) '
    'has:attachment filename:invoice*pdf newer_than:6m'
)
```

**Common query patterns:**
- `from:specific-email@domain.com` - Emails from specific address
- `subject:invoice` - Emails with "invoice" in subject
- `filename:invoice*pdf` - PDF attachments starting with "invoice"
- `newer_than:6m` - Only emails from last 6 months
- `has:attachment` - Only emails with attachments

#### 2. Invoice Amount Detection

If your nursery uses different invoice formats, you may need to customize the amount detection patterns in `app.py`:

```python
# Amount patterns - add your nursery's specific format
amount_patterns = [
    r'Payment Due[:\s]*£?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
    r'(?:total|amount due|balance)[\s:]*£?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
    r'£\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
    r'Amount:\s*\$(\d+\.\d{2})',  # Add patterns for your currency/format
]
```

#### 3. Invoice Number Patterns

Customize how invoice numbers are extracted:

```python
# Invoice number patterns
invoice_patterns = [
    r'(?:invoice\s*(?:no|number)\s*[:#]?\s*)([A-Z0-9-]{4,})',
    r'Invoice\s+ID:\s*([A-Z0-9-]+)',  # Add your nursery's format
]
```

## Security Considerations

- **Credentials**: Never commit your `credentials.prod.json` file to version control
- **OAuth Scopes**: The app only requests Gmail read-only access
- **Data Storage**: Invoice status is stored in Google Cloud Storage (if configured) or local JSON
- **HTTPS**: Always use HTTPS in production for OAuth security

## Troubleshooting

### Common Issues

1. **"No Invoices Found"**:
   - **Most common issue**: Gmail query doesn't match your emails
   - Check the query in `app.py` matches your nursery's email format
   - Verify invoices are PDF attachments (not embedded images)
   - Test with a broader query first: `has:attachment filename:pdf`
   - Use Gmail web interface to test your query manually

2. **"Invalid Grant" OAuth Error**:
   - Check redirect URIs in Google Cloud Console match exactly
   - For local development: `http://localhost:5000/oauth2callback`
   - For production: `https://your-domain.com/oauth2callback`
   - Ensure system clock is synchronized
   - Try re-authorizing: clear browser data and re-authenticate

3. **"Authentication Failed"**:
   - Verify `credentials.prod.json` is in the correct location
   - Check Gmail API is enabled in Google Cloud Console
   - Ensure OAuth consent screen is properly configured
   - For production, publish the OAuth app or add test users

4. **Memory Issues (Cloud Run)**:
   - Increase memory allocation to 2GB in Cloud Run
   - The app automatically limits PDF processing to prevent memory issues
   - Consider excluding very large PDF files

5. **CORS Errors**:
   - Update `CLOUD_RUN_URL` environment variable with your actual URL
   - Check allowed origins in `app.py` include your domain

### Testing Your Setup

1. **Test Gmail Query**:
   - Use Gmail web interface to test your query
   - Go to Gmail → Search → paste your query
   - Verify it returns the expected invoice emails

2. **Test OAuth**:
   - Visit `/debug/session` endpoint to check authentication status
   - Should show `"has_credentials": true` when authenticated

3. **Test Invoice Detection**:
   - Use `/scan_invoices` endpoint to trigger manual scan
   - Check browser developer tools for error messages

### Debug Endpoints

- `/debug/session` - Check authentication and session status
- `/scan_invoices` - Manual trigger for invoice scanning

## Getting Help

### Before Opening an Issue

1. Check that you've configured the Gmail query correctly for your nursery
2. Test your Gmail query in the Gmail web interface first
3. Verify your OAuth credentials are properly set up
4. Check the troubleshooting section above

### When Reporting Issues

Please include:
- Your Gmail query (with sensitive emails redacted)
- Error messages from browser console or server logs
- Whether you're running locally, Docker, or Cloud Run
- Sample invoice format (with personal details removed)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. Areas for improvement:

- Additional nursery provider support and patterns
- Better invoice amount detection for different formats
- Support for additional currencies
- Mobile app development
- Enhanced PDF parsing for complex invoice layouts
- Automated tests for invoice detection patterns

### Development Guidelines

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Test your changes with your own Gmail account
4. Update documentation if adding new features
5. Submit a pull request with clear description of changes

## License

This project is open source and available under the [MIT License](LICENSE).

## Support

If you find this app useful, please consider:
- ⭐ Starring the repository
- 🐛 Reporting bugs via GitHub Issues
- 💡 Suggesting new features
- 🤝 Contributing code improvements

---

**Disclaimer**: This app is designed for personal use to help parents manage childcare payments. Always verify amounts before making payments to your childcare account. The app only reads your Gmail data and does not send any emails or make any payments on your behalf.

**Privacy**: Your Gmail data stays between your browser and Google's servers. The app runs on your own infrastructure and does not send your emails to any third-party services. 
