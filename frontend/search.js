/* =======================================================================
 * i3T4AN (Ethan Blair)
 * Project:      Vector Knowledge Base
 * File:         Search functionality and results display
 * ======================================================================= */

// API_URL is defined in config.js

document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('searchInput');
    const searchBtn = document.getElementById('searchBtn');
    const extFilter = document.getElementById('extFilter');
    const dateStart = document.getElementById('dateStart');
    const dateEnd = document.getElementById('dateEnd');
    const limitFilter = document.getElementById('limitFilter');
    const resultsGrid = document.getElementById('resultsGrid');
    const loading = document.getElementById('loading');
    const resultCount = document.getElementById('resultCount');

    // Event Listeners
    searchBtn.addEventListener('click', performSearch);
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') performSearch();
    });

    async function performSearch() {
        const query = searchInput.value.trim();
        if (!query) return;

        // Show loading
        loading.style.display = 'block';
        resultsGrid.innerHTML = '';
        resultCount.textContent = '';

        // Prepare filters
        const filters = {};
        if (extFilter.value) filters.extension = extFilter.value;

        // Date Range
        if (dateStart.value || dateEnd.value) {
            filters.date_range = {};
            if (dateStart.value) {
                filters.date_range.gte = new Date(dateStart.value).getTime() / 1000;
            }
            if (dateEnd.value) {
                // Add 1 day to include the end date fully
                const endDate = new Date(dateEnd.value);
                endDate.setDate(endDate.getDate() + 1);
                filters.date_range.lte = endDate.getTime() / 1000;
            }
        }

        try {
            const response = await fetch(`${API_URL}/search`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    query: query,
                    limit: parseInt(limitFilter.value),
                    filters: Object.keys(filters).length > 0 ? filters : null
                })
            });

            if (!response.ok) throw new Error('Search failed');

            const data = await response.json();
            displayResults(data.results);
            resultCount.textContent = `Found ${data.count} results`;

        } catch (error) {
            console.error('Search error:', error);
            resultsGrid.innerHTML = `<div class="error">Search failed: ${error.message}</div>`;
        } finally {
            loading.style.display = 'none';
        }
    }

    function displayResults(results) {
        if (results.length === 0) {
            resultsGrid.innerHTML = '<div class="no-results">No results found. Try different keywords.</div>';
            return;
        }

        resultsGrid.innerHTML = results.map(result => {
            // Create a short description (snippet)
            const text = result.text || '';
            const snippet = text.length > 200 ? text.substring(0, 200) + '...' : text;

            return `
            <div class="result-card">
                <div class="result-header">
                    <div class="result-title">${escapeHtml(result.metadata.filename || 'Unknown Document')}</div>
                    <div class="result-score">${(result.score * 100).toFixed(1)}% match</div>
                </div>
                <div class="result-content">${escapeHtml(snippet)}</div>
                <div class="result-meta">
                    ${result.metadata.tags ? `<span class="meta-tag">🏷️ ${escapeHtml(Array.isArray(result.metadata.tags) ? result.metadata.tags.join(', ') : result.metadata.tags)}</span>` : ''}
                    ${result.metadata.course_name ? `<span class="meta-tag">📚 ${escapeHtml(result.metadata.course_name)}</span>` : ''}
                    ${result.metadata.document_type ? `<span class="meta-tag">📄 ${escapeHtml(result.metadata.document_type)}</span>` : ''}
                </div>
            </div>
        `}).join('');
    }

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
