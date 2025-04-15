import io
import logging
from typing import Union, Dict
from PyPDF2 import PdfReader

logger = logging.getLogger(__name__)

def extract_text_from_pdf(content: Union[bytes, io.BytesIO]) -> str:
    """
    Extract text from a PDF document.
    
    Args:
        content: PDF content as bytes or BytesIO object
        
    Returns:
        Extracted text from the PDF
    """
    logger.info("Extracting text from PDF")
    
    try:
        # If content is bytes, convert to BytesIO
        if isinstance(content, bytes):
            content = io.BytesIO(content)
        
        # Create a PDF reader object
        pdf_reader = PdfReader(content)
        
        # Extract text from all pages
        text = ""
        for page_num, page in enumerate(pdf_reader.pages):
            page_text = page.extract_text()
            if page_text:
                text += f"\n--- Page {page_num + 1} ---\n"
                text += page_text
        
        if not text.strip():
            logger.warning("No text extracted from PDF. The PDF might be scanned or contain images only.")
            return "No extractable text found in the PDF. The document might be scanned or contain images only."
        
        logger.info(f"Successfully extracted {len(text)} characters from PDF")
        return text
    
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {str(e)}")
        raise Exception(f"Failed to extract text from PDF: {str(e)}") 