# Resume Screening System

A sophisticated Django-based resume screening and analysis system that combines vector similarity search with graph-based relationship analysis to provide intelligent resume matching and searching capabilities. Now supports **automatic Gmail resume importing** using Google OAuth.

---

## 🌟 Features

- **Intelligent Resume Processing**
  - Automatic text extraction from PDF documents
  - OCR fallback for scanned documents
  - Structured information extraction (skills, experience, education, etc.)
- **Advanced Search Capabilities**
  - Vector-based semantic search using Pinecone
  - Graph-based relationship search using Neo4j
  - Hybrid search combining both approaches
  - Skills-based matching and scoring
- **Gmail Resume Fetch**
  - Secure OAuth2 Gmail integration
  - One-click and scheduled fetching of new resumes from Gmail attachments
- **User Interface**
  - Clean, intuitive dashboard
  - Detailed resume viewing interface
  - Advanced search interface with multiple search modes
  - Real-time feature extraction
  - Debug information for search results

---

## 🚀 Technology Stack

- **Backend Framework**: Django 4.2+
- **Databases**:
  - PostgreSQL (Primary Database)
  - Pinecone (Vector Database)
  - Neo4j (Graph Database)
- **Text Processing**:
  - NLTK
  - Spacy
  - Sentence Transformers
- **File Processing**:
  - pdfminer.six
  - Tesseract OCR
  - pdf2image
- **Mail Integration**:
  - Google OAuth 2.0 (Gmail API)
  - Celery (Scheduled fetching)

---

## 📋 Prerequisites

- Python 3.9+
- PostgreSQL
- Neo4j Database
- Pinecone API Key
- Tesseract OCR installed on the system
- **Redis** (for Celery background tasks)
- **Google Cloud Project** with Gmail API enabled

---

## 🛠️ Installation

### 1. Clone the repository

```bash
git clone https://github.com/meddhiabetis/resume-screening-django.git
cd resume-screening-django
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv
# On Unix/Mac:
source venv/bin/activate
# On Windows:
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up environment variables (`.env`)

Create a `.env` file in the project root with these variables:

```env
DEBUG=True
SECRET_KEY=your-secret-key
DATABASE_URL=postgres://user:password@localhost:5432/dbname
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
PINECONE_API_KEY=your-pinecone-api-key
PINECONE_ENVIRONMENT=your-pinecone-environment
GOOGLE_OAUTH_CLIENT_SECRETS=/absolute/path/to/your/google_oauth_client_secrets.json
GOOGLE_OAUTH_SCOPES=openid,https://www.googleapis.com/auth/userinfo.profile,https://www.googleapis.com/auth/userinfo.email,https://www.googleapis.com/auth/gmail.readonly
GOOGLE_OAUTH_REDIRECT_URI=http://localhost:8000/accounts/gmail/callback/
REDIS_URL=redis://localhost:6379/0
```

> **Tip:** In production, set `DEBUG=False` and use `https` in your redirect URI and site URLs.

---

### 5. Database migrations

```bash
python manage.py migrate
```

### 6. Create a superuser

```bash
python manage.py createsuperuser
```

### 7. Install & Run Redis (for Celery)

#### On Ubuntu:

```bash
sudo apt update
sudo apt install redis-server
sudo systemctl enable redis-server
sudo systemctl start redis-server
```

#### On Mac (with Homebrew):

```bash
brew install redis
brew services start redis
```

#### On Windows:

- Download and install from [Memurai](https://www.memurai.com/) or [Microsoft archive](https://github.com/microsoftarchive/redis/releases).
- Start the Redis service.

---

### 8. Start Celery worker

#### Windows (use solo pool):

```bash
$env:OAUTHLIB_INSECURE_TRANSPORT=1  # PowerShell, only for development!
python -m celery -A core worker --loglevel=info --concurrency=1 --pool=solo
```

#### Mac/Linux:

```bash
export OAUTHLIB_INSECURE_TRANSPORT=1  # Only for development!
celery -A core worker --loglevel=info
```

> **Important:** Only use `OAUTHLIB_INSECURE_TRANSPORT=1` for local development. In production, always use HTTPS for OAuth callbacks.

---

### 9. Run the Django development server

```bash
python manage.py runserver
```

---

## 📧 Gmail Integration Setup

### 1. Get Google OAuth Credentials

To use Gmail features, you need to set up a Google OAuth application.

**Steps:**

1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project or select your project.
3. **Enable the Gmail API** for your project.
4. Go to **APIs & Services > Credentials**.
5. Click **Create Credentials** > **OAuth client ID**.
6. Choose **Web application**.  
   - Authorized redirect URI:  
     - For development: `http://localhost:8000/accounts/gmail/callback/`
     - For production: use your live `https://yourdomain.com/accounts/gmail/callback/`
7. Download the credentials JSON file.
8. Place the JSON file somewhere safe, and set its absolute path in your `.env` as `GOOGLE_OAUTH_CLIENT_SECRETS`.
9. Make sure your OAuth consent screen is configured and published.
10. Required Scopes (add these to your credentials or `.env`):
    - openid
    - https://www.googleapis.com/auth/userinfo.profile
    - https://www.googleapis.com/auth/userinfo.email
    - https://www.googleapis.com/auth/gmail.readonly

---

### 2. Connect Gmail in the App

- Log in as a user.
- On the dashboard or profile, click **"Connect Gmail"**.
- Complete the Google authentication flow.
- Once connected, you can:
  - **Fetch resumes from your Gmail inbox** (manual and automatic).
  - Disconnect Gmail at any time.

---

## 🌐 Usage

1. **Upload Resumes**
   - Go to the dashboard, click "Upload Resumes"
   - Drag/drop or select PDF, DOC, or DOCX files
   - System processes and extracts info automatically

2. **Gmail Resume Import**
   - Connect your Gmail account
   - Fetch resumes manually or let Celery auto-fetch new attachments

3. **View Resumes**
   - Access processed resumes from the dashboard
   - View structured info and original text

4. **Search Resumes**
   - Use the search interface for vector, graph, or hybrid search
   - View detailed match scores and related skills

---

## 🔍 Search Types

1. **Vector Search**
   - Uses semantic similarity for matching
   - Great for concept-based searching

2. **Graph Search**
   - Uses skill relationships and graph analysis
   - Great for specific skill matching

3. **Hybrid Search**
   - Combines both approaches for best results

---

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 📫 Contact

- LinkedIn: [Mohamed Dhia Betis ](https://www.linkedin.com/in/mohamed-dhia-betis/)
- Project Link: [https://github.com/meddhiabetis/resume-screening-django](https://github.com/meddhiabetis/resume-screening-django)