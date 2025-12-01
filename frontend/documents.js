/* =======================================================================
 * i3T4AN (Ethan Blair)
 * Project:      Vector Knowledge Base
 * File:         Document management functionality
 * ======================================================================= */

document.addEventListener('DOMContentLoaded', () => {
    const docsTableBody = document.querySelector('#docsTable tbody');
    const totalDocsEl = document.getElementById('totalDocs');
    const totalChunksEl = document.getElementById('totalChunks');
    const refreshBtn = document.getElementById('refreshDocsBtn');
    // Load docs automatically on page load
    loadDocuments();

    refreshBtn.addEventListener('click', loadDocuments);

    async function loadDocuments() {
        console.log('Loading documents...');
        try {
            docsTableBody.innerHTML = '<tr><td colspan="6" style="text-align:center">Loading...</td></tr>';

            const response = await fetch(`${API_URL}/documents`);
            console.log('Response status:', response.status);

            if (!response.ok) throw new Error('Failed to fetch documents');

            const docs = await response.json();
            console.log('Docs loaded:', docs);

            renderTable(docs);
            updateStats(docs);

        } catch (error) {
            console.error('Error loading docs:', error);
            docsTableBody.innerHTML = `<tr><td colspan="6" style="text-align:center; color: var(--error-color)">Error: ${error.message}</td></tr>`;
        }
    }

    function renderTable(docs) {
        if (docs.length === 0) {
            docsTableBody.innerHTML = '<tr><td colspan="6" style="text-align:center">No documents found. Upload one!</td></tr>';
            return;
        }

        docsTableBody.innerHTML = docs.map(doc => `
            <tr>
                <td>${escapeHtml(doc.filename)}</td>
                <td>${escapeHtml(doc.metadata.category || '-')}</td>
                <td>${(doc.metadata.tags || []).join(', ') || '-'}</td>
                <td>${new Date(doc.upload_date * 1000).toLocaleDateString()}</td>
                <td>${doc.total_chunks || 0}</td>
                <td>
                    <button class="btn btn-danger" onclick="deleteDocument('${escapeHtml(doc.filename)}')">Delete</button>
                </td>
            </tr>
        `).join('');
    }

    function updateStats(docs) {
        totalDocsEl.textContent = docs.length;
        const totalChunks = docs.reduce((sum, doc) => sum + (doc.total_chunks || 0), 0);
        totalChunksEl.textContent = totalChunks;
    }

    // Expose delete function globally
    // Expose delete function globally
    window.deleteDocument = async (filename) => {
        console.log('Deleting:', filename);

        try {
            const response = await fetch(`${API_URL}/documents/${encodeURIComponent(filename)}`, {
                method: 'DELETE'
            });

            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || 'Delete failed');
            }

            console.log('Delete successful');
            // Trigger refresh
            document.getElementById('refreshDocsBtn').click();

        } catch (error) {
            console.error('Delete error:', error);
            alert(`Error deleting document: ${error.message}`);
        }
    };

    function escapeHtml(unsafe) {
        if (!unsafe) return '';
        return unsafe
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }
});
