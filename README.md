# Vector Knowledge Base

*A personal semantic search engine for your documents and knowledge base*

[![Python](https://img.shields.io/badge/Python-3.11+-blue?style=flat-square)](https://www.python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat-square)](https://fastapi.tiangolo.com)
[![Qdrant](https://img.shields.io/badge/Qdrant-Vector_Database-DC244C?style=flat-square)](https://qdrant.tech)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

[Features](#features) • [Quick Start](#quick-start) • [Usage](#usage) • [Architecture](#architecture) • [API Reference](#api-reference)

---

**Vector Knowledge Base** is a vector database application that transforms your documents into a searchable knowledge base using semantic search. Upload PDFs, Word documents, and code files, then search using natural language to find exactly what you need.

## Features

- **Semantic Search** - Find documents by meaning, not just keywords
- **Multi-Format Support** - PDF, DOCX, TXT, Markdown, and code files (.py, .js, .java, etc.)
- **Intelligent Chunking** - AST-aware parsing for code, sentence-boundary awareness for prose
- **Folder Organization** - Drag-and-drop file management with custom folder hierarchy
- **Modern UI** - Clean, responsive interface with dark mode support
- **Vector Embeddings** - Powered by SentenceTransformers (all-mpnet-base-v2, 768-dimensional embeddings)
- **High-Performance Search** - Qdrant vector database for sub-50ms search queries

## Quick Start

### Prerequisites

- Python 3.11 or higher
- Docker (for Qdrant vector database)
- Node.js 18+ (optional, for development server)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/i3T4AN/Vector-Knowledge-Base.git
   cd database
   ```

2. **Start Qdrant with Docker**
   ```bash
   docker run -d -p 6333:6333 -v ./qdrant_storage:/qdrant/storage:z qdrant/qdrant
   ```

3. **Set up Python environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. **Start the backend server**
   ```bash
   cd backend
   python -m uvicorn main:app --reload --port 8001
   ```

5. **Start the frontend server**
   ```bash
   cd frontend
   python -m http.server 8002
   ```

6. **Open your browser**
   
   Navigate to `http://localhost:8002`

> [!TIP]
> On first run, the embedding model (~400MB) will be downloaded automatically. This may take a few minutes.

## Usage

### Uploading Documents

1. Navigate to the **Upload** tab
2. Drag and drop files or click to browse
3. Add metadata (course name, document type, tags)
4. Click **Upload**

The backend will:
- Extract text from your files
- Split content into intelligent chunks
- Generate vector embeddings
- Store in Qdrant for fast retrieval

### Searching

1. Navigate to the **Search** tab
2. Enter your query in natural language
3. Optionally filter by:
   - File extension
   - Date range
   - Document type
4. Click **Search** to see ranked results with similarity scores

### Organizing Files

Use the **Files** tab to:
- Create custom folders
- Drag files between folders
- View unsorted files in the sidebar
- Navigate with breadcrumb navigation

## Architecture

```
┌─────────────┐
│   Frontend  │  Vanilla JavaScript + CSS
│  (Port 8002)│  
└──────┬──────┘
       │ HTTP
       ▼
┌─────────────┐
│   Backend   │  FastAPI + Python
│  (Port 8001)│  
└──────┬──────┘
       │
   ┌───┴────┬────────────┐
   ▼        ▼            ▼
┌──────┐ ┌──────┐ ┌──────────┐
│SQLite│ │Qdrant│ │Sentence  │
│(Meta)│ │(Vec) │ │Transform │
└──────┘ └──────┘ └──────────┘
         Port 6333
```

### Tech Stack

**Backend:**
- FastAPI - Modern async web framework
- Qdrant - High-performance vector database (Dockerized)
- SentenceTransformers - State-of-the-art embeddings
- SQLite - Lightweight metadata storage

**Frontend:**
- Vanilla JavaScript (ES6+)
- Custom CSS with modern design patterns
- Fetch API for backend communication

**File Processing:**
- pypdf - PDF text extraction
- docx2txt - Word document parsing
- AST parser - Code-aware chunking

## API Reference

### Core Endpoints

#### Upload Document
```http
POST /upload
Content-Type: multipart/form-data

Parameters:
- file: File (required)
- course_name: string (required)
- document_type: string (optional)
- tags: string[] (optional)

Response: {
  "filename": "doc.pdf",
  "chunks_count": 42,
  "document_id": "uuid"
}
```

#### Search
```http
POST /search
Content-Type: application/json

Body: {
  "query": "What is semantic search?",
  "extension": ".pdf",
  "start_date": "2024-01-01",
  "end_date": "2024-12-31",
  "limit": 10
}

Response: {
  "results": [
    {
      "text": "chunk content",
      "score": 0.89,
      "metadata": {...}
    }
  ]
}
```

#### List Documents
```http
GET /documents

Response: [
  {
    "filename": "doc.pdf",
    "course_name": "CS101",
    "upload_date": "2024-01-15"
  }
]
```

#### Delete Document
```http
DELETE /documents/{filename}

Response: {
  "message": "Document deleted successfully"
}
```

### Folder Management

- `GET /folders` - List all folders
- `POST /folders` - Create folder
- `PUT /folders/{id}` - Update folder
- `DELETE /folders/{id}` - Delete empty folder
- `POST /files/move` - Move file to folder
- `GET /files/unsorted` - List unsorted files

## Configuration

Create a `.env` file in the backend directory:

```env
# Qdrant Configuration
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=vector_db

# File Upload Settings
UPLOAD_DIR=../uploads
MAX_FILE_SIZE=52428800  # 50MB

# Embedding Model
EMBEDDING_MODEL=all-mpnet-base-v2

# Chunking Settings
CHUNK_SIZE=500
CHUNK_OVERLAP=50
```

## Troubleshooting

### Qdrant Connection Error

If you see "Connection refused" errors:

```bash
# Check if Qdrant is running
docker ps

# Restart Qdrant container
docker restart <container-id>

# Or start a new container
docker run -d -p 6333:6333 -v ./qdrant_storage:/qdrant/storage:z qdrant/qdrant
```

### Backend Won't Start

> [!WARNING]
> Dependency conflicts between `sentence-transformers` and `huggingface-hub` can cause startup failures.

Solution:
```bash
pip install --upgrade sentence-transformers huggingface-hub
```

### File Upload Fails

Check supported file types:
- Documents: `.pdf`, `.docx`, `.txt`, `.md`
- Code: `.py`, `.js`, `.java`, `.cpp`, `.c`, `.h`, `.cs`

Maximum file size: 50MB (configurable)

## Project Structure

```
database/
├── backend/
│   ├── extractors/          # File format parsers
│   ├── main.py             # FastAPI application
│   ├── vector_db.py        # Qdrant client
│   ├── embedding_service.py # Embedding generation
│   ├── ingestion.py        # File processing pipeline
│   ├── chunker.py          # Text chunking logic
│   ├── filesystem_db.py    # SQLite for folders
│   ├── config.py           # Configuration
│   └── exceptions.py       # Custom exceptions
├── frontend/
│   ├── index.html          # Main UI
│   ├── styles.css          # Styling
│   ├── search.js           # Search functionality
│   ├── upload.js           # File upload
│   ├── filesystem.js       # Folder management
│   ├── documents.js        # Document listing
│   └── notifications.js    # Toast notifications
├── qdrant_storage/         # Vector DB persistence
├── uploads/                # Uploaded files
└── requirements.txt        # Python dependencies
```

## Performance

- **Upload**: ~2-5 seconds for typical PDF
- **Search**: 100-500ms depending on corpus size (sub-50ms for <10k vectors)
- **Embedding**: ~50-100ms per chunk
- **Capacity**: Scales to 100k+ documents with Qdrant

---

Built with ❤️ using FastAPI, Qdrant, and SentenceTransformers
