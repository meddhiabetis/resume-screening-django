# Resume Screening System

A sophisticated Django-based resume screening and analysis system that combines vector similarity search with graph-based relationship analysis to provide intelligent resume matching and searching capabilities. Now supports automatic Gmail resume importing using Google OAuth.

---

## 🌟 Features

- Intelligent Resume Processing
  - Automatic text extraction from PDF/DOC/DOCX
  - OCR fallback for scanned documents
  - Structured information extraction (skills, experience, education, etc.)
- Advanced Search Capabilities
  - Vector-based semantic search using Pinecone
  - Graph-based relationship search using Neo4j
  - Hybrid search combining both approaches
  - Skills-based matching and scoring
- Gmail Resume Fetch
  - Secure OAuth2 Gmail integration
  - One-click and scheduled fetching of new resumes from Gmail attachments
- User Interface
  - Clean, intuitive dashboard
  - Detailed resume viewing interface
  - Advanced search interface with multiple search modes
  - Real-time feature extraction
  - Debug information for search results

---

## 🚀 Technology Stack

- Backend Framework: Django 4.2+
- Databases:
  - PostgreSQL (Primary)
  - Pinecone (Vector)
  - Neo4j (Graph)
- Text Processing: NLTK, spaCy, scikit-learn, Sentence Transformers
- File Processing: pdfminer.six, PyMuPDF, Tesseract OCR, pdf2image, python-docx, easyocr
- Async: Celery + Redis (Memurai on Windows)

---

## 📋 Prerequisites

- Python 3.9+ (3.13 works too)
- PostgreSQL
- Neo4j
- Pinecone API Key
- Redis (Memurai on Windows)
- Tesseract OCR installed on the system
- Poppler installed (for pdf2image)
- Google Cloud Project with Gmail API enabled

---

## 🧰 System Dependencies

- Tesseract OCR
  - Windows: Install from the UB-Mannheim build and note the install path (e.g., `C:\Program Files\Tesseract-OCR\tesseract.exe`)
  - macOS: `brew install tesseract`
  - Ubuntu/Debian: `sudo apt-get install tesseract-ocr`
- Poppler (for pdf2image)
  - Windows: Install Poppler for Windows and add `...\poppler\bin` to PATH
  - macOS: `brew install poppler`
  - Ubuntu/Debian: `sudo apt-get install poppler-utils`
- Redis
  - Windows: Install Memurai and start the service
  - macOS (Homebrew): `brew install redis && brew services start redis`
  - Ubuntu/Debian: `sudo apt-get install redis-server && sudo systemctl enable --now redis-server`

Optional (Windows): If `python-magic` gives errors, use `python-magic-bin` instead.

---

## 🛠️ Installation

### 1) Clone the repository

```bash
git clone https://github.com/meddhiabetis/resume-screening-django.git
cd resume-screening-django
```

### 2) Create and activate a virtual environment

```bash
python -m venv venv
# On Windows (PowerShell)
.\venv\Scripts\Activate.ps1
# On macOS/Linux
source venv/bin/activate
```

### 3) Install Python dependencies

```bash
pip install -r requirements.txt
```

Notes:
- If you previously had `pinecone-client` installed, uninstall it: `pip uninstall -y pinecone-client`
- Ensure `python-docx` (not `docx`) and `PyMuPDF` are installed.

### 4) Set up PostgreSQL

Create a database and user (replace names if you prefer):

Option A: Using SQL (psql or pgAdmin Query Tool)
```sql
-- Run as postgres superuser
CREATE USER resume_user WITH PASSWORD 'resume_password';
CREATE DATABASE resume_db OWNER resume_user;

-- Ensure permissions on public schema
GRANT ALL ON SCHEMA public TO resume_user;
GRANT ALL PRIVILEGES ON DATABASE resume_db TO resume_user;
```

Option B: Create via pgAdmin UI (then grant privileges as above).

Default port: 5432.

### 5) Create credentials folder and add Google OAuth JSON

- Create `credentials/` at the project root.
- Place your `google_oauth.json` inside:
  - `resume-screening-django/credentials/google_oauth.json`
- Make sure it’s in `.gitignore` (avoid committing secrets).

### 6) Create a `.env` file

Create a `.env` file at the project root with:

