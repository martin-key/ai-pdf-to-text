# PDF to Text Extraction API

A FastAPI backend that accepts PDF documents and extracts text using Gemma 3 model running on Ollama.

## Features

- Extract text from PDF documents using two methods:
  - **Vision Method** (default): Uses Gemma 3's multimodal capabilities to directly process PDF pages as images
  - **Text Method**: Uses PyPDF2 to extract text first, then processes with Gemma 3
- **Page-by-Page Processing** (recommended): Process each PDF page individually and then concatenate the results
  - Improved accuracy for contracts and multi-page documents
  - Better handling of complex layouts
  - Built-in retry mechanism for handling timeouts
  - Detailed progress tracking and logging
- **Multiple Upload Methods**:
  - Form-data upload (web forms, multipart/form-data)
  - Direct binary upload (Content-Type: application/pdf)

## Prerequisites

- Python 3.8+
- Ollama server running with Gemma 3 model installed
- Poppler (required for pdf2image)
  - On macOS: `brew install poppler`
  - On Ubuntu/Debian: `apt-get install poppler-utils`
  - On Windows: Download and install from [poppler releases](https://github.com/oschwartz10612/poppler-windows/releases/)

## Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/pdf-to-text.git
cd pdf-to-text
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
   - Copy the `.env.example` file to `.env`
   - Modify the variables as needed:
     - `OLLAMA_SERVER_URL`: URL of your Ollama server (default: http://192.168.10.226:11434)
     - `OLLAMA_MODEL`: Model to use (default: gemma3:4b)
     - `MAX_PAGES`: Maximum number of PDF pages to process at once (default: 10)
     - `PROCESS_PER_PAGE`: Whether to process each page individually (default: true)
     - `PAGE_TIMEOUT`: Timeout in seconds for processing each page (default: 90)
     - `RETRY_COUNT`: Number of retries for failed requests (default: 2)
     - `DEBUG_MODE`: Enable detailed debug logging (default: false)

## Usage

1. Start the server:
```bash
uvicorn app.main:app --reload
```

2. The API will be available at http://localhost:8000

3. Use the web interface at http://localhost:8000 to upload a PDF file and get extracted text

4. Or use the `/extract-text` endpoint to upload a PDF file with curl:

   ### Method 1: Form-data Upload
   ```bash
   # Vision method with page-by-page processing (default)
   curl -X POST -F "file=@/path/to/your/contract.pdf" http://localhost:8000/extract-text
   
   # Vision method with batch processing
   curl -X POST -F "file=@/path/to/your/contract.pdf" "http://localhost:8000/extract-text?processPerPage=false"
   
   # Text method (PyPDF2)
   curl -X POST -F "file=@/path/to/your/contract.pdf" "http://localhost:8000/extract-text?method=text"
   ```

   ### Method 2: Direct Binary Upload
   ```bash
   # Vision method with page-by-page processing (default)
   curl -X POST --location 'http://localhost:8000/extract-text' \
     --header 'Content-Type: application/pdf' \
     --data-binary '@/path/to/your/contract.pdf'
   
   # Vision method with batch processing
   curl -X POST --location 'http://localhost:8000/extract-text?processPerPage=false' \
     --header 'Content-Type: application/pdf' \
     --data-binary '@/path/to/your/contract.pdf'
   
   # Text method (PyPDF2)
   curl -X POST --location 'http://localhost:8000/extract-text?method=text' \
     --header 'Content-Type: application/pdf' \
     --data-binary '@/path/to/your/contract.pdf'
   ```

## API Endpoints

- `GET /`: Web interface for uploading PDFs
- `POST /extract-text`: Upload a PDF and get extracted text
  - Parameters:
    - `file`: The PDF file to extract text from (required for form-data method)
    - `method`: Text extraction method (`vision` or `text`, default: `vision`)
    - `processPerPage`: Whether to process each page individually (`true` or `false`, default: `true`)
  - Upload Methods:
    - **Multipart Form**: Upload with `Content-Type: multipart/form-data` and field name `file`
    - **Direct Binary**: Upload with `Content-Type: application/pdf` and PDF as raw body

## How It Works

### Vision Method with Page-by-Page Processing (Recommended for Contracts)

1. Converts each PDF page to an image using pdf2image
2. Processes each page individually with Gemma 3
   - Dynamic timeout based on image size
   - Automatic retry for failed requests
   - Progress tracking throughout processing
   - Continuity even if some pages fail
3. Concatenates the results from all pages
4. Returns the complete text with page markers

### Vision Method with Batch Processing

1. Converts PDF pages to images using pdf2image
2. Sends all images at once to Gemma 3 using Ollama's multimodal capabilities
3. Returns the extracted text as processed by the model

### Text Method (PyPDF2)

1. Extracts text from PDF using PyPDF2
2. Sends the extracted text to Gemma 3 for processing
3. Returns the processed text

## Troubleshooting

### Timeouts
- If you experience timeouts, try:
  - Using the page-by-page processing mode (default)
  - Reducing the number of pages being processed at once (MAX_PAGES)
  - Increasing the PAGE_TIMEOUT value in .env
  - Checking your Ollama server's resource utilization

### Debugging
- Enable DEBUG_MODE in your .env file for detailed logging
- Review the logs to see exactly where processing time is being spent
- Each page's progress is tracked individually with clear markers

## Docker Support

Build the Docker image:
```bash
docker build -t pdf-to-text .
```

Run the container:
```bash
docker run -p 8000:8000 --env-file .env pdf-to-text
```

## CI/CD with GitHub Actions

This repository includes GitHub Actions workflows for continuous integration and deployment:

### Automatic Docker Image Building

The workflow automatically builds and pushes a Docker image to GitHub Container Registry (ghcr.io) when:
- Pushing to the main/master branch
- Creating a new release tag (v*)

The resulting image will be available at: `ghcr.io/yourusername/pdf-to-text:latest`

### Using the Container Image

1. Pull the image from GitHub Container Registry:
```bash
docker pull ghcr.io/yourusername/pdf-to-text:latest
```

2. Run the container:
```bash
docker run -p 8000:8000 \
  -e OLLAMA_SERVER_URL=http://your-ollama-server:11434 \
  -e OLLAMA_MODEL=gemma3:4b \
  ghcr.io/yourusername/pdf-to-text:latest
```

3. For production use, you can specify a specific version tag:
```bash
docker pull ghcr.io/yourusername/pdf-to-text:v1.0.0
```

### Release Process

To create a new release:

1. Create and push a new tag:
```bash
git tag v1.0.0
git push origin v1.0.0
```

2. GitHub Actions will automatically build and push the tagged version.

3. You can then use the specific version in your deployments:
```bash
docker pull ghcr.io/yourusername/pdf-to-text:v1.0.0
``` 