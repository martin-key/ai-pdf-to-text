from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Request, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
import logging
import os
from enum import Enum
from dotenv import load_dotenv

from app.services.pdf_service import extract_text_from_pdf
from app.services.ollama_service import get_text_from_ollama, extract_text_from_pdf_with_vision

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="PDF to Text API",
    description="API for extracting text from PDF documents using Gemma 3-4b model",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Mount static files directory
app.mount("/static", StaticFiles(directory="app/static"), name="static")

class ExtractionMethod(str, Enum):
    TEXT = "text"
    VISION = "vision"

@app.get("/", response_class=HTMLResponse)
async def root():
    """
    Serve the HTML upload form.
    """
    return FileResponse("app/static/index.html")

@app.post("/extract-text")
async def extract_text(
    request: Request,
    file: UploadFile = File(None), 
    method: ExtractionMethod = Query(ExtractionMethod.VISION, description="Text extraction method: text (PyPDF2) or vision (Gemma 3 multimodal)"),
    processPerPage: bool = Query(True, description="Whether to process each page individually (vision method only)")
):
    """
    Extract text from a PDF document using Gemma 3-4b model.
    
    Supports two upload methods:
    1. Multipart form data with 'file' field
    2. Direct binary upload with Content-Type: application/pdf
    
    Parameters:
    - file: The PDF file to extract text from (when using form-data)
    - method: Text extraction method (text or vision)
    - processPerPage: Whether to process each page individually (vision method only)
    
    Returns:
    - A JSON object with the filename, extracted text, and processing method
    """
    # Override environment variable with query parameter
    if method == ExtractionMethod.VISION:
        os.environ["PROCESS_PER_PAGE"] = str(processPerPage).lower()
    
    try:
        # Check content type for direct binary upload
        content_type = request.headers.get("content-type", "")
        
        if file is None and content_type.lower() == "application/pdf":
            # Handle direct binary upload
            logger.info(f"Received direct binary PDF upload with Content-Type: {content_type}")
            
            # Read binary content
            content = await request.body()
            filename = request.headers.get("file-name", "document.pdf")
            
            if not content:
                raise HTTPException(status_code=400, detail="Empty PDF content")
        
        elif file is not None:
            # Handle multipart form upload
            logger.info(f"Received PDF file upload via form: {file.filename}")
            
            # Validate file
            if not file.filename.endswith('.pdf'):
                raise HTTPException(status_code=400, detail="Only PDF files are supported")
            
            # Read file content
            content = await file.read()
            filename = file.filename
        
        else:
            # No file provided
            raise HTTPException(
                status_code=400, 
                detail="No PDF file provided. Upload a file using multipart/form-data with 'file' field or send raw PDF with Content-Type: application/pdf"
            )
        
        # Extract text based on the selected method
        if method == ExtractionMethod.TEXT:
            # Use PyPDF2 to extract text and then Ollama to clean it
            pdf_text = extract_text_from_pdf(content)
            processed_text = get_text_from_ollama(pdf_text)
        else:
            # Use Gemma 3's multimodal capabilities to extract text directly from PDF
            processed_text = extract_text_from_pdf_with_vision(content)
        
        return {
            "filename": filename, 
            "text": processed_text, 
            "method": method,
            "processPerPage": processPerPage if method == ExtractionMethod.VISION else None
        }
    
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")
    
    finally:
        if file:
            await file.close()

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    uvicorn.run("app.main:app", host=host, port=port, reload=True) 