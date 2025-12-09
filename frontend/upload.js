/* =======================================================================
 * i3T4AN (Ethan Blair)
 * Project:      Vector Knowledge Base
 * File:         File upload functionality
 * ======================================================================= */

document.addEventListener('DOMContentLoaded', () => {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const folderInput = document.getElementById('folderInput');
    const uploadBtn = document.getElementById('uploadBtn');
    const categoryInput = document.getElementById('categoryInput');
    const uploadTags = document.getElementById('uploadTags');
    const uploadProgress = document.getElementById('uploadProgress');
    const progressFill = document.querySelector('.progress-fill');
    const uploadStatus = document.getElementById('uploadStatus');

    // Module-level allowed extensions (fetched from backend)
    let allowedExtensions = null;

    // Fetch allowed extensions from backend on load
    async function loadAllowedExtensions() {
        try {
            const response = await fetch(`${API_URL}/config/allowed-extensions`);
            if (response.ok) {
                const data = await response.json();
                allowedExtensions = new Set(data.extensions);
                console.log('Loaded allowed extensions from API:', allowedExtensions);
            }
        } catch (error) {
            console.warn('Failed to load allowed extensions from API, using fallback');
            // Fallback to hardcoded list if API fails
            allowedExtensions = new Set(['.pdf', '.docx', '.pptx', '.ppt', '.xlsx', '.csv', '.jpg', '.jpeg', '.png', '.webp', '.txt', '.md', '.py', '.js', '.java', '.cpp', '.html', '.css', '.json', '.xml', '.yaml', '.yml', '.cs']);
        }
    }

    // Load extensions immediately
    loadAllowedExtensions();

    // Drag & Drop Handlers

    const browseFilesBtn = document.getElementById('browseFilesBtn');
    const browseFolderBtn = document.getElementById('browseFolderBtn');

    if (browseFilesBtn) browseFilesBtn.addEventListener('click', () => fileInput.click());
    if (browseFolderBtn) browseFolderBtn.addEventListener('click', () => folderInput.click());

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });

    dropZone.addEventListener('drop', async (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');

        const items = e.dataTransfer.items;
        if (!items) {
            // Fallback for browsers without DataTransferItemList
            if (e.dataTransfer.files.length) {
                fileInput.files = e.dataTransfer.files;
                updateDropZoneText(e.dataTransfer.files[0].name);
            }
            return;
        }

        // Check if any item is a directory
        const entries = [];
        for (let i = 0; i < items.length; i++) {
            const entry = items[i].webkitGetAsEntry();
            if (entry) entries.push(entry);
        }

        // Traverse all entries and collect files with paths
        const filesWithPaths = await traverseFileTree(entries);

        if (filesWithPaths.length > 0) {
            // If only one file and it's at root, treat as normal single upload
            if (filesWithPaths.length === 1 && !filesWithPaths[0].folderPath) {
                const dt = new DataTransfer();
                dt.items.add(filesWithPaths[0].file);
                fileInput.files = dt.files;
                updateDropZoneText(filesWithPaths[0].file.name);
            } else {
                handleBatchUpload(filesWithPaths);
            }
        }
    });

    fileInput.addEventListener('change', () => {
        if (fileInput.files.length) {
            updateDropZoneText(`${fileInput.files.length} file(s) selected`);
        }
    });

    folderInput.addEventListener('change', () => {
        if (folderInput.files.length) {
            updateDropZoneText(`${folderInput.files.length} file(s) from folder selected`);
        }
    });

    function updateDropZoneText(filename) {
        const p = dropZone.querySelector('p');
        p.innerHTML = `Selected: <strong>${filename}</strong>`;
    }

    function showStatus(msg, type) {
        uploadStatus.textContent = msg;
        uploadStatus.className = 'status-msg';
        if (type === 'success') uploadStatus.classList.add('status-success');
        if (type === 'error') uploadStatus.classList.add('status-error');
    }

    // Upload button handler
    uploadBtn.addEventListener('click', async () => {
        const hasFiles = fileInput.files.length > 0;
        const hasFolder = folderInput.files.length > 0;

        if (!hasFiles && !hasFolder) {
            window.notifications.error('Please select files or a folder');
            return;
        }

        if (!categoryInput.value.trim()) {
            window.notifications.error('Please enter a category');
            return;
        }

        // Disable upload button to prevent double-clicks
        uploadBtn.disabled = true;

        // Process files for batch upload
        const filesWithPaths = [];

        // Process standard files
        if (hasFiles) {
            for (let i = 0; i < fileInput.files.length; i++) {
                const file = fileInput.files[i];
                filesWithPaths.push({
                    file: file,
                    relativePath: file.name,
                    folderPath: null
                });
            }
        }

        // Process folder files
        if (hasFolder) {
            for (let i = 0; i < folderInput.files.length; i++) {
                const file = folderInput.files[i];
                // webkitRelativePath example: "folder/sub/file.txt"
                const relativePath = file.webkitRelativePath || file.name;
                const folderPath = relativePath.includes('/') ? relativePath.substring(0, relativePath.lastIndexOf('/')) : null;

                filesWithPaths.push({
                    file: file,
                    relativePath: relativePath,
                    folderPath: folderPath
                });
            }
        }

        // Clear inputs immediately to allow new selection
        fileInput.value = '';
        folderInput.value = '';
        const p = dropZone.querySelector('p');
        p.innerHTML = 'Drag & Drop files here or <span class="browse-btn" id="browseFilesBtn">Browse Files</span> | <span class="browse-btn" id="browseFolderBtn">Browse Folder</span>';

        // Re-attach listeners
        document.getElementById('browseFilesBtn').addEventListener('click', () => fileInput.click());
        document.getElementById('browseFolderBtn').addEventListener('click', () => folderInput.click());

        // Use batch handler (await it to handle async properly)
        await handleBatchUpload(filesWithPaths);

        // Re-enable upload button
        uploadBtn.disabled = false;
    });
    // Export Data Handler
    const exportBtn = document.getElementById('exportBtn');
    if (exportBtn) {
        exportBtn.addEventListener('click', async () => {
            try {
                exportBtn.disabled = true;
                exportBtn.textContent = 'Exporting...';

                const response = await fetch(`${API_URL}/export`);

                if (!response.ok) {
                    throw new Error('Export failed');
                }

                // Trigger download
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'data_export.zip';
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);

                window.notifications.success('Data exported successfully');
            } catch (error) {
                window.notifications.error(`Export failed: ${error.message}`);
            } finally {
                exportBtn.disabled = false;
                exportBtn.textContent = 'Export Data';
            }
        });
    }

    // Delete Data Handler
    const deleteDataBtn = document.getElementById('deleteDataBtn');
    if (deleteDataBtn) {
        deleteDataBtn.addEventListener('click', async () => {
            if (!confirm('WARNING: This will permanently delete ALL uploaded documents and reset the database. This action cannot be undone. Are you sure?')) {
                return;
            }

            // Prompt for admin key (may be empty if not configured on server)
            const adminKey = prompt('Enter admin password (leave empty if not configured):');
            if (adminKey === null) return; // User cancelled

            try {
                deleteDataBtn.disabled = true;
                deleteDataBtn.textContent = 'Deleting...';

                const response = await fetch(`${API_URL}/reset`, {
                    method: 'DELETE',
                    headers: adminKey ? { 'X-Admin-Key': adminKey } : {}
                });

                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || 'Reset failed');
                }

                window.notifications.success('All data has been reset');

                // Refresh stats and lists
                if (window.documents) {
                    window.documents.refresh();
                }
                if (window.fileSystem) {
                    window.fileSystem.refresh();
                }

                // Update stats manually if needed
                document.getElementById('totalDocs').textContent = '0';
                document.getElementById('totalChunks').textContent = '0';

            } catch (error) {
                window.notifications.error(`Reset failed: ${error.message}`);
            } finally {
                deleteDataBtn.disabled = false;
                deleteDataBtn.textContent = 'Delete Data';
            }
        });
    }

    // ==========================================
    // Batch Upload & Folder Traversal Logic
    // ==========================================

    /**
     * Recursively traverse file system entries from drag-drop or file picker.
     * @param {FileSystemEntry[]} entries - Array of FileSystemEntry objects
     * @returns {Promise<Array<{file: File, relativePath: string, folderPath: string|null}>>}
     */
    async function traverseFileTree(entries) {
        const filesWithPaths = [];

        async function readEntry(entry, path = '') {
            if (entry.isFile) {
                return new Promise((resolve) => {
                    entry.file((file) => {
                        const relativePath = path ? `${path}/${file.name}` : file.name;
                        const folderPath = path || null; // null for root-level files

                        filesWithPaths.push({
                            file: file,
                            relativePath: relativePath,
                            folderPath: folderPath
                        });
                        resolve();
                    });
                });
            } else if (entry.isDirectory) {
                const dirReader = entry.createReader();
                return new Promise((resolve) => {
                    const readEntries = async () => {
                        dirReader.readEntries(async (entries) => {
                            if (entries.length === 0) {
                                resolve();
                            } else {
                                for (const childEntry of entries) {
                                    const newPath = path ? `${path}/${entry.name}` : entry.name;
                                    await readEntry(childEntry, newPath);
                                }
                                // Recursively call readEntries until empty (standard API behavior)
                                await readEntries();
                            }
                        });
                    };
                    readEntries();
                });
            }
        }

        for (const entry of entries) {
            await readEntry(entry);
        }

        return filesWithPaths;
    }

    /**
     * Process and upload a batch of files with their relative paths.
     * @param {Array<{file: File, relativePath: string, folderPath: string|null}>} filesWithPaths
     * @returns {Promise<void>}
     */
    async function handleBatchUpload(filesWithPaths) {
        // Ensure extensions are loaded
        if (!allowedExtensions) {
            await loadAllowedExtensions();
        }

        // Filter out incompatible files and show notifications
        const validFiles = [];

        for (const item of filesWithPaths) {
            const ext = '.' + item.file.name.split('.').pop().toLowerCase();
            if (!allowedExtensions.has(ext)) {
                window.notifications.error(`"${item.relativePath}" is not compatible to be embedded`);
                continue;
            }
            validFiles.push(item);
        }

        if (validFiles.length === 0) {
            window.notifications.error('No compatible files found in the batch');
            return;
        }

        // ========== NEW: GROUP FILES BY FOLDER PATH ==========
        const folderGroups = {};
        for (const item of validFiles) {
            const folderKey = item.folderPath || '__root__'; // Use '__root__' for files without folder
            if (!folderGroups[folderKey]) {
                folderGroups[folderKey] = [];
            }
            folderGroups[folderKey].push(item);
        }

        console.log(`Grouped ${validFiles.length} files into ${Object.keys(folderGroups).length} folder batches`);

        // Show batch queue card
        const batchCard = document.getElementById('batchQueueCard');
        const queueList = document.getElementById('queueList');
        const cancelBtn = document.getElementById('cancelBatchBtn');

        batchCard.style.display = 'flex';
        queueList.innerHTML = '';

        // Reset button state
        if (cancelBtn) {
            cancelBtn.textContent = 'Cancel All';
            cancelBtn.className = 'btn btn-danger';
            cancelBtn.onclick = () => {
                batchCard.style.display = 'none';
                window.notifications.warning('Batch upload cancelled');
            };
        }

        // Create queue items
        const queue = validFiles.map((item, index) => ({
            id: `queue-${Date.now()}-${index}`,
            ...item,
            status: 'pending' // pending, uploading, success, error
        }));

        // Render queue
        renderQueue(queue);
        updateQueueCounter(0, queue.length);

        // ========== UPLOAD FOLDER-GROUPED BATCHES ==========
        let completed = 0;

        for (const [folderKey, items] of Object.entries(folderGroups)) {
            // Check if cancelled (simple check via UI state)
            if (batchCard.style.display === 'none') break;

            const folderPath = folderKey === '__root__' ? null : folderKey;

            // Mark all items in this folder batch as uploading
            for (const item of items) {
                const queueItem = queue.find(q => q.file === item.file);
                if (queueItem) {
                    queueItem.status = 'uploading';
                    updateQueueItem(queueItem);
                }
            }

            try {
                // Upload entire folder batch at once
                const result = await uploadFolderBatch(items.map(i => i.file), folderPath);

                // Mark as success
                for (const item of items) {
                    const queueItem = queue.find(q => q.file === item.file);
                    if (queueItem) {
                        queueItem.status = 'success';
                        updateQueueItem(queueItem);
                        completed++;
                        updateQueueCounter(completed, queue.length);
                    }
                }
            } catch (error) {
                // Mark as error
                for (const item of items) {
                    const queueItem = queue.find(q => q.file === item.file);
                    if (queueItem) {
                        queueItem.status = 'error';
                        queueItem.error = error.message;
                        updateQueueItem(queueItem);
                    }
                }
            }
        }

        // Update button to "Done" when finished
        if (cancelBtn) {
            cancelBtn.textContent = 'Done';
            cancelBtn.className = 'btn btn-primary';
            cancelBtn.onclick = () => {
                batchCard.style.display = 'none';
            };
        }

        // Refresh lists after batch
        if (window.documents) window.documents.refresh();
        if (window.fileSystem) window.fileSystem.refresh();
    }

    function renderQueue(queue) {
        const queueList = document.getElementById('queueList');
        queueList.innerHTML = queue.map(item => `
            <div id="${item.id}" class="queue-item queue-${item.status}">
                <div class="queue-item-icon">📄</div>
                <div class="queue-item-content">
                    <div class="queue-item-path">${item.relativePath}</div>
                    <div class="queue-item-status">${item.status}</div>
                </div>
                <div class="queue-item-indicator"></div>
            </div>
        `).join('');
    }

    function updateQueueItem(item) {
        const element = document.getElementById(item.id);
        if (element) {
            element.className = `queue-item queue-${item.status}`;
            element.querySelector('.queue-item-status').textContent =
                item.status === 'error' ? item.error : item.status;
        }
    }

    function updateQueueCounter(completed, total) {
        document.getElementById('queueCounter').textContent = `${completed} / ${total}`;
    }

    async function uploadFolderBatch(files, folderPath) {
        const formData = new FormData();

        // Append all files
        for (const file of files) {
            formData.append('files', file);
        }

        // Append metadata
        formData.append('category', categoryInput.value.trim() || 'Batch Upload');

        if (uploadTags.value.trim()) {
            formData.append('tags', uploadTags.value.trim());
        }

        // Add relative_path if files are in a folder
        if (folderPath) {
            formData.append('relative_path', folderPath);
        }

        const response = await fetch(`${API_URL}/upload-batch`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Batch upload failed');
        }

        return await response.json();
    }

    // Note: Cancel batch button behavior is managed dynamically in handleBatchUpload()
});
