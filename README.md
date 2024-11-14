## API Documentation

### 1. Upload PDF
Uploads a PDF file to Cloudinary and saves its metadata in MongoDB.

- **URL:** `/upload_pdf`
- **Method:** `POST`
- **Content-Type:** `multipart/form-data`
- **Request Body:**
  - `file` (required, type: `UploadFile`): PDF file to be uploaded.

**Example Request:**
```bash
curl -X POST "http://localhost:8000/upload_pdf" -F "file=@/path/to/file.pdf"
```

**Response:**
- **Status:** `200 OK`
- **Content-Type:** `application/json`
- **Response JSON:**
  ```json
  {
    "status": "success",
    "message": "PDF 'sample.pdf' uploaded and processed successfully.",
    "data": {
      "pdf_id": "64f60c1b8f8e4b48d8f8e4b4",
      "pdf_metadata": {
        "id": "64f60c1b8f8e4b48d8f8e4b4",
        "filename": "sample.pdf",
        "cloudinary_url": "https://res.cloudinary.com/.../sample.pdf",
        "cloudinary_public_id": "sample_id",
        "file_size": 123456,
        "created_at": "2024-10-15T12:00:00Z",
        "format": "pdf"
      }
    }
  }
  ```

---

### 2. Query PDF
Queries the content of a PDF by extracting relevant text chunks and returning a generated response based on a query.

- **URL:** `/query`
- **Method:** `POST`
- **Content-Type:** `application/json`
- **Request Body:**
  - `pdf_id` (type: `str`, required): The MongoDB ID of the PDF document.
  - `query` (type: `str`, required): The query text.

**Example Request:**
```json
{
  "pdf_id": "64f60c1b8f8e4b48d8f8e4b4",
  "query": "What is the summary of this document?"
}
```

**Response:**
- **Status:** `200 OK`
- **Content-Type:** `application/json`
- **Response JSON:**
  ```json
  {
    "id": "64f61d2b8f8e4b49d8f8e4c7",
    "pdf_id": "64f60c1b8f8e4b48d8f8e4b4",
    "query": "What is the summary of this document?",
    "response": "This document discusses...",
    "created_at": "2024-10-15T12:05:00Z"
  }
  ```

---

### 3. Get Query History
Retrieves the history of previous queries for a specific PDF.

- **URL:** `/history/{pdf_id}`
- **Method:** `GET`
- **Content-Type:** `application/json`
- **Path Parameter:**
  - `pdf_id` (type: `str`, required): The MongoDB ID of the PDF document.
- **Query Parameters:**
  - `skip` (type: `int`, optional, default: `0`): Number of records to skip for pagination.
  - `limit` (type: `int`, optional, default: `10`): Max number of records to return.

**Example Request:**
```bash
curl -X GET "http://localhost:8000/history/64f60c1b8f8e4b48d8f8e4b4?skip=0&limit=10"
```

**Response:**
- **Status:** `200 OK`
- **Content-Type:** `application/json`
- **Response JSON:**
  ```json
  [
    {
      "id": "64f61d2b8f8e4b49d8f8e4c7",
      "pdf_id": "64f60c1b8f8e4b48d8f8e4b4",
      "query": "What is the summary of this document?",
      "response": "This document discusses...",
      "created_at": "2024-10-15T12:05:00Z"
    },
    {
      "id": "64f61d2c8f8e4b49d8f8e4c8",
      "pdf_id": "64f60c1b8f8e4b48d8f8e4b4",
      "query": "List the main points of the document.",
      "response": "The main points are...",
      "created_at": "2024-10-15T12:10:00Z"
    }
  ]
  ```

---

### 4. Delete PDF
Deletes a PDF from both Cloudinary and MongoDB.

- **URL:** `/pdfs/{pdf_id}`
- **Method:** `DELETE`
- **Path Parameter:**
  - `pdf_id` (type: `str`, required): The MongoDB ID of the PDF document to delete.

**Example Request:**
```bash
curl -X DELETE "http://localhost:8000/pdfs/64f60c1b8f8e4b48d8f8e4b4"
```

**Response:**
- **Status:** `200 OK`
- **Content-Type:** `application/json`
- **Response JSON:**
  ```json
  {
    "status": "success",
    "message": "PDF deleted successfully",
    "pdf_id": "64f60c1b8f8e4b48d8f8e4b4"
  }
  ```

---