import PyPDF2
import docx
import io

class TextExtractor:
    def extract(self, file_obj, filename):
        """
        Extract text from PDF or DOCX files
        """
        file_extension = filename.lower().split('.')[-1]
        
        if file_extension == 'pdf':
            return self._extract_from_pdf(file_obj)
        elif file_extension in ['doc', 'docx']:
            return self._extract_from_docx(file_obj)
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")

    def _extract_from_pdf(self, file_obj):
        """
        Extract text from PDF files
        """
        try:
            pdf_reader = PyPDF2.PdfReader(file_obj)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            return text.strip()
        except Exception as e:
            raise Exception(f"Error extracting text from PDF: {str(e)}")

    def _extract_from_docx(self, file_obj):
        """
        Extract text from DOCX files
        """
        try:
            doc = docx.Document(file_obj)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text.strip()
        except Exception as e:
            raise Exception(f"Error extracting text from DOCX: {str(e)}")