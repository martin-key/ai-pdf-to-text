#!/usr/bin/env python3
"""
Direct Binary Upload Client for PDF-to-Text API

This script demonstrates how to upload a PDF directly as binary content
to the PDF-to-Text API without using form-data.
"""

import argparse
import requests
import json
import sys
import os
from urllib.parse import urljoin

def extract_text_from_pdf(api_url, pdf_path, method="vision", process_per_page=True):
    """
    Extract text from a PDF using direct binary upload.
    
    Args:
        api_url: Base URL of the API
        pdf_path: Path to the PDF file
        method: Text extraction method (vision or text)
        process_per_page: Whether to process each page individually
        
    Returns:
        The API response
    """
    # Build the endpoint URL
    endpoint = urljoin(api_url, "/extract-text")
    params = {
        "method": method,
        "processPerPage": str(process_per_page).lower()
    }
    
    # Check if file exists
    if not os.path.exists(pdf_path):
        print(f"Error: File {pdf_path} does not exist.")
        sys.exit(1)
    
    # Check if file is a PDF
    if not pdf_path.lower().endswith('.pdf'):
        print(f"Error: File {pdf_path} is not a PDF.")
        sys.exit(1)
    
    # Read the PDF file as binary
    with open(pdf_path, 'rb') as pdf_file:
        pdf_content = pdf_file.read()
    
    # Prepare headers
    headers = {
        "Content-Type": "application/pdf",
        "File-Name": os.path.basename(pdf_path)
    }
    
    print(f"Sending PDF '{os.path.basename(pdf_path)}' to {endpoint}")
    print(f"Method: {method}, Process Per Page: {process_per_page}")
    
    try:
        # Make the POST request with binary content
        response = requests.post(
            endpoint,
            params=params,
            headers=headers,
            data=pdf_content,
            timeout=600  # 10 minutes timeout for large files
        )
        
        # Check if request was successful
        response.raise_for_status()
        
        # Parse and return the JSON response
        return response.json()
    
    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error: {e}")
        if response.status_code == 400:
            print("Bad request: The API rejected the PDF file")
        elif response.status_code == 422:
            print("Validation error: Check your parameters")
        try:
            error_detail = response.json()
            print(f"Error details: {json.dumps(error_detail, indent=2)}")
        except:
            print(f"Response: {response.text}")
    
    except requests.exceptions.ConnectionError:
        print(f"Error: Could not connect to {api_url}")
        print("Make sure the API server is running and accessible")
    
    except requests.exceptions.Timeout:
        print("Error: Request timed out")
        print("The PDF might be too large or complex for processing within the timeout limit")
    
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract text from a PDF using direct binary upload")
    
    parser.add_argument("pdf_path", help="Path to the PDF file")
    parser.add_argument("--url", default="http://localhost:8000", help="API base URL (default: http://localhost:8000)")
    parser.add_argument("--method", choices=["vision", "text"], default="vision", help="Text extraction method (default: vision)")
    parser.add_argument("--batch", action="store_true", help="Use batch processing instead of page-by-page")
    
    args = parser.parse_args()
    
    # Extract text from PDF
    result = extract_text_from_pdf(
        api_url=args.url,
        pdf_path=args.pdf_path,
        method=args.method,
        process_per_page=not args.batch
    )
    
    # Print result
    if result:
        print("\nExtracted Text:")
        print("=" * 80)
        print(result["text"])
        print("=" * 80)
        print(f"Method: {result['method']}")
        if result['method'] == 'vision':
            print(f"Processing: {'Page-by-page' if result['processPerPage'] else 'Batch'}") 