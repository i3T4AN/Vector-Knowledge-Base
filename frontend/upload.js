/* =======================================================================
 * i3T4AN (Ethan Blair)
 * Project:      Vector Knowledge Base
 * File:         File upload functionality
 * ======================================================================= */

document.addEventListener('DOMContentLoaded', () => {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const uploadBtn = document.getElementById('uploadBtn');
    const courseName = document.getElementById('courseName');
    const uploadTags = document.getElementById('uploadTags');
    const uploadProgress = document.getElementById('uploadProgress');
    const progressFill = document.querySelector('.progress-fill');
    const uploadStatus = document.getElementById('uploadStatus');

    // Drag & Drop Handlers
    dropZone.addEventListener('click', () => fileInput.click());

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        if (e.dataTransfer.files.length) {
            fileInput.files = e.dataTransfer.files;
            updateDropZoneText(e.dataTransfer.files[0].name);
        }
    });

    fileInput.addEventListener('change', () => {
        if (fileInput.files.length) {
            updateDropZoneText(fileInput.files[0].name);
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
        if (!fileInput.files.length) {
            window.notifications.error('Please select a file');
            return;
        }

        if (!courseName.value.trim()) {
            window.notifications.error('Please enter a description');
            return;
        }

        const file = fileInput.files[0];
        const formData = new FormData();
        formData.append('file', file);
        formData.append('course_name', courseName.value.trim());

        if (uploadTags.value.trim()) {
            formData.append('tags', uploadTags.value.trim());
        }

        try {
            uploadProgress.style.display = 'block';
            progressFill.style.width = '0%';
            uploadBtn.disabled = true;

            const response = await fetch(`${API_URL}/upload`, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Upload failed');
            }

            const result = await response.json();
            progressFill.style.width = '100%';

            window.notifications.success(`Uploaded successfully! ${result.chunks_count} chunks created.`);

            // Reset form
            fileInput.value = '';
            courseName.value = '';
            uploadTags.value = '';
            const p = dropZone.querySelector('p');
            p.innerHTML = 'Drag & Drop files here or <span class="browse-btn">Browse</span>';

            setTimeout(() => {
                uploadProgress.style.display = 'none';
                progressFill.style.width = '0%';
            }, 2000);

        } catch (error) {
            window.notifications.error(`Upload failed: ${error.message}`);
            uploadProgress.style.display = 'none';
        } finally {
            uploadBtn.disabled = false;
        }
    });
});
