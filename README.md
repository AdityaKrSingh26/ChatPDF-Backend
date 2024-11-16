# API Documentation

## 1. Root Endpoint

### GET `/`

**Description**:  
Root endpoint to check the status of the service.

### Responses:
- **200 OK**  
  Returns the root status.

---

## 2. Upload PDF

### POST `/api/v1/upload_pdf`

**Description**:  
Uploads a PDF to the server and processes it.

### Parameters:
- **None**  

### Request Body:
- **Content-Type**: `multipart/form-data`
- **File**: 
  - **Field Name**: `file`
  - **Type**: `string($binary)`
  - **Example File**: `Abhisahar Article - Open Src.pdf`

### Example cURL Request:
```bash
curl -X 'POST' \
  'http://127.0.0.1:8000/api/v1/upload_pdf' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'file=@Abhisahar Article - Open Src.pdf;type=application/pdf'
```

### Responses:

#### 200 OK
- **Description**: PDF uploaded and processed successfully.
- **Response Body**:
```json
{
  "status": "success",
  "message": "PDF 'Abhisahar Article - Open Src.pdf' uploaded and processed successfully.",
  "data": {
    "pdf_id": "67385818c013d1176861687e",
    "pdf_metadata": {
      "id": "67385818c013d1176861687e",
      "filename": "Abhisahar Article - Open Src.pdf",
      "cloudinary_url": "https://res.cloudinary.com/dnu3aojdm/raw/upload/v1731745816/mxvdhu1nxgxtynjdecbw",
      "cloudinary_public_id": "mxvdhu1nxgxtynjdecbw",
      "file_size": 64475,
      "created_at": "2024-11-16T08:30:16",
      "format": "pdf"
    }
  }
}
```

#### 422 Unprocessable Entity
- **Description**: Validation error, typically due to missing or invalid parameters.
- **Response Body**:
```json
{
  "detail": [
    {
      "loc": ["body", "file"],
      "msg": "Field required",
      "type": "value_error.missing"
    }
  ]
}
```

---

## 3. List Uploaded PDFs

### GET `/api/v1/pdfs`

**Description**:  
Retrieves a list of uploaded PDFs with pagination support.

### Parameters:
- **skip**: `integer` (query) - Offset for pagination (default: 0).
- **limit**: `integer` (query) - Number of records to fetch (default: 10).

### Example cURL Request:
```bash
curl -X 'GET' \
  'http://127.0.0.1:8000/api/v1/pdfs?skip=0&limit=10' \
  -H 'accept: application/json'
```

### Responses:

#### 200 OK
- **Description**: Successfully retrieves the list of PDFs.
- **Response Body**:
```json
[
  {
    "id": "67385818c013d1176861687e",
    "filename": "Abhisahar Article - Open Src.pdf",
    "cloudinary_url": "https://res.cloudinary.com/dnu3aojdm/raw/upload/v1731745816/mxvdhu1nxgxtynjdecbw",
    "cloudinary_public_id": "mxvdhu1nxgxtynjdecbw",
    "file_size": 64475,
    "created_at": "2024-11-16T08:30:16",
    "format": "pdf"
  },
  ...
]
```

#### 422 Unprocessable Entity
- **Description**: Validation error for request parameters.
- **Response Body**:
```json
{
  "detail": [
    {
      "loc": ["query", "limit"],
      "msg": "Value is too large",
      "type": "value_error.max_size"
    }
  ]
}
```

---

## 4. Delete PDF

### DELETE `/api/v1/pdfs/{pdf_id}`

**Description**:  
Deletes a PDF from both Cloudinary and the database.

### Parameters:
- **pdf_id**: `string` (path) - The unique identifier of the PDF to be deleted.

### Example cURL Request:
```bash
curl -X 'DELETE' \
  'http://127.0.0.1:8000/api/v1/pdfs/673793c2fcf059dc08dcc4d2' \
  -H 'accept: application/json'
```

### Responses:

#### 200 OK
- **Description**: Successfully deleted the PDF.
- **Response Body**:
```json
{
  "status": "success",
  "message": "PDF deleted successfully",
  "pdf_id": "673793c2fcf059dc08dcc4d2"
}
```

#### 422 Unprocessable Entity
- **Description**: Validation error, typically due to an invalid `pdf_id`.
- **Response Body**:
```json
{
  "detail": [
    {
      "loc": ["path", "pdf_id"],
      "msg": "Invalid PDF ID",
      "type": "value_error"
    }
  ]
}
```

---

## 5. Query PDF

### POST `/api/v1/query`

**Description**:  
Queries a PDF with a specific question.

### Parameters:
- **pdf_id**: `string` (body) - The ID of the PDF to query.
- **query**: `string` (body) - The question to ask the PDF.

### Request Body:
```json
{
  "pdf_id": "67385818c013d1176861687e",
  "query": "what is the topic?"
}
```

### Example cURL Request:
```bash
curl -X 'POST' \
  'http://127.0.0.1:8000/api/v1/query' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
    "pdf_id": "67385818c013d1176861687e",
    "query": "what is the topic?"
  }'
```

### Responses:

#### 200 OK
- **Description**: Successfully queries the PDF.
- **Response Body**:
```json
{
  "id": "6738587ac013d1176861687f",
  "pdf_id": "67385818c013d1176861687e",
  "query": "what is the topic?",
  "response": "Open source software development",
  "created_at": "2024-11-16T08:31:54.333289"
}
```

#### 422 Unprocessable Entity
- **Description**: Validation error for request parameters.
- **Response Body**:
```json
{
  "detail": [
    {
      "loc": ["body", "query"],
      "msg": "Query is required",
      "type": "value_error.missing"
    }
  ]
}
```