import os
import base64
import logging
import requests
import tempfile
import io
import time
import sys
from typing import Dict, Any, List, Optional, Tuple
from dotenv import load_dotenv
from pdf2image import convert_from_bytes

# Load environment variables
load_dotenv()

# Configure logging with more details
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Get Ollama server URL from environment variables or use default
OLLAMA_SERVER_URL = os.getenv("OLLAMA_SERVER_URL", "http://192.168.10.226:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:4b")
MAX_PAGES = int(os.getenv("MAX_PAGES", "10"))  # Maximum number of pages to process
PROCESS_PER_PAGE = os.getenv("PROCESS_PER_PAGE", "true").lower() in ("true", "yes", "1")  # Process each page separately
PAGE_TIMEOUT = int(os.getenv("PAGE_TIMEOUT", "90"))  # Timeout for each page in seconds
RETRY_COUNT = int(os.getenv("RETRY_COUNT", "2"))  # Number of retries for failed requests
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() in ("true", "yes", "1")  # Enable extra debug logging

def debug_log(message):
    """Helper function for debug logging"""
    if DEBUG_MODE:
        logger.info(f"DEBUG: {message}")
    else:
        logger.debug(message)

def get_text_from_ollama(pdf_text: str) -> str:
    """
    Legacy method for text-only processing with Ollama.
    
    Args:
        pdf_text: Text extracted from the PDF
        
    Returns:
        Processed text from Ollama
    """
    logger.info(f"Sending text to Ollama model {OLLAMA_MODEL}")
    
    # Craft the prompt for Ollama
    prompt = f"""
    I have the following text extracted from a PDF document. 
    Please format it properly, fix any extraction errors, and provide the cleaned text:

    {pdf_text}
    
    Respond only with the cleaned text, no additional commentary or explanations.
    """
    
    # Prepare the payload for Ollama API
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "temperature": 0.1,  # Low temperature for more deterministic output
    }
    
    try:
        # Make a POST request to Ollama API
        response = requests.post(
            f"{OLLAMA_SERVER_URL}/api/generate",
            json=payload,
            timeout=60  # 60 seconds timeout
        )
        
        # Check if the request was successful
        response.raise_for_status()
        
        # Parse the JSON response
        result = response.json()
        
        # Extract the response text
        processed_text = result.get("response", "")
        
        logger.info(f"Received response from Ollama ({len(processed_text)} characters)")
        return processed_text
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Error communicating with Ollama server: {str(e)}")
        raise Exception(f"Failed to communicate with Ollama server: {str(e)}")
    
    except Exception as e:
        logger.error(f"Unexpected error while processing text with Ollama: {str(e)}")
        raise Exception(f"Unexpected error while processing text with Ollama: {str(e)}")

def convert_pdf_to_images(pdf_content: bytes, max_pages: int = MAX_PAGES) -> List[Tuple[int, bytes]]:
    """
    Convert PDF content to a list of images.
    
    Args:
        pdf_content: PDF file content as bytes
        max_pages: Maximum number of pages to convert
        
    Returns:
        List of tuples containing (page_number, image_bytes)
    """
    logger.info(f"Converting PDF to images (max {max_pages} pages)")
    
    try:
        # Convert PDF pages to images
        t_start = time.time()
        images = convert_from_bytes(
            pdf_content,
            dpi=200,  # Higher DPI for better quality
            fmt='JPEG',
            first_page=1,
            last_page=max_pages
        )
        t_convert = time.time()
        
        total_pages = len(images)
        logger.info(f"PDF contains {total_pages} pages (limited to {max_pages}) - Converted in {t_convert-t_start:.2f}s")
        
        # Convert images to bytes
        image_bytes_list = []
        for i, img in enumerate(images):
            page_start = time.time()
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='JPEG', quality=85)
            img_bytes = img_byte_arr.getvalue()
            image_size = len(img_bytes) / 1024  # Size in KB
            image_bytes_list.append((i+1, img_bytes))
            page_end = time.time()
            logger.info(f"Converted page {i+1}/{total_pages} to image ({image_size:.1f} KB) in {page_end-page_start:.2f}s")
        
        logger.info(f"Successfully converted all {total_pages} pages to images")
        return image_bytes_list
    
    except Exception as e:
        logger.error(f"Error converting PDF to images: {str(e)}")
        raise Exception(f"Failed to convert PDF to images: {str(e)}")

