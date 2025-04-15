#!/bin/bash

# This script demonstrates how to use curl to upload a PDF file to the API

# Check if a PDF file path was provided
if [ -z "$1" ]; then
  echo "Usage: $0 <path_to_pdf_file>"
  exit 1
fi

PDF_FILE="$1"

# Check if the file exists
if [ ! -f "$PDF_FILE" ]; then
  echo "Error: File '$PDF_FILE' not found."
  exit 1
fi

# Check if the file is a PDF
if [[ ! "$PDF_FILE" =~ \.pdf$ ]]; then
  echo "Error: File '$PDF_FILE' is not a PDF file."
  exit 1
fi

# API URL
API_URL="http://localhost:8000/extract-text"

echo "Uploading $PDF_FILE to $API_URL..."

# The key part is using the correct form field name 'file'
# This matches the parameter name in the FastAPI endpoint
curl -X POST \
  -F "file=@$PDF_FILE" \
  "$API_URL"

echo ""
echo "Done!" 