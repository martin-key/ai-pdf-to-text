import io
import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.pdf_service import extract_text_from_pdf

class TestPdfService(unittest.TestCase):
    
    @patch('app.services.pdf_service.PdfReader')
    def test_extract_text_from_pdf(self, mock_pdf_reader):
        # Mock the PdfReader and page behavior
        mock_page1 = MagicMock()
        mock_page1.extract_text.return_value = "This is page 1 content."
        
        mock_page2 = MagicMock()
        mock_page2.extract_text.return_value = "This is page 2 content."
        
        mock_pdf_reader.return_value.pages = [mock_page1, mock_page2]
        
        # Create test PDF content
        test_content = b"dummy PDF content"
        
        # Call the function
        result = extract_text_from_pdf(test_content)
        
        # Assertions
        self.assertIn("Page 1", result)
        self.assertIn("This is page 1 content.", result)
        self.assertIn("Page 2", result)
        self.assertIn("This is page 2 content.", result)
        
        # Verify PdfReader was called with BytesIO object
        args, _ = mock_pdf_reader.call_args
        self.assertIsInstance(args[0], io.BytesIO)
    
    @patch('app.services.pdf_service.PdfReader')
    def test_extract_text_from_pdf_empty(self, mock_pdf_reader):
        # Mock the PdfReader and page behavior
        mock_page = MagicMock()
        mock_page.extract_text.return_value = ""
        
        mock_pdf_reader.return_value.pages = [mock_page]
        
        # Create test PDF content
        test_content = b"dummy PDF content"
        
        # Call the function
        result = extract_text_from_pdf(test_content)
        
        # Assertions
        self.assertIn("No extractable text found", result)
    
    @patch('app.services.pdf_service.PdfReader')
    def test_extract_text_from_pdf_exception(self, mock_pdf_reader):
        # Mock PdfReader to raise an exception
        mock_pdf_reader.side_effect = Exception("PDF read error")
        
        # Create test PDF content
        test_content = b"dummy PDF content"
        
        # Assertions
        with self.assertRaises(Exception) as context:
            extract_text_from_pdf(test_content)
        
        self.assertIn("Failed to extract text from PDF", str(context.exception))

if __name__ == '__main__':
    unittest.main() 