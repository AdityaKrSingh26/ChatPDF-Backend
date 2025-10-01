# ChatPDF Backend

A FastAPI-based backend service that allows users to upload PDF documents and query their content using AI. The system uses Google Gemini AI for intelligent document querying, Cloudinary for file storage, and MongoDB for metadata management.

## Features

- **PDF Upload & Storage**: Upload PDF documents to Cloudinary cloud storage
- **AI-Powered Querying**: Query PDF content using Google Gemini AI
- **Document Management**: List, view, and delete uploaded PDFs
- **Query History**: Track and retrieve past queries for each document
- **Intelligent Text Processing**: Advanced text chunking and similarity search for relevant content extraction
- **RESTful API**: Clean, well-documented REST API endpoints
- **Async Operations**: High-performance async/await implementation

## Tech Stack

- **Framework**: FastAPI (Python)
- **Database**: MongoDB with Motor (async driver)
- **File Storage**: Cloudinary
- **AI Model**: Google Gemini Pro
- **Text Processing**: 
  - PyPDF2 for PDF text extraction
  - SentenceTransformers for embeddings
  - Scikit-learn for similarity calculations
- **Other Tools**: 
  - Pydantic for data validation
  - CORS middleware for cross-origin requests

## Quick Start

### Prerequisites

- Python 3.8+
- MongoDB instance
- Cloudinary account
- Google Gemini API key

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/AdityaKrSingh26/ChatPDF-Backend.git
   cd ChatPDF-Backend
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Environment Setup**
   
   Create a `.env` file in the root directory:
   ```env
   # MongoDB Configuration
   MONGODB_URL=mongodb://localhost:27017
   DB_NAME=pdf_query_system
   
   # Cloudinary Configuration
   CLOUDINARY_CLOUD_NAME=your_cloud_name
   CLOUDINARY_API_KEY=your_api_key
   CLOUDINARY_API_SECRET=your_api_secret
   
   # AI Configuration
   GEMINI_API_KEY=your_gemini_api_key
   OPENAI_API_KEY=your_openai_key  # Optional
   ```

4. **Run the application**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

The API will be available at `http://localhost:8000`

## API Documentation

### Base URL
```
http://localhost:8000
```

### Authentication
Currently, no authentication is required. All endpoints are publicly accessible.

---

## API Endpoints

### 1. Health Check

#### GET `/`
Check if the service is running.

**Response:**
```json
{
  "message": "Welcome to the PDF Query System API!"
}
```

---

### 2. Upload PDF

#### POST `/api/v1/upload_pdf`
Upload a PDF document for processing and querying.

**Request:**
- **Content-Type**: `multipart/form-data`
- **Body**: PDF file with field name `file`

**Example:**
```bash
curl -X POST \
  'http://localhost:8000/api/v1/upload_pdf' \
  -H 'accept: application/json' \
  -F 'file=@document.pdf'
```

**Response (200):**
```json
{
  "status": "success",
  "message": "PDF 'document.pdf' uploaded and processed successfully.",
  "data": {
    "pdf_id": "67385818c013d1176861687e",
    "pdf_metadata": {
      "id": "67385818c013d1176861687e",
      "filename": "document.pdf",
      "cloudinary_url": "https://res.cloudinary.com/...",
      "cloudinary_public_id": "unique_id",
      "file_size": 64475,
      "created_at": "2024-11-16T08:30:16",
      "format": "pdf"
    }
  }
}
```

---

### 3. List PDFs

#### GET `/api/v1/pdfs`
Retrieve a paginated list of uploaded PDFs.

**Parameters:**
- `skip` (int, optional): Number of records to skip (default: 0)
- `limit` (int, optional): Maximum records to return (default: 10)

**Example:**
```bash
curl -X GET \
  'http://localhost:8000/api/v1/pdfs?skip=0&limit=10' \
  -H 'accept: application/json'
```

**Response (200):**
```json
[
  {
    "id": "67385818c013d1176861687e",
    "filename": "document.pdf",
    "cloudinary_url": "https://res.cloudinary.com/...",
    "cloudinary_public_id": "unique_id",
    "file_size": 64475,
    "created_at": "2024-11-16T08:30:16",
    "format": "pdf"
  }
]
```

---

### 4. Query PDF

#### POST `/api/v1/query`
Ask questions about the content of an uploaded PDF.

**Request Body:**
```json
{
  "pdf_id": "67385818c013d1176861687e",
  "query": "What is the main topic of this document?"
}
```

**Example:**
```bash
curl -X POST \
  'http://localhost:8000/api/v1/query' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
    "pdf_id": "67385818c013d1176861687e",
    "query": "What is the main topic?"
  }'
```

**Response (200):**
```json
{
  "id": "6738587ac013d1176861687f",
  "pdf_id": "67385818c013d1176861687e",
  "query": "What is the main topic?",
  "response": "The main topic of this document is artificial intelligence and its applications in modern technology.",
  "created_at": "2024-11-16T08:31:54.333289"
}
```

---

### 5. Query History

#### GET `/api/v1/history/{pdf_id}`
Retrieve the query history for a specific PDF.

**Parameters:**
- `pdf_id` (string): The ID of the PDF
- `skip` (int, optional): Number of records to skip (default: 0)
- `limit` (int, optional): Maximum records to return (default: 10)

**Example:**
```bash
curl -X GET \
  'http://localhost:8000/api/v1/history/67385818c013d1176861687e?skip=0&limit=5' \
  -H 'accept: application/json'
```

---

### 6. Delete PDF

#### DELETE `/api/v1/pdfs/{pdf_id}`
Delete a PDF and all associated queries from both Cloudinary and the database.

