import requests
import sys
import os

# Replace with your API URL
API_URL = "http://localhost:8000/extract-text"

def extract_text_from_pdf(pdf_path):
    """
    Send a PDF file to the API and get the extracted text.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        The response from the API
    """
    # Check if file exists
    if not os.path.exists(pdf_path):
        print(f"Error: File {pdf_path} does not exist.")
        return
    
    # Check if file is a PDF
    if not pdf_path.lower().endswith('.pdf'):
        print(f"Error: File {pdf_path} is not a PDF.")
        return
    
    # Prepare the files for the request
    # Important: 'file' must match the parameter name in the FastAPI endpoint
    files = {'file': open(pdf_path, 'rb')}
    
    try:
        # Make the POST request
        print(f"Sending {pdf_path} to {API_URL}...")
        response = requests.post(API_URL, files=files)
        
        # Close the file
        files['file'].close()
        
        # Check if request was successful
        response.raise_for_status()
        
        # Return the response
        return response.json()
    
    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error: {e}")
        if response.status_code == 422:
            print("This error usually means the 'file' parameter wasn't correctly sent.")
            print("Make sure you're using 'file' as the form field name.")
        if hasattr(response, 'text'):
            print(f"Response details: {response.text}")
    
    except Exception as e:
        print(f"Error: {str(e)}")
        
if __name__ == "__main__":
    # Check if PDF file path is provided
    if len(sys.argv) < 2:
        print("Usage: python test_client.py <path_to_pdf>")
        sys.exit(1)
    
    # Get PDF file path
    pdf_path = sys.argv[1]
    
    # Extract text from PDF
    result = extract_text_from_pdf(pdf_path)
    
    # Print result
    if result:
        print("\nExtracted Text:")
        print(result['text']) 