```env
# Core
DEBUG=True
SECRET_KEY=your-secret-key

# Database (Option A: single URL)
DATABASE_URL=postgres://resume_user:resume_password@localhost:5432/resume_db
# Database (Option B: discrete settings—uncomment if your settings support these)
# DB_NAME=resume_db
# DB_USER=resume_user
# DB_PASSWORD=resume_password
# DB_HOST=localhost
# DB_PORT=5432

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# Pinecone
PINECONE_API_KEY=your-pinecone-api-key
# If your code uses it, keep environment/region variable as well
PINECONE_ENVIRONMENT=your-pinecone-environment-or-region

# Gmail OAuth
GOOGLE_OAUTH_CLIENT_SECRETS=credentials/google_oauth.json
GOOGLE_OAUTH_SCOPES=openid,https://www.googleapis.com/auth/userinfo.profile,https://www.googleapis.com/auth/userinfo.email,https://www.googleapis.com/auth/gmail.readonly
GOOGLE_OAUTH_REDIRECT_URI=http://localhost:8000/accounts/gmail/callback/

# Only for local development (HTTP callback)
OAUTHLIB_INSECURE_TRANSPORT=1

# Redis
REDIS_URL=redis://localhost:6379/0

# OCR (set if pytesseract can't find tesseract automatically)
# TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
```

### 7) Run database migrations

```bash
python manage.py migrate
```

If you see a permission error on `public` schema, grant privileges as shown in Step 4.

### 8) Create a superuser

```bash
python manage.py createsuperuser
```

### 9) Start Celery worker

Windows (use solo pool):
```powershell
# OAUTH only needed for local HTTP callbacks
# It's already in .env and loaded by settings; if needed you can also export here.
$env:OAUTHLIB_INSECURE_TRANSPORT=1
python -m celery -A core worker --loglevel=info --concurrency=1 --pool=solo
```

macOS/Linux:
```bash
export OAUTHLIB_INSECURE_TRANSPORT=1
celery -A core worker --loglevel=info
```

### 10) Run the Django development server

```bash
python manage.py runserver
```

Visit http://127.0.0.1:8000

---

## 📧 Gmail Integration

1) Google Cloud Console setup
- Enable Gmail API.
- Create OAuth client (Web Application).
- Add redirect URI: `http://localhost:8000/accounts/gmail/callback/`
- Download credentials JSON and place it at `credentials/google_oauth.json`.

2) In the app
- Log in to the Django app.
- Go to “Connect Gmail” (route like `/accounts/gmail/connect/`).
- Complete Google login and grant permissions.
- After connecting, you can fetch resumes from Gmail.

Note: For local development over HTTP, `OAUTHLIB_INSECURE_TRANSPORT=1` must be set (as in `.env`).

---

## 🌐 Usage

- Upload Resumes: Use the dashboard to upload PDF/DOC/DOCX; system extracts text and metadata automatically.
- Gmail Resume Import: Connect Gmail, fetch manually or via scheduled Celery tasks.
- View Resumes: See processed resumes, extracted entities, and original text.
- Search: Run vector, graph, or hybrid searches with detailed scoring.

---

## 🔧 Troubleshooting

- Pinecone package error:
  - Error mentions `pinecone-client` rename: Uninstall old package:
    ```bash
    pip uninstall -y pinecone-client
    pip install pinecone
    ```
- `ModuleNotFoundError: No module named 'docx'`:
  - Install the correct package: `pip install python-docx`
- `ModuleNotFoundError: No module named 'fitz'`:
  - Install PyMuPDF: `pip install PyMuPDF`
- Postgres permission error on `public` schema:
  - Grant privileges as postgres superuser:
    ```sql
    GRANT ALL ON SCHEMA public TO resume_user;
    GRANT ALL PRIVILEGES ON DATABASE resume_db TO resume_user;
    ```
- Google OAuth “insecure transport” in dev:
  - Ensure `.env` includes `OAUTHLIB_INSECURE_TRANSPORT=1`
- Credentials file not found:
  - Ensure `credentials/google_oauth.json` exists and path matches `.env`
- pdf2image errors on Windows:
  - Install Poppler and add its `bin` directory to PATH
- python-magic errors on Windows:
  - Try `pip install python-magic-bin` (or ensure libmagic is available)

---

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch: `git checkout -b feature/AmazingFeature`
3. Commit your changes: `git commit -m 'feat: Add AmazingFeature'`
4. Push to the branch: `git push origin feature/AmazingFeature`
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 📫 Contact

- LinkedIn: [Mohamed Dhia Betis](https://www.linkedin.com/in/mohamed-dhia-betis/)
- Project Link: [resume-screening-django](https://github.com/meddhiabetis/resume-screening-django)