**Parameters:**
- `pdf_id` (string): The ID of the PDF to delete

**Example:**
```bash
curl -X DELETE \
  'http://localhost:8000/api/v1/pdfs/67385818c013d1176861687e' \
  -H 'accept: application/json'
```

**Response (200):**
```json
{
  "status": "success",
  "message": "PDF and associated queries deleted successfully",
  "pdf_id": "67385818c013d1176861687e",
  "deleted_queries_count": 5
}
```

---

## Project Structure

```
ChatPDF-Backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── config.py            # Configuration settings
│   ├── api/
│   │   └── endpoints/
│   │       ├── pdf.py       # PDF management endpoints
│   │       └── query.py     # Query processing endpoints
│   ├── db/
│   │   └── mongodb.py       # MongoDB connection and operations
│   ├── schemas/
│   │   └── models.py        # Pydantic models for request/response
│   └── utils/
│       └── pdf_processor.py # PDF processing and AI utilities
├── requirements.txt         # Python dependencies
├── README.md               # This file
└── .env                    # Environment variables (create this)
```

## Configuration

The application uses environment variables for configuration. Create a `.env` file with the following variables:

| Variable | Description | Required |
|----------|-------------|----------|
| `MONGODB_URL` | MongoDB connection string | Yes |
| `DB_NAME` | Database name | Yes |
| `CLOUDINARY_CLOUD_NAME` | Cloudinary cloud name | Yes |
| `CLOUDINARY_API_KEY` | Cloudinary API key | Yes |
| `CLOUDINARY_API_SECRET` | Cloudinary API secret | Yes |
| `GEMINI_API_KEY` | Google Gemini API key | Yes |
| `OPENAI_API_KEY` | OpenAI API key | No |

## How It Works

1. **PDF Upload**: Users upload PDF files which are stored in Cloudinary
2. **Text Extraction**: PyPDF2 extracts text content from the PDF
3. **Text Chunking**: Large documents are split into manageable chunks with overlap
4. **Embedding Generation**: SentenceTransformers creates embeddings for text chunks
5. **Query Processing**: User queries are matched against relevant chunks using cosine similarity
6. **AI Response**: Google Gemini generates contextual responses based on relevant content
7. **Storage**: All queries and responses are stored in MongoDB for history tracking

## Deployment

### Production Deployment

1. **Environment Variables**: Set all required environment variables
2. **Database**: Ensure MongoDB is accessible
3. **Dependencies**: Install production dependencies
4. **WSGI Server**: Use Gunicorn or similar for production

```bash
# Install Gunicorn
pip install gunicorn

# Run with Gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

## Testing

### Manual Testing
Visit `http://localhost:8000/docs` for interactive API documentation (Swagger UI).

### API Testing Examples

```bash
# Test PDF upload
curl -X POST http://localhost:8000/api/v1/upload_pdf \
  -F 'file=@test.pdf'

# Test query
curl -X POST http://localhost:8000/api/v1/query \
  -H 'Content-Type: application/json' \
  -d '{"pdf_id": "your_pdf_id", "query": "What is this document about?"}'
```

## Error Handling

The API returns appropriate HTTP status codes and error messages:

- **200**: Success
- **400**: Bad Request (invalid file type, etc.)
- **404**: Not Found (PDF not found)
- **422**: Validation Error (missing fields, invalid data)
- **500**: Internal Server Error

Example error response:
```json
{
  "detail": "Only PDF files are allowed."
}
```

## Contributing

We welcome contributions to the ChatPDF Backend project! Whether you're fixing bugs, adding features, or improving documentation, your help is appreciated.

### Quick Setup

**Prerequisites**: Python 3.8+, Git, MongoDB, FastAPI knowledge

1. **Fork and Clone**
   ```bash
   git clone https://github.com/YOUR_USERNAME/ChatPDF-Backend.git
   cd ChatPDF-Backend
   ```

2. **Setup Environment**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   # source venv/bin/activate  # macOS/Linux
   pip install -r requirements.txt
   ```

3. **Configure and Run**
   ```bash
   # Create .env with your development config
   uvicorn app.main:app --reload
   ```

### Guidelines

**Code Standards**:
- Follow PEP 8, use type hints, async/await for I/O
- Format with: `black . && isort . && flake8 .`

**Commit Format**:
```bash
type(scope): description
# Examples:
feat(api): add batch upload endpoint
fix(query): handle empty PDF extraction
docs: update API documentation
```

### Workflow

1. **Branch**: `git checkout -b feature/your-feature`
2. **Code**: Write clean, tested code following existing patterns
3. **Test**: Run locally and verify at `http://localhost:8000/docs`
4. **Commit**: `git commit -m "feat: your feature"`
5. **PR**: Submit with description and checklist and Raise your PR on DEV branch

### Pull Request Checklist

```markdown
## What this PR does
Brief description of changes

## Type of Change
- [ ] Bug fix / New feature / Breaking change / Documentation

## Testing Done
- [ ] Tested locally
- [ ] Added tests for new functionality
- [ ] All existing tests pass
- [ ] Updated documentation

## Changes Made
- List key changes
- Note any new dependencies
- Mention configuration updates needed
```

### Issues & Requests

**Bug Reports**: Include title, reproduction steps, expected vs actual behavior, environment details, error messages

**Feature Requests**: Include problem statement, proposed solution, alternatives considered


### Help & Support

- **Issues**: Bug reports and feature requests
- **Discussions**: Questions and general discussion
- **PR Comments**: Code review discussions

**Code Review Process**: Automated checks → Peer review → Testing → Documentation → Approval

Thank you for contributing!
