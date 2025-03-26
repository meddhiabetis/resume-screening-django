import fitz  # PyMuPDF
import docx
import io
import os
from .ocr_processor import OCRProcessor
import tempfile
from contextlib import contextmanager

class TextExtractor:
    def __init__(self):
        self.ocr_processor = OCRProcessor()

    @contextmanager
    def _temp_file(self, file_obj, suffix):
        """Context manager for handling temporary files"""
        temp_file = None
        try:
            # Create temporary file
            file_obj.seek(0)
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            temp_file.write(file_obj.read())
            temp_file.close()
            yield temp_file.name
        finally:
            # Clean up
            if temp_file and os.path.exists(temp_file.name):
                try:
                    os.unlink(temp_file.name)
                except Exception:
                    pass

    def extract(self, file_obj, filename):
        """Extract text from PDF, DOCX, or image files"""
        file_extension = filename.lower().split('.')[-1]
        
        if file_extension == 'pdf':
            return self._extract_from_pdf(file_obj)
        elif file_extension in ['doc', 'docx']:
            return self._extract_from_docx(file_obj)
        elif file_extension in ['jpg', 'jpeg', 'png', 'tiff', 'bmp']:
            return self._extract_from_image(file_obj)
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")

    def _extract_from_pdf(self, file_obj):
        """Extract text from PDF files with OCR fallback"""
        with self._temp_file(file_obj, '.pdf') as temp_path:
            try:
                # Try normal PDF text extraction first
                doc = None
                try:
                    doc = fitz.open(temp_path)
                    text = ""
                    for page in doc:
                        text += page.get_text() + "\n"
                finally:
                    if doc:
                        doc.close()

                # If extracted text is too short or empty, fall back to OCR
                if not text or len(text.strip()) < 100:
                    text = self.ocr_processor.process_pdf_with_ocr(temp_path)

                return text.strip()
            except Exception as e:
                raise Exception(f"Error extracting text from PDF: {str(e)}")

    def _extract_from_docx(self, file_obj):
        """Extract text from DOCX files"""
        try:
            doc = docx.Document(file_obj)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text.strip()
        except Exception as e:
            raise Exception(f"Error extracting text from DOCX: {str(e)}")

    def _extract_from_image(self, file_obj):
        """Extract text from image files using OCR"""
        with self._temp_file(file_obj, '.png') as temp_path:
            try:
                return self.ocr_processor.process_image(temp_path)
            except Exception as e:
                raise Exception(f"Error extracting text from image: {str(e)}")