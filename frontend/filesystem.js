/* =======================================================================
 * i3T4AN (Ethan Blair)
 * Project:      Vector Knowledge Base
 * File:         File system and folder management
 * ======================================================================= */

// FileSystem class for managing folder hierarchy and file organization

if (typeof FileSystem === 'undefined') {
    class FileSystem {
        constructor() {
            this.currentFolderId = null; // null = Root
            this.folders = [];
            this.files = {}; // Map of folderId -> [filenames]
            this.unsortedFiles = [];
            this.breadcrumbs = [{ id: null, name: '<span class="purple-emoji">🏠</span> Home' }];
            this.isProcessingMove = false; // Flag to prevent duplicate moves
            this.draggedType = null; // Track what is being dragged ('file' or 'folder')

            this.init();
        }

        init() {
            // The newFolderBtn has an inline onclick handler, no need for programmatic listener

            // Initialize the view
            this.refresh();
        }

        async refresh() {
            try {
                // Fetch folder data
                const foldersResp = await fetch(`${API_URL}/folders`);
                this.folders = await foldersResp.json();

                // Fetch unsorted files
                const unsortedResp = await fetch(`${API_URL}/files/unsorted`);
                this.unsortedFiles = await unsortedResp.json();

                // Fetch files in folders
                const filesResp = await fetch(`${API_URL}/files/in_folders`);
                this.files = await filesResp.json();

                // Render the UI
                this.renderUnsortedFiles();
                this.renderFolderView();
                this.renderBreadcrumbs();
            } catch (error) {
                console.error('Error refreshing filesystem:', error);
                if (window.notifications) {
                    window.notifications.error('Failed to load file system');
                }
            }
        }

        renderUnsortedFiles() {
            let container = document.getElementById('unsortedFilesList');
            // Clone to remove old event listeners
            const newContainer = container.cloneNode(false);
            container.parentNode.replaceChild(newContainer, container);
            container = newContainer;

            // Make the unsorted container a drop zone
            // Passing FOLDER_UNSORTED string to distinguish from null (Root)
            this.makeDropZone(container, CONSTANTS.FOLDER_UNSORTED);

            if (this.unsortedFiles.length === 0) {
                container.innerHTML = '<p style="color: var(--text-muted); font-size: 0.875rem;">All files are organized! <span class="purple-emoji">🎉</span></p>';
                return;
            }

            this.unsortedFiles.forEach(file => {
                const item = document.createElement('div');
                item.className = 'unsorted-file-item';
                item.draggable = true;
                item.textContent = file.filename;

                // Drag start
                item.addEventListener('dragstart', (e) => {
                    e.dataTransfer.effectAllowed = 'move';
                    e.dataTransfer.setData('type', 'file');
                    e.dataTransfer.setData('document_id', file.document_id);
                    e.dataTransfer.setData('filename', file.filename);
                    this.draggedType = 'file';
                    item.classList.add('dragging');
                });

                item.addEventListener('dragend', () => {
                    this.draggedType = null;
                    item.classList.remove('dragging');
                });

                // Double-click to open file
                item.addEventListener('dblclick', () => {
                    this.openFileViewer(file.filename);
                });

                container.appendChild(item);
            });


        }

        renderFolderView() {
            let grid = document.getElementById('folderGrid');
            // Clone to remove old event listeners
            const newGrid = grid.cloneNode(false);
            grid.parentNode.replaceChild(newGrid, grid);
            grid = newGrid;

            // Get subfolders of current folder
            const subfolders = this.folders.filter(f => f.parent_id === this.currentFolderId);

            // Get files in current folder (handle null as FOLDER_NULL string from backend)
            const currentFolderKey = this.currentFolderId === null ? CONSTANTS.FOLDER_NULL : this.currentFolderId;
            const filesInFolder = this.files[currentFolderKey] || [];

            // Render subfolders
            subfolders.forEach(folder => {
                // Check if folder is empty (no subfolders AND no files)
                const childrenFolders = this.folders.filter(f => f.parent_id === folder.id);
                const childrenFiles = this.files[folder.id] || [];
                const isEmpty = childrenFolders.length === 0 && childrenFiles.length === 0;

                const item = this.createFolderElement(folder, isEmpty);
                grid.appendChild(item);
            });

            // Render files
            filesInFolder.forEach(file => {
                const item = this.createFileElement(file);
                grid.appendChild(item);
            });

            // Empty state
            if (subfolders.length === 0 && filesInFolder.length === 0) {
                grid.innerHTML = `
                <div class="empty-folder">
                    <p><span class="purple-emoji">📭</span> This folder is empty</p>
                    <small>Drag files here or create a subfolder</small>
                </div>
            `;
            }

            // Make grid a drop zone
            this.makeDropZone(grid, this.currentFolderId);
        }

        createFolderElement(folder, isEmpty) {
            const div = document.createElement('div');
            div.className = 'fs-item draggable';
            div.draggable = true;

            div.innerHTML = `
            <div class="fs-item-icon"><span class="purple-emoji">📁</span></div>
            <div class="fs-item-name">${folder.name}</div>
        `;

            // Double-click to enter folder
            div.addEventListener('dblclick', () => {
                this.enterFolder(folder.id, folder.name);
            });

            // Drag start
            div.addEventListener('dragstart', (e) => {
                e.dataTransfer.effectAllowed = 'move';
                e.dataTransfer.setData('type', 'folder');
                e.dataTransfer.setData('folder_id', folder.id);
                this.draggedType = 'folder';
                div.classList.add('dragging');
            });

            div.addEventListener('dragend', () => {
                this.draggedType = null;
                div.classList.remove('dragging');
            });

            // Drop zone for moving files/folders INTO this folder
            this.makeDropZone(div, folder.id);

            // Delete button for empty folders
            if (isEmpty) {
                const deleteBtn = document.createElement('button');
                deleteBtn.className = 'delete-folder-btn';
                deleteBtn.innerHTML = '×';
                deleteBtn.title = 'Delete empty folder';
                deleteBtn.onclick = (e) => {
                    e.stopPropagation(); // Prevent entering folder
                    this.deleteFolder(folder.id);
                };
                div.appendChild(deleteBtn);
            }

            return div;
        }

        createFileElement(file) {
            const div = document.createElement('div');
            div.className = 'fs-item draggable';
            div.draggable = true;

            div.innerHTML = `
            <div class="fs-item-icon"><span class="purple-emoji">📄</span></div>
            <div class="fs-item-name">${file.filename}</div>
        `;

            // Drag start
            div.addEventListener('dragstart', (e) => {
                e.dataTransfer.effectAllowed = 'move';
                e.dataTransfer.setData('type', 'file');
                e.dataTransfer.setData('document_id', file.document_id);
                e.dataTransfer.setData('filename', file.filename);
                this.draggedType = 'file';
                div.classList.add('dragging');
            });

            div.addEventListener('dragend', () => {
                this.draggedType = null;
                div.classList.remove('dragging');
            });

            // Double-click to open file
            div.addEventListener('dblclick', () => {
                this.openFileViewer(file.filename);
            });

            return div;
        }

        makeDropZone(element, targetFolderId) {
            element.addEventListener('dragover', (e) => {
                e.preventDefault();

                // Prevent folders from being dropped into Unsorted
                if (targetFolderId === CONSTANTS.FOLDER_UNSORTED && this.draggedType === 'folder') {
                    e.dataTransfer.dropEffect = 'none';
                    return;
                }

                e.dataTransfer.dropEffect = 'move';
                if (element.classList.contains('fs-item')) {
                    element.classList.add('drop-target');
                } else {
                    element.classList.add('active-drop-zone');
                }
            });

            element.addEventListener('dragleave', (e) => {
                if (element.classList.contains('fs-item')) {
                    element.classList.remove('drop-target');
                } else {
                    element.classList.remove('active-drop-zone');
                }
            });

            element.addEventListener('drop', async (e) => {
                e.preventDefault();
                e.stopPropagation(); // Prevent event bubbling

                if (element.classList.contains('fs-item')) {
                    element.classList.remove('drop-target');
                } else {
                    element.classList.remove('active-drop-zone');
                }

                // Prevent folders from being dropped into Unsorted
                if (targetFolderId === CONSTANTS.FOLDER_UNSORTED && this.draggedType === 'folder') {
                    return;
                }

                const type = e.dataTransfer.getData('type');

                if (type === 'file') {
                    const document_id = e.dataTransfer.getData('document_id');
                    const filename = e.dataTransfer.getData('filename');
                    await this.moveFile(document_id, filename, targetFolderId);
                } else if (type === 'folder') {
                    const folderId = e.dataTransfer.getData('folder_id');
                    await this.moveFolder(folderId, targetFolderId);
                }
            });
        }

        renderBreadcrumbs() {
            const nav = document.getElementById('breadcrumbs');
            nav.innerHTML = '';

            this.breadcrumbs.forEach((crumb, index) => {
                const link = document.createElement('a');
                link.href = '#';
                link.innerHTML = crumb.name;
                link.dataset.folderId = crumb.id;

                if (index < this.breadcrumbs.length - 1) {
                    link.addEventListener('click', (e) => {
                        e.preventDefault();
                        this.navigateToFolder(crumb.id, this.breadcrumbs.slice(0, index + 1));
                    });
                } else {
                    link.style.color = 'var(--text-primary)';
                    link.style.pointerEvents = 'none';
                }

                nav.appendChild(link);
            });
        }

        enterFolder(folderId, folderName) {
            this.currentFolderId = folderId;
            this.breadcrumbs.push({ id: folderId, name: folderName });
            this.renderFolderView();
            this.renderBreadcrumbs();
        }

        navigateToFolder(folderId, newBreadcrumbs) {
            this.currentFolderId = folderId;
            this.breadcrumbs = newBreadcrumbs;
            this.renderFolderView();
            this.renderBreadcrumbs();
        }

        openCreateFolderModal() {
            console.log('openCreateFolderModal called');
            const modal = document.getElementById('createFolderModal');
            const input = document.getElementById('newFolderNameInput');

            if (modal && input) {
                modal.style.display = 'flex';
                input.value = '';
                input.focus();

                // Handle Enter key
                input.onkeydown = (e) => {
                    if (e.key === 'Enter') this.confirmCreateFolder();
                    if (e.key === 'Escape') this.closeCreateFolderModal();
                };
            } else {
                console.error('Modal or input element not found!');
            }
        }

        closeCreateFolderModal() {
            const modal = document.getElementById('createFolderModal');
            if (modal) {
                modal.style.display = 'none';
            }
        }

        async confirmCreateFolder() {
            const input = document.getElementById('newFolderNameInput');
            const name = input ? input.value.trim() : '';

            if (!name) {
                if (typeof window.showNotification === 'function') {
                    window.showNotification('Please enter a folder name', 'error');
                } else {
                    alert('Please enter a folder name');
                }
                return;
            }

            try {
                const payload = {
                    name: name,
                    parent_id: this.currentFolderId
                };

                console.log('Creating folder with payload:', payload);

                const response = await fetch(`${API_URL}/folders`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                if (response.ok) {
                    this.closeCreateFolderModal();

                    if (typeof window.showNotification === 'function') {
                        window.showNotification('Folder created successfully!', 'success');
                    } else {
                        console.log('Folder created successfully!');
                    }

                    await this.refresh();
                } else {
                    const errorData = await response.json().catch(() => ({}));
                    throw new Error(errorData.detail || 'Failed to create folder');
                }
            } catch (error) {
                console.error('Error creating folder:', error);

                if (typeof window.showNotification === 'function') {
                    window.showNotification(`Error: ${error.message}`, 'error');
                } else {
                    alert(`Failed to create folder: ${error.message}`);
                }
            }
        }

        async moveFile(document_id, filename, targetFolderId) {
            // Prevent duplicate moves from stacked event listeners
            if (this.isProcessingMove) {
                console.log('Move already in progress, skipping duplicate');
                return;
            }

            this.isProcessingMove = true;

            try {
                const response = await fetch(`${API_URL}/files/move`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ document_id, filename, folder_id: targetFolderId })
                });

                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({}));
                    throw new Error(errorData.detail || 'Failed to move file');
                }

                // Ensure refresh completes before showing success
                await this.refresh();
                window.notifications.success(`Moved "${filename}" successfully!`);

            } catch (error) {
                console.error('Error moving file:', error);
                window.notifications.error(`Failed to move file: ${error.message}`);
                // Still try to refresh to sync state
                await this.refresh().catch(e => console.error('Refresh failed:', e));
            } finally {
                // Always reset the flag
                this.isProcessingMove = false;
            }
        }

        async moveFolder(folderId, targetParentId) {
            // Prevent moving a folder into itself or its descendants
            if (folderId === targetParentId) {
                window.notifications.error('Cannot move a folder into itself');
                return;
            }

            // Prevent duplicate moves from stacked event listeners
            if (this.isProcessingMove) {
                console.log('Move already in progress, skipping duplicate');
                return;
            }

            this.isProcessingMove = true;

            try {
                const response = await fetch(`${API_URL}/folders/${folderId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ parent_id: targetParentId })
                });

                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({}));
                    throw new Error(errorData.detail || 'Failed to move folder');
                }

                // Ensure refresh completes before showing success
                await this.refresh();
                window.notifications.success('Folder moved successfully!');

            } catch (error) {
                console.error('Error moving folder:', error);
                window.notifications.error(`Failed to move folder: ${error.message}`);
                // Still try to refresh to sync state
                await this.refresh().catch(e => console.error('Refresh failed:', e));
            } finally {
                // Always reset the flag
                this.isProcessingMove = false;
            }
        }

        async deleteFolder(folderId) {


            try {
                const response = await fetch(`${API_URL}/folders/${folderId}`, {
                    method: 'DELETE'
                });

                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({}));
                    throw new Error(errorData.detail || 'Failed to delete folder');
                }

                window.notifications.success('Folder deleted successfully');
                await this.refresh();

            } catch (error) {
                console.error('Error deleting folder:', error);
                window.notifications.error(`Failed to delete folder: ${error.message}`);
            }
        }
        openFileViewer(filename) {
            const modal = document.getElementById('fileViewerModal');
            const title = document.getElementById('fileViewerTitle');
            const frame = document.getElementById('fileViewerFrame');

            if (modal && title && frame) {
                title.textContent = filename;
                frame.src = `${API_URL}/files/content/${encodeURIComponent(filename)}`;
                modal.style.display = 'flex';
            }
        }

        closeFileViewer() {
            const modal = document.getElementById('fileViewerModal');
            const frame = document.getElementById('fileViewerFrame');
            if (modal) {
                modal.style.display = 'none';
                if (frame) frame.src = ''; // Clear source to stop loading/playing
            }
        }
    }
    window.FileSystem = FileSystem;
}

// Initialize filesystem when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.fileSystem = new FileSystem();
});
