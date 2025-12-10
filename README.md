# Vector Knowledge Base

*A personal semantic search engine for your documents and knowledge base*

[![Python](https://img.shields.io/badge/Python-3.11+-blue?style=flat-square)](https://www.python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat-square)](https://fastapi.tiangolo.com)
[![Qdrant](https://img.shields.io/badge/Qdrant-Vector_Database-DC244C?style=flat-square)](https://qdrant.tech)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

[Features](#features) • [Quick Start](#quick-start) • [Usage](#usage) • [Architecture](#architecture) • [API Reference](#api-reference) • [Configuration](#configuration) • [MCP Integration](#mcp-integration-ai-agents) • [Troubleshooting](#troubleshooting)

---

**Vector Knowledge Base** is a vector database application that transforms your documents into a searchable knowledge base using semantic search. Upload PDFs, Word documents, PowerPoint, Excel, images (with OCR), and code files, then search using natural language to find exactly what you need.

## Features

- **Semantic Search** - Find documents by meaning, not just keywords
- **Auto-Clustering** - Automatically organize documents into semantic clusters using HDBSCAN (density-based clustering)
- **Semantic Cluster Naming** - Clusters are automatically named using TF-IDF keyword extraction (e.g., "Shakespeare & Drama", "Python & Programming")
- **Cluster-Based Filtering** - Filter search results by document clusters for more focused searches
- **Batch Upload & Folder Preservation** - Drag and drop entire folders to upload, automatically preserving folder structure in your knowledge base
- **3D Embedding Visualization** - Interactive 3D visualization of your document embeddings using Three.js
- **Multi-Format Support** - PDF, DOCX, PPTX, XLSX, CSV, images (OCR), TXT, Markdown, and code files (Python, JavaScript, C#, etc.)
- **Intelligent Chunking** - AST-aware parsing for code, sentence-boundary awareness for prose
- **Folder Organization** - Drag-and-drop file management with custom folder hierarchy
- **File Viewer** - Double-click any file to preview it directly in the browser
- **Multi-Page Navigation** - Dedicated pages for search, documents, and file management
- **Data Management** - Export all data as ZIP or reset the entire database with one click
- **Modern UI** - Clean, responsive interface with dark mode and modular CSS architecture
- **Vector Embeddings** - Powered by SentenceTransformers (all-mpnet-base-v2, 768-dimensional embeddings)
- **High-Performance Search** - Qdrant vector database for sub-50ms search queries
- **O(1) Document Listing** - JSON-based document registry for instant document listing at any scale
- **AI Agent Integration (MCP)** - Connect Claude Desktop or other AI agents to search, create, and manage documents via Model Context Protocol

![Main Search Interface](screenshots/search-interface.png)
*Clean, modern dark-mode interface with semantic search and filtering options*

## Quick Start

### Prerequisites

- Docker and Docker Compose (recommended)
- **OR** Python 3.11+ and Docker (for Performance Mode or Manual Installation)

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

### Option 2: Performance Mode (GPU Acceleration)

For **significantly faster** embedding generation, run the backend natively with GPU support:

| Mode | Embedding Speed | Best For |
|------|----------------|----------|
| Docker (CPU) | ~18s per batch | Cross-platform compatibility |
| Native (Apple M1/M2/M3) | ~3s per batch (**6x faster**) | Mac with Apple Silicon |
| Native (NVIDIA CUDA) | ~1s per batch (**18x faster**) | Windows/Linux with NVIDIA GPU |

**Setup:**

1. **Start Qdrant and Frontend in Docker**
   ```bash
   docker-compose -f docker-compose.native.yml up -d
   # Or simply:
   docker-compose up -d qdrant frontend
   ```

2. **Run the backend natively**
   
   **macOS/Linux:**
   ```bash
   ./scripts/start-backend-native.sh
   ```
   
   **Windows:**
   ```batch
   scripts\start-backend-native.bat
   ```

The script will:
- Create a virtual environment
- Install dependencies
- Auto-detect your GPU (MPS for Apple Silicon, CUDA for NVIDIA)
- Start the backend with GPU acceleration

> [!NOTE]
> GPU acceleration requires PyTorch with MPS support (macOS 12.3+) or CUDA toolkit (Windows/Linux with NVIDIA).

**Deployment Options Summary:**

| Mode | Command | GPU | Speed | Use Case |
|------|---------|-----|-------|----------|
| Full Docker | `docker-compose up -d` | ❌ | ~18s/batch | Production, cross-platform |
| Native (Mac/Linux) | `./scripts/start-backend-native.sh` | ✅ | ~1-3s/batch | Development, large uploads |
| Native (Windows) | `scripts\start-backend-native.bat` | ✅ | ~1-3s/batch | Development, large uploads |

### Option 3: Manual Installation (Not Recommended)

For development or if you prefer not to use Docker for the backend:

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
2. Upload several documents first (clustering works best with 5+ documents)
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
┌─────────────┐     ┌─────────────┐
│   Backend   │ ←── │  MCP Server │  AI Agent Integration
│  (Port 8000)│     │  (/mcp)     │  (Claude Desktop, etc.)
└──────┬──────┘     └─────────────┘
       │
   ┌───┴────┬────────────┐
   ▼        ▼            ▼
┌──────┐ ┌──────┐ ┌──────────┐
│SQLite│ │Qdrant│ │Sentence  │
│(Meta)│ │(Vec) │ │Transform │
└──────┘ └──────┘ └──────────┘
         Port 6333
```

### Document Processing Pipeline

```
┌──────────┐    ┌───────────┐    ┌─────────┐    ┌──────────┐    ┌────────┐
│  Upload  │ -> │ Extractor │ -> │ Chunker │ -> │ Embedder │ -> │ Qdrant │
│  (File)  │    │  (Text)   │    │ (Chunks)│    │(Vectors) │    │ (Store)│
└──────────┘    └───────────┘    └─────────┘    └──────────┘    └────────┘
```

**How Chunks Relate to Documents:**
- Each uploaded file is processed by the appropriate **Extractor** to extract raw text
- The **Chunker** splits the text into smaller pieces (default: 500 tokens with 50-token overlap)
- Each chunk is converted to a 768-dimensional vector by the **Embedder** (SentenceTransformers)
- Chunks are stored in **Qdrant** with metadata linking them back to the original document
- A single document may produce 10-100+ chunks depending on its length
- Search queries match against individual chunks, but results show which document they came from

### Frontend Architecture

**Multi-Page Application (MPA)**:
- `index.html` - Search interface with 3D visualization
- `documents.html` - Document upload and management
- `files.html` - File organization with drag-and-drop

Pages communicate with the backend API and share a modular CSS architecture.

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

**Extractor Architecture:**

The application uses a factory pattern for modular file processing:

- **ExtractorFactory** - Routes files to appropriate extractors based on file extension
- **BaseExtractor** - Interface that all extractors implement with `extract(file_path) → str` method

**Specialized Extractors:**
- **PDFExtractor** - Uses `pypdf` for PDF text extraction
- **DocxExtractor** - Uses `docx2txt` for Word document parsing
- **PptxExtractor** - Uses `python-pptx` for PowerPoint presentations
- **XlsxExtractor** - Uses `openpyxl` for Excel spreadsheets with multi-sheet support
- **CsvExtractor** - Uses `pandas` for CSV file processing with configurable delimiters
- **ImageExtractor** - Uses `pytesseract` + `PIL` for OCR on images (.jpg, .jpeg, .png, .webp)
- **TextExtractor** - Handles plain text and Markdown files (.txt, .md)
- **CodeExtractor** - AST-aware parsing for Python code with function/class extraction
- **CsExtractor** - Dedicated C# file parsing with namespace and method detection

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
    "upload_date": 1705320000.0
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
- `GET /files/in_folders` - Get file-to-folder mappings
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
# Automatically determines optimal number of clusters using HDBSCAN density-based algorithm
```

```http
GET /api/clusters

Response: {
  "clusters": [0, 1, 2, 3, 4]
}
# Returns list of all cluster IDs currently assigned to documents
```

### 3D Visualization

```http
GET /api/embeddings/3d

Response: {
  "coords": [[x, y, z], ...],  // PCA-reduced 3D coordinates
  "point_ids": ["uuid1", ...],
  "metadata": [{"filename": "doc.pdf", ...}, ...]
}
# Returns 3D coordinates for all document chunks (cached for performance)
```

```http
POST /api/embeddings/3d/query
Content-Type: application/json

Body: {
  "query": "machine learning",
  "k": 5  // Number of nearest neighbors
}

Response: {
  "query_coords": [x, y, z],
  "neighbors": [{"id": "uuid", "coords": [x, y, z], "score": 0.89}, ...]
}
# Transforms a search query to 3D space and finds nearest neighbors
```

### Batch Upload

```http
POST /upload-batch
Content-Type: multipart/form-data

Parameters:
- files: File[] (required) - Multiple files to upload
- category: string (required)
- tags: string[] (optional)
- relative_path: string (optional) - Shared folder path for all files

Response: {
  "results": [...],  // Array of upload results
  "total": 10,
  "successful": 10,
  "failed": 0
}
# Optimized batch upload for files sharing the same folder
```

### Job Management

```http
GET /api/jobs

Response: {
  "jobs": [
    {"id": "uuid", "type": "clustering", "status": "completed", "progress": 100}
  ]
}
# List all background jobs (clustering, etc.)
```

```http
GET /api/jobs/{job_id}

Response: {
  "id": "uuid",
  "type": "clustering",
  "status": "running",
  "progress": 45,
  "created_at": "2024-01-15T10:30:00",
  "message": "Processing..."
}
# Get status of a specific background job
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

Create a `.env` file in the project root directory (copy from `.env.example`):

```env
# Qdrant Configuration
QDRANT_HOST=localhost        # Default: "localhost". Use "qdrant" when running in Docker Compose
QDRANT_PORT=6333             # Default: 6333
QDRANT_COLLECTION=vector_db  # Default: "vector_db"

# File Upload Settings
UPLOAD_DIR=uploads           # Default: "uploads" (relative to backend directory)
MAX_FILE_SIZE=52428800       # Default: 50MB (50 * 1024 * 1024 bytes)

# Embedding Model
EMBEDDING_MODEL=all-mpnet-base-v2  # Default: "all-mpnet-base-v2" (768-dimensional)

# Compute Device (for native mode)
DEVICE=auto                        # Options: "auto", "cpu", "cuda", "mps"
                                   # auto = detect best available (MPS > CUDA > CPU)

# Chunking Settings
CHUNK_SIZE=500               # Default: 500 characters per chunk
CHUNK_OVERLAP=50             # Default: 50 characters overlap between chunks

# Security
ADMIN_KEY=                   # Optional: protects /reset endpoint. Leave empty to disable.

# Rate Limiting (High defaults for personal use)
RATE_LIMIT_UPLOAD=1000/minute  # Default: 1000/minute (won't affect normal use)
RATE_LIMIT_SEARCH=1000/minute  # Default: 1000/minute
RATE_LIMIT_RESET=60/minute     # Default: 60/minute (stricter for destructive ops)
```

> [!NOTE]
> When using Docker Compose, `QDRANT_HOST` is automatically set to `qdrant` (the service name) in `docker-compose.yml`. You only need a `.env` file for manual installations or to override defaults.

## MCP Integration (AI Agents)

The Vector Knowledge Base includes built-in support for the **Model Context Protocol (MCP)**, allowing AI agents like Claude Desktop to interact with your knowledge base directly.

### Prerequisites

- **Node.js 18+** - Required for the MCP bridge
  - Download from [nodejs.org](https://nodejs.org/) (LTS recommended)
  - Or on macOS: `brew install node`

### Setting Up Claude Desktop

1. **Ensure the backend is running**
   ```bash
   # Docker mode
   docker-compose up -d
   
   # OR Native mode - macOS/Linux
   ./scripts/start-backend-native.sh
   
   # OR Native mode - Windows
   scripts\start-backend-native.bat
   ```

2. **Locate the Claude Desktop config file**
   - **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
   
   > [!TIP]
   > In Claude Desktop: **Claude → Settings → Developer → Edit Config**

3. **Add the MCP server configuration**
   
   Edit `claude_desktop_config.json`:
   ```json
   {
     "mcpServers": {
       "vector-knowledge-base": {
         "command": "npx",
         "args": ["-y", "mcp-remote", "http://localhost:8000/mcp"]
       }
     }
   }
   ```
   
   > [!NOTE]
   > On macOS, if `npx` is not in PATH, use the full path: `/usr/local/bin/npx`

4. **Restart Claude Desktop**
   - Fully quit (Cmd+Q / Alt+F4), don't just close the window
   - Reopen Claude Desktop
   - The MCP tools should now be available

### Using the Knowledge Base from Claude

Once connected, just ask Claude naturally:

| Example Prompt | Action |
|----------------|--------|
| "Search my knowledge base for machine learning" | Semantic search |
| "List all documents in my knowledge base" | List documents |
| "Show me the document clusters" | Get clusters |
| "Run auto-clustering on my documents" | Cluster documents |
| "Check if my vector database is healthy" | Health check |
| "Get 3D embedding data for cluster 1" | Visualization data |
| "Create a summary document with my notes" | Create text document |

![Claude Desktop MCP Demo](screenshots/claude-mcp-demo.png)

*Claude Desktop searching and listing documents via MCP integration*

### MCP Limitations

> [!IMPORTANT]
> Claude Desktop has limitations when interacting with the knowledge base via MCP.

**What Claude CAN do:**
- ✅ Search documents semantically
- ✅ List all documents and folders
- ✅ Delete documents by filename
- ✅ Run clustering and get cluster info
- ✅ Get 3D embedding coordinates for visualization
- ✅ Check system health
- ✅ **Create text documents** (.txt, .md, .json) - Claude can generate content and save it to your knowledge base

**What Claude CANNOT do:**
- ❌ **Upload binary files** - PDFs, Word docs, images require multipart uploads which MCP cannot provide (at least from what I found with Claude Desktop)
- ❌ **Access your filesystem** - Claude cannot read files from paths like `/Users/.../file.pdf`

**To upload files**, use one of these methods instead:
1. **Web interface** at `http://localhost:8001/documents.html`
2. **curl command**:
   ```bash
   curl -X POST http://localhost:8000/upload \
     -F "file=@/path/to/document.pdf" \
     -F "category=my-category"
   ```

### Available MCP Tools

| Tool | Description |
|------|-------------|
| `health_check` | Check if the API is running |
| `get_allowed_extensions` | Get list of supported file types |
| `search_documents` | Semantic search across all documents |
| `list_documents` | List all uploaded documents |
| `delete_document` | Delete a document by filename |
| `get_folders` | List folder structure |
| `create_folder` | Create a new folder |
| `update_folder` | Rename or move a folder |
| `delete_folder` | Delete an empty folder |
| `move_file` | Move file to folder |
| `get_unsorted_files` | List files not in any folder |
| `get_files_in_folders` | Get file-to-folder mappings |
| `cluster_documents` | Run auto-clustering |
| `get_clusters` | Get cluster information |
| `get_embeddings_3d` | Get 3D visualization coordinates |
| `transform_query_3d` | Project query into 3D space |
| `get_job_status` | Check background job progress |
| `mcp_create_document` | Create text documents (.txt, .md, .json) |

> [!TIP]
> Claude can create searchable text documents using `mcp_create_document`. Ask it to "create a summary", "write notes", or "save a document" and it will add the content to your knowledge base.

### MCP Configuration

MCP settings are configured in [config.py](backend/config.py#L95-L111) (not in `.env`):

```env
MCP_ENABLED=true                    # Enable/disable MCP endpoint
MCP_PATH=/mcp                       # URL path for MCP server
MCP_NAME=Vector Knowledge Base      # Display name
MCP_AUTH_ENABLED=false              # Enable OAuth (production)
```

### Troubleshooting MCP

**"Server disconnected" error in Claude Desktop:**
1. Ensure the backend is running: `curl http://localhost:8000/health`
2. Check that Node.js is installed: `node --version`
3. Try the full path to npx: `/usr/local/bin/npx`

**MCP tools not appearing:**
1. Fully quit and reopen Claude Desktop
2. Check the Claude Desktop logs for errors
3. Verify the config JSON is valid (no trailing commas)

> [!CAUTION]
> MCP provides AI agents with full access to your knowledge base. In production environments, enable `MCP_AUTH_ENABLED=true` for OAuth protection.

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
- Documents: `.pdf`, `.docx`, `.pptx`, `.ppt`, `.xlsx`, `.csv`, `.txt`, `.md`
- Images: `.jpg`, `.jpeg`, `.png`, `.webp` (OCR-processed)
- Code: `.py`, `.js`, `.java`, `.cpp`, `.html`, `.css`, `.json`, `.xml`, `.yaml`, `.yml`, `.cs`

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
Vector-Knowledge-Base/
├── backend/
│   ├── extractors/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── factory.py
│   │   ├── pdf_extractor.py
│   │   ├── docx_extractor.py
│   │   ├── pptx_extractor.py
│   │   ├── xlsx_extractor.py
│   │   ├── csv_extractor.py
│   │   ├── text_extractor.py
│   │   ├── code_extractor.py
│   │   ├── cs_extractor.py
│   │   └── image_extractor.py
│   ├── uploads/          # Uploaded files (gitignored except .gitkeep)
│   │   └── .gitkeep
│   ├── data/             # Runtime data (auto-created)
│   │   └── documents.json  # Document registry for O(1) listing
│   ├── main.py
│   ├── vector_db.py
│   ├── embedding_service.py
│   ├── ingestion.py
│   ├── chunker.py
│   ├── clustering.py
│   ├── filesystem_db.py
│   ├── document_registry.py  # O(1) document listing registry
│   ├── dimensionality_reduction.py
│   ├── jobs.py           # Background task tracking
│   ├── config.py
│   ├── constants.py      # Shared constants
│   ├── mcp_server.py     # MCP server integration
│   └── exceptions.py
├── frontend/
│   ├── css/
│   │   ├── base.css
│   │   ├── animations.css
│   │   ├── components.css
│   │   ├── layout.css
│   │   ├── filesystem.css
│   │   ├── batch-upload.css
│   │   └── modals.css
│   ├── js/
│   │   └── embedding-visualizer.js
│   ├── index.html
│   ├── documents.html
│   ├── files.html
│   ├── config.js
│   ├── constants.js
│   ├── search.js
│   ├── upload.js
│   ├── documents.js
│   ├── filesystem.js
│   ├── notifications.js
│   └── favicon.ico
├── scripts/
│   ├── start-backend-native.sh   # GPU mode startup (Unix)
│   └── start-backend-native.bat  # GPU mode startup (Windows)
├── screenshots/
├── qdrant_storage/       # Created at runtime (gitignored)
├── uploads/              # Created at runtime by Docker (gitignored)
├── backend_db/           # Created at runtime (gitignored)
├── Dockerfile
├── docker-compose.yml          # Full Docker deployment
├── docker-compose.native.yml   # Native backend mode
├── nginx.conf
├── requirements.txt
├── requirements.in
├── LICENSE
└── README.md
```

## Performance

- **Upload**: ~2-5 seconds for typical PDF
- **Search**: 100-500ms depending on corpus size (sub-50ms for <10k vectors)
- **Embedding**: ~50-100ms per chunk
- **Capacity**: Scales to 100k+ documents with Qdrant

---

Built with ❤️ using FastAPI, Qdrant, and SentenceTransformers
