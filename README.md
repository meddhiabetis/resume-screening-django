# Resume Screening System

A sophisticated Django-based resume screening and analysis system that combines vector similarity search with graph-based relationship analysis to provide intelligent resume matching and searching capabilities.

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

- **User Interface**
  - Clean, intuitive dashboard
  - Detailed resume viewing interface
  - Advanced search interface with multiple search modes
  - Real-time feature extraction
  - Debug information for search results

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

## 📋 Prerequisites

- Python 3.9+
- PostgreSQL
- Neo4j Database
- Pinecone API Key
- Tesseract OCR installed on the system

## 🛠️ Installation

1. Clone the repository:
```bash
git clone https://github.com/meddhiabetis/resume-screening-django.git
cd resume-screening-django
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables (.env):
```env
DEBUG=True
SECRET_KEY=your-secret-key
DATABASE_URL=postgres://user:password@localhost:5432/dbname
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
PINECONE_API_KEY=your-pinecone-api-key
PINECONE_ENVIRONMENT=your-pinecone-environment
```

5. Run migrations:
```bash
python manage.py migrate
```

6. Create a superuser:
```bash
python manage.py createsuperuser
```

7. Run the development server:
```bash
python manage.py runserver
```

## 🌐 Usage

1. **Upload Resumes**
   - Navigate to the upload page
   - Select one or multiple PDF resumes
   - System will automatically process and extract information

2. **View Resumes**
   - Access processed resumes from the dashboard
   - View structured information and original text
   - Extract additional features if needed

3. **Search Resumes**
   - Use the search interface to find matching resumes
   - Choose between vector, graph, or hybrid search
   - View detailed match scores and related skills

## 🔍 Search Types

1. **Vector Search**
   - Uses semantic similarity for matching
   - Better for concept-based searching
   - Handles variations in terminology

2. **Graph Search**
   - Uses skill relationships
   - Better for specific skill matching
   - Shows connection between skills

3. **Hybrid Search**
   - Combines both approaches
   - Weighted scoring system
   - Best overall results

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📫 Contact

LinkedIn: [Mohamed Dhia Betis ](https://www.linkedin.com/in/mohamed-dhia-betis/)

Project Link: [https://github.com/meddhiabetis/resume-screening-django](https://github.com/meddhiabetis/resume-screening-django)