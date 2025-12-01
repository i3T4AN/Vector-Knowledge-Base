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
- **Auto-Clustering** - Automatically organize documents into semantic clusters using HDBSCAN (density-based clustering)
- **Semantic Cluster Naming** - Clusters are automatically named using TF-IDF keyword extraction (e.g., "Shakespeare & Drama", "Python & Programming")
- **Cluster-Based Filtering** - Filter search results by document clusters for more focused searches
- **Batch Upload & Folder Preservation** - Drag and drop entire folders to upload, automatically preserving folder structure in your knowledge base
- **3D Embedding Visualization** - Interactive 3D visualization of your document embeddings using Three.js
- **Multi-Format Support** - PDF, DOCX, TXT, Markdown, and code files (.py, .js, .java, etc.)
- **Intelligent Chunking** - AST-aware parsing for code, sentence-boundary awareness for prose
- **Folder Organization** - Drag-and-drop file management with custom folder hierarchy
- **File Viewer** - Double-click any file to preview it directly in the browser
- **Multi-Page Navigation** - Dedicated pages for search, documents, and file management
- **Data Management** - Export all data as ZIP or reset the entire database with one click
- **Modern UI** - Clean, responsive interface with dark mode and modular CSS architecture
- **Vector Embeddings** - Powered by SentenceTransformers (all-mpnet-base-v2, 768-dimensional embeddings)
- **High-Performance Search** - Qdrant vector database for sub-50ms search queries

![Main Search Interface](screenshots/search-interface.png)
*Clean, modern dark-mode interface with semantic search and filtering options*

## Quick Start

### Prerequisites

- Docker and Docker Compose (recommended)
- **OR** Python 3.11+ and Docker (for manual setup)

### Option 1: Docker Deployment (Recommended)

The easiest way to run the entire application:

1. **Clone the repository**
   ```bash
   git clone https://github.com/i3T4AN/Vector-Knowledge-Base.git
   cd Vector-Knowledge-Base
   ```

2. **Start all services with Docker Compose**
   ```bash
   docker-compose up -d
   ```

3. **Open your browser**
   
   Navigate to `http://localhost:8001/index.html`

That's it! Docker Compose will automatically:
- Start Qdrant vector database
- Build and start the backend API
- Start the frontend server with Nginx

> [!TIP]
> On first run, the embedding model (~400MB) will be downloaded automatically. This may take a few minutes.

**Managing the application:**
```bash
# View logs
docker-compose logs -f

# Stop all services
docker-compose down

# Rebuild after code changes
docker-compose up -d --build
```

### Option 2: Manual Installation

For development or if you prefer not to use Docker:

1. **Clone the repository**
   ```bash
   git clone https://github.com/i3T4AN/Vector-Knowledge-Base.git
   cd Vector-Knowledge-Base
   ```

2. **Start Qdrant with Docker**
   ```bash
   docker run -d -p 6333:6333 -v ./qdrant_storage:/qdrant/storage:z qdrant/qdrant
   ```

3. **Set up Python environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   python -m pip install -r requirements.txt
   ```

4. **Start the backend server**
   ```bash
   cd backend
   python -m uvicorn main:app --reload --port 8000 --host 0.0.0.0
   ```

5. **Start the frontend server**
   ```bash
   cd frontend
   python -m http.server 8001
   ```
   
   > [!NOTE]
   > On Mac, use `python3` instead of `python` if the command is not found.

6. **Open your browser**
   
   Navigate to `http://localhost:8001/index.html`

> [!TIP]
> On first run, the embedding model (~400MB) will be downloaded automatically. This may take a few minutes.

## Usage

### Uploading Documents

1. Navigate to the **My Documents** page (`documents.html`)
2. Drag and drop files or click to browse
   - **Batch Upload**: Drop entire folders to upload multiple files at once
   - **Folder Preservation**: Folder structure is automatically maintained in the "Files" tab
3. Add metadata (course name, document type, tags)
4. Click **Upload**
5. Monitor progress in the Queue card for batch uploads

The backend will:
- Extract text from your files
- Split content into intelligent chunks
- Generate vector embeddings
- Store in Qdrant for fast retrieval
- Organize files in folders matching your source structure

![Document Upload Page](screenshots/documents-page.png)
*Upload interface with drag-and-drop support, batch queue, and document management*

### Searching

1. Navigate to the **Search** page (`index.html`)
2. Enter your query in natural language
3. Optionally filter by:
   - **Cluster** - Filter results by document cluster (requires clustering first)
   - **Date range** - Filter by upload date
   - **Result limit** - Number of results to display (5, 10, or 20)
4. Click **Search** to see ranked results with similarity scores

![Search Results](screenshots/search-results.png)
*Semantic search results showing similarity scores and relevant text snippets*

### Auto-Clustering Documents

1. Navigate to the **Search** page (`index.html`)
2. Upload several documents first (at least 2 documents required)
3. Click **Auto-Cluster Documents**
4. The system will:
   - Automatically determine the optimal number of clusters using HDBSCAN
   - Group similar documents together using density-based clustering
   - Generate semantic names for each cluster (e.g., "Python & Programming")
   - Update document metadata with cluster assignments and names
5. Use the **Cluster** filter to search within specific document groups (shown as "ID: Cluster Name")

![3D Visualization with Clusters](screenshots/3d-visualization.png)
*Interactive 3D embedding space showing document clusters and search results with cluster information*

### Organizing Files

Use the **Files** page (`files.html`) to:
- Create custom folders
- Drag files between folders
- View unsorted files in the sidebar
- Navigate with breadcrumb navigation
- **Double-click any file** to open it in the built-in file viewer

