import os
import tempfile
from contextlib import contextmanager
import easyocr
from PIL import Image
import numpy as np

import fitz  # PyMuPDF


class OCRProcessor:
    """A class to process images and PDFs using Optical Character Recognition (OCR)."""

    def __init__(self):
        """Initialize the OCRProcessor with an EasyOCR reader for English language."""
        self.reader = easyocr.Reader(['en'])

    @contextmanager
    def _temp_image(self, image_data):
        """Context manager for handling temporary image files.

        Args:
            image_data: The image data to be saved as a temporary file.
        """
        temp_file = None
        try:
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
            image_data.save(temp_file.name)
            temp_file.close()
            yield temp_file.name
        finally:
            if temp_file and os.path.exists(temp_file.name):
                try:
                    os.unlink(temp_file.name)
                except Exception:
                    pass

    def process_image(self, image_path):
        """Process a single image using EasyOCR.

        Args:
            image_path (str): The path to the image file.

        Returns:
            str: The extracted text from the image.
        """
        try:
            results = self.reader.readtext(image_path)
            text = "\n".join([result[1] for result in results])
            return text.strip()
        except Exception as e:
            raise Exception(f"Error processing image with OCR: {str(e)}")

    def process_pdf_with_ocr(self, pdf_path):
        """Process a PDF using OCR by converting pages to images.

        Args:
            pdf_path (str): The path to the PDF file.

        Returns:
            str: The extracted text from the PDF.
        """
        doc = None
        try:
            doc = fitz.open(pdf_path)
            text = []

            for page in doc:
                # Get the page as an image
                pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72))
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

                # Process the image with OCR
                with self._temp_image(img) as temp_img_path:
                    results = self.reader.readtext(temp_img_path)
                    page_text = "\n".join([result[1] for result in results])
                    text.append(page_text)

            return "\n\n".join(text).strip()
        except Exception as e:
            raise Exception(f"Error processing PDF with OCR: {str(e)}")
        finally:
            if doc:
                doc.close()