def process_image_with_ollama(image_bytes: bytes, page_num: int, total_pages: int, retry_count: int = RETRY_COUNT) -> str:
    """
    Process a single image with Ollama's vision capabilities.
    
    Args:
        image_bytes: Image content as bytes
        page_num: Page number for logging
        total_pages: Total number of pages (for logging)
        retry_count: Number of retries for failed requests
        
    Returns:
        Extracted text from the image
    """
    logger.info(f"STARTING PAGE {page_num}/{total_pages} PROCESSING")
    image_size = len(image_bytes) / 1024  # Size in KB
    logger.info(f"Image size for page {page_num}: {image_size:.1f} KB")
    
    # Calculate a dynamic timeout based on image size
    dynamic_timeout = min(max(int(image_size / 10), PAGE_TIMEOUT), 180)  # Between PAGE_TIMEOUT and 180 seconds
    
    for attempt in range(retry_count + 1):
        try:
            start_time = time.time()
            
            # Encode image to base64
            debug_log(f"Starting base64 encoding for page {page_num}")
            base64_image = base64.b64encode(image_bytes).decode('utf-8')
            encode_time = time.time() - start_time
            logger.info(f"Base64 encoding for page {page_num} completed in {encode_time:.2f}s")
            
            # Create a chat message with image
            messages = [
                {
                    "role": "user",
                    "content": f"Extract all the text from this PDF page (page {page_num} of {total_pages}). Format it properly and fix any extraction errors. Return only the text content, no additional commentary.",
                    "images": [base64_image]
                }
            ]
            
            # Prepare the payload for Ollama API
            payload = {
                "model": OLLAMA_MODEL,
                "messages": messages,
                "stream": False,
                "temperature": 0.1  # Low temperature for more deterministic output
            }
            
            logger.info(f"Sending page {page_num}/{total_pages} to Ollama (timeout: {dynamic_timeout}s, attempt: {attempt+1}/{retry_count+1})")
            
            # Make a POST request to Ollama API
            api_start = time.time()
            response = requests.post(
                f"{OLLAMA_SERVER_URL}/api/chat",
                json=payload,
                timeout=dynamic_timeout
            )
            
            # Check if the request was successful
            response.raise_for_status()
            api_time = time.time() - api_start
            logger.info(f"API call for page {page_num} completed in {api_time:.2f}s")
            
            # Parse the JSON response
            debug_log(f"Parsing API response for page {page_num}")
            result = response.json()
            
            # Extract the response text
            if "message" in result:
                extracted_text = result["message"]["content"]
            else:
                logger.warning(f"No 'message' field in API response for page {page_num}")
                extracted_text = f"No text could be extracted from page {page_num}."
            
            process_time = time.time() - start_time
            logger.info(f"COMPLETED PAGE {page_num}/{total_pages} in {process_time:.2f}s ({len(extracted_text)} characters)")
            return extracted_text
            
        except requests.exceptions.Timeout:
            if attempt < retry_count:
                wait_time = (attempt + 1) * 5  # Progressive backoff
                logger.warning(f"Timeout processing page {page_num}/{total_pages} (attempt {attempt+1}/{retry_count+1}). Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                logger.error(f"Timeout processing page {page_num}/{total_pages} after {retry_count+1} attempts")
                return f"[Error processing page {page_num}: Request timed out after {retry_count+1} attempts]"
        
        except requests.exceptions.RequestException as e:
            if attempt < retry_count:
                wait_time = (attempt + 1) * 5  # Progressive backoff
                logger.warning(f"Error processing page {page_num}/{total_pages} (attempt {attempt+1}/{retry_count+1}): {str(e)}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                logger.error(f"Error communicating with Ollama for page {page_num}/{total_pages}: {str(e)}")
                return f"[Error processing page {page_num}: Failed to communicate with Ollama server]"
        
        except Exception as e:
            logger.error(f"Unexpected error processing page {page_num}/{total_pages}: {str(e)}")
            return f"[Error processing page {page_num}: {str(e)}]"

def extract_text_from_pdf_with_vision(pdf_content: bytes) -> str:
    """
    Extract text from PDF using Gemma 3's multimodal capabilities.
    
    Args:
        pdf_content: PDF file content as bytes
        
    Returns:
        Extracted text from the PDF
    """
    start_time = time.time()
    logger.info(f"*** STARTING PDF TEXT EXTRACTION USING {OLLAMA_MODEL} ***")
    logger.info(f"Processing configuration: PROCESS_PER_PAGE={PROCESS_PER_PAGE}, MAX_PAGES={MAX_PAGES}, MODEL={OLLAMA_MODEL}")
    
    try:
        # Convert PDF pages to images
        image_data_list = convert_pdf_to_images(pdf_content)
        
        if not image_data_list:
            logger.warning("No images could be extracted from the PDF")
            return "No images could be extracted from the PDF."
        
        total_pages = len(image_data_list)
        conversion_time = time.time() - start_time
        logger.info(f"PDF conversion to images completed in {conversion_time:.2f}s for {total_pages} pages")
        
        # Process based on the configuration
        if PROCESS_PER_PAGE:
            # Process each page individually
            all_pages_text = []
            
            logger.info(f"*** BEGINNING PAGE-BY-PAGE PROCESSING FOR {total_pages} PAGES ***")
            
            for idx, (page_num, image_bytes) in enumerate(image_data_list):
                logger.info(f"*** PROCESSING PAGE {page_num}/{total_pages} (index {idx}) ***")
                page_start_time = time.time()
                
                try:
                    page_text = process_image_with_ollama(image_bytes, page_num, total_pages)
                    page_process_time = time.time() - page_start_time
                    
                    all_pages_text.append(f"\n--- Page {page_num} ---\n{page_text}")
                    logger.info(f"*** FINISHED PAGE {page_num}/{total_pages} in {page_process_time:.2f}s ***")
                except Exception as e:
                    error_msg = f"Error processing page {page_num}: {str(e)}"
                    logger.error(error_msg)
                    all_pages_text.append(f"\n--- Page {page_num} ---\n[{error_msg}]")
                
                # Log progress
                logger.info(f"Progress: {idx+1}/{total_pages} pages processed ({((idx+1)/total_pages)*100:.1f}%)")
                
                # Brief pause between pages to let GPU cool down if needed
                if idx < total_pages - 1:
                    debug_log(f"Pausing briefly before processing next page")
                    time.sleep(1)
            
            # Concatenate all pages
            logger.info(f"All {total_pages} pages processed, concatenating results")
            full_text = "\n".join(all_pages_text)
            
            total_time = time.time() - start_time
            logger.info(f"*** PDF PROCESSING COMPLETED: {total_pages} pages in {total_time:.2f}s ***")
            return full_text
        else:
            # Original implementation: Process all pages at once
            batch_start_time = time.time()
            logger.info(f"Starting batch processing for {total_pages} pages")
            
            # Separate images and page numbers
            page_numbers = [page_num for page_num, _ in image_data_list]
            image_bytes_list = [img_bytes for _, img_bytes in image_data_list]
            
            # Calculate total image size
            total_image_size = sum(len(img) for img in image_bytes_list) / 1024  # Size in KB
            logger.info(f"Total image data size: {total_image_size:.1f} KB for {total_pages} pages")
            
            # Encode images to base64
            encoding_start = time.time()
            base64_images = [base64.b64encode(img).decode('utf-8') for img in image_bytes_list]
            encoding_time = time.time() - encoding_start
            logger.info(f"Base64 encoding completed in {encoding_time:.2f}s")
            
            # Create a chat message with images
            messages = [
                {
                    "role": "user",
                    "content": f"Extract all the text from these {total_pages} PDF pages. Format it properly and fix any extraction errors. Return only the text content, no additional commentary.",
                    "images": base64_images
                }
            ]
            
            # Prepare the payload for Ollama API
            payload = {
                "model": OLLAMA_MODEL,
                "messages": messages,
                "stream": False,
                "temperature": 0.1  # Low temperature for more deterministic output
            }
            
            # Calculate a dynamic timeout based on the number of pages and total image size
            dynamic_timeout = min(max(total_pages * 30, 120), 600)  # Between 120s and 10min
            
            logger.info(f"Sending {total_pages} page images to Ollama model {OLLAMA_MODEL} (timeout: {dynamic_timeout}s)")
            
            # Make a POST request to Ollama API
            api_start_time = time.time()
            response = requests.post(
                f"{OLLAMA_SERVER_URL}/api/chat",
                json=payload,
                timeout=dynamic_timeout
            )
            
            # Check if the request was successful
            response.raise_for_status()
            
            # Parse the JSON response
            result = response.json()
            api_time = time.time() - api_start_time
            
            # Extract the response text
            if "message" in result:
                extracted_text = result["message"]["content"]
            else:
                logger.warning("No 'message' field in API response for batch processing")
                extracted_text = "No text could be extracted from the PDF."
            
            batch_total_time = time.time() - batch_start_time
            logger.info(f"Batch processing completed in {batch_total_time:.2f}s (API call: {api_time:.2f}s)")
            logger.info(f"Received response from Ollama ({len(extracted_text)} characters)")
            logger.info(f"*** PDF PROCESSING COMPLETED: {total_pages} pages in {batch_total_time:.2f}s ***")
            
            return extracted_text
    
    except requests.exceptions.Timeout:
        error_msg = "Request timed out while processing PDF. Try processing fewer pages or using page-by-page mode."
        logger.error(error_msg)
        raise Exception(error_msg)
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Error communicating with Ollama server: {str(e)}")
        raise Exception(f"Failed to communicate with Ollama server: {str(e)}")
    
    except Exception as e:
        logger.error(f"Unexpected error while processing PDF with Ollama: {str(e)}")
        raise Exception(f"Unexpected error while processing PDF with Ollama: {str(e)}") 