![File Organization](screenshots/files-page.png)
*File management interface with folder hierarchy and drag-and-drop organization*

### Data Management

In the **My Documents** tab, you can:
- **Export Data** - Download all uploaded files as a ZIP archive for backup
- **Delete Data** - Reset the entire database (requires confirmation)
  - Clears all vector embeddings from Qdrant
  - Removes all folder organization
  - Deletes all uploaded files
  - This action is irreversible

### 3D Visualization

1. Navigate to the **Search** page (index.html)
2. Click **Show 3D Embedding Space** to reveal the interactive visualization
3. Explore your document corpus in 3D space
4. Enter a search query to see:
   - Your query point highlighted in gold
   - Top matching documents connected with colored lines
   - Line colors indicating similarity (green = high, red = low)
5. Hover over points to see document details

## Architecture

### System Overview

```
┌─────────────┐
│   Frontend  │  Multi-Page Application
│  (Port 8001)│  index.html, documents.html, files.html
└──────┬──────┘
       │ HTTP
       ▼
┌─────────────┐
│   Backend   │  FastAPI + Python
│  (Port 8000)│  
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

### Frontend Architecture

**Multi-Page Application (MPA)**:
- `index.html` - Search interface with 3D visualization
- `documents.html` - Document upload and management
- `files.html` - File organization with drag-and-drop

Pages communicate with the backend API and share a modular CSS architecture
### Tech Stack

**Backend:**
- FastAPI - Modern async web framework
- Qdrant - High-performance vector database (Dockerized)
- SentenceTransformers - State-of-the-art embeddings
- SQLite - Lightweight metadata storage

**Frontend:**
- Vanilla JavaScript (ES6+ modules)
- Modular CSS architecture (7 organized stylesheets)
- Three.js for 3D embedding visualization
- Fetch API for backend communication

**File Processing:**
- pypdf - PDF text extraction
- docx2txt - Word document parsing
- AST parser - Code-aware chunking

### CSS Architecture

The frontend uses:

- **base.css** - CSS variables, reset, body, container
- **animations.css** - Keyframe animations and transitions
- **components.css** - Buttons, cards, forms, tables
- **layout.css** - Page-specific layouts
- **filesystem.css** - File manager UI
- **batch-upload.css** - Batch upload queue card and status indicators
- **modals.css** - Modal overlays and notifications

## API Reference

### Core Endpoints

#### Upload Document
```http
POST /upload
Content-Type: multipart/form-data

Parameters:
- file: File (required)
- category: string (required)
- tags: string[] (optional)
- relative_path: string (optional) - Folder path for batch uploads (e.g., "projects/homework")

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
  "limit": 10,
  "cluster_filter": "0"  // Optional: filter by cluster ID
}

Response: {
  "results": [
    {
      "text": "chunk content",
      "score": 0.89,
      "metadata": {
        "cluster": 0,
        ...
      }
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
    "category": "CS101",
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
- `GET /files/content/{filename}` - Retrieve file content for viewing

### Clustering

```http
POST /api/cluster

Response: {
  "message": "Clustering complete",
  "total_documents": 150,
  "clusters": 5
}
# Automatically clusters all documents in the database
# Determines optimal number of clusters using silhouette score
```

```http
GET /api/clusters

Response: {
  "clusters": [0, 1, 2, 3, 4]
}
# Returns list of all cluster IDs currently assigned to documents
```

### Data Management

```http
GET /export

Response: application/zip
# Downloads a ZIP archive of all uploaded files
```

```http
DELETE /reset

Response: {
  "status": "success",
  "message": "All data has been reset"
}
# WARNING: Irreversibly deletes all data
```

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

### Frontend Can't Connect to Backend

If you see "Failed to fetch" errors in the browser console:

1. Verify backend is running on port 8000:
   ```bash
   curl http://127.0.0.1:8000/health
   ```

2. Check `frontend/config.js` uses `127.0.0.1` (not `localhost`):
   ```javascript
   const API_BASE_URL = 'http://127.0.0.1:8000';
   ```
   
This avoids IPv6/IPv4 resolution issues on some systems.

## Project Structure

```
database/
├── backend/
│   ├── extractors/          # File format parsers
│   │   ├── pdf_extractor.py
│   │   ├── docx_extractor.py
│   │   ├── text_extractor.py
│   │   └── code_extractor.py
│   ├── main.py             # FastAPI application
│   ├── vector_db.py        # Qdrant client
│   ├── embedding_service.py # Embedding generation
│   ├── ingestion.py        # File processing pipeline
│   ├── chunker.py          # Text chunking logic
│   ├── filesystem_db.py    # SQLite for folders
│   ├── dimensionality_reduction.py # PCA for 3D visualization
│   ├── config.py           # Configuration
│   └── exceptions.py       # Custom exceptions
├── frontend/
│   ├── css/                # Modular CSS architecture
│   │   ├── base.css       # Variables, reset, foundation
│   │   ├── animations.css # Keyframe animations
│   │   ├── components.css # Buttons, cards, forms
│   │   ├── layout.css     # Page layouts
│   │   ├── filesystem.css # File manager styles
│   │   ├── batch-upload.css # Batch upload queue styles
│   │   └── modals.css     # Overlays and notifications
│   ├── js/
│   │   └── embedding-visualizer.js  # 3D visualization module
│   ├── index.html          # Search page
│   ├── documents.html      # Upload & document management
│   ├── files.html          # File organization
│   ├── config.js           # API configuration
│   ├── search.js           # Search functionality
│   ├── upload.js           # File upload
│   ├── documents.js        # Document listing
│   ├── filesystem.js       # Folder management
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
