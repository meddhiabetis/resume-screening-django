import os
import re
import pdfplumber

def clean_resume(text):
    # Remove URLs
    text = re.sub(r'http\S+', '', text)
    # Remove special characters and symbols
    text = re.sub(r'[^\w\s]', '', text)
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def extract_text_from_pdf(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text()
    return clean_resume(text)

def process_uploaded_resumes(resumes_directory):
    extracted_texts = []
    file_names = []
    for filename in os.listdir(resumes_directory):
        if filename.endswith('.pdf'):
            pdf_path = os.path.join(resumes_directory, filename)
            text = extract_text_from_pdf(pdf_path)
            extracted_texts.append(text)
            file_names.append(filename)
    return extracted_texts, file_names
