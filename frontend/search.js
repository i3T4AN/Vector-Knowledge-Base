/* =======================================================================
 * i3T4AN (Ethan Blair)
 * Project:      Vector Knowledge Base
 * File:         Search functionality and results display
 * ======================================================================= */

// API_URL is defined in config.js

document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('searchInput');
    const searchBtn = document.getElementById('searchBtn');

    const dateStart = document.getElementById('dateStart');
    const dateEnd = document.getElementById('dateEnd');
    const limitFilter = document.getElementById('limitFilter');
    const clusterFilter = document.getElementById('cluster-filter');
    const resultsGrid = document.getElementById('resultsGrid');
    const loading = document.getElementById('loading');
    const resultCount = document.getElementById('resultCount');

    // Event Listeners
    searchBtn.addEventListener('click', performSearch);
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') performSearch();
    });

    // Clustering Button with Job Polling
    const clusterBtn = document.getElementById('clusterBtn');
    if (clusterBtn) {
        clusterBtn.addEventListener('click', async () => {
            clusterBtn.disabled = true;
            const originalText = clusterBtn.textContent;
            clusterBtn.textContent = 'Starting...';

            try {
                // Start the clustering job (returns immediately with job_id)
                const response = await fetch(`${API_URL}/api/cluster`, {
                    method: 'POST'
                });

                if (!response.ok) throw new Error('Failed to start clustering');

                const jobInfo = await response.json();
                const jobId = jobInfo.job_id;

                showNotification('Clustering job started. Processing in background...', 'info');
                clusterBtn.textContent = 'Clustering... 0%';

                // Poll for job status
                const result = await pollJobStatus(jobId, (progress) => {
                    clusterBtn.textContent = `Clustering... ${progress}%`;
                });

                // Job completed - show results
                if (result.error) {
                    throw new Error(result.error);
                }

                const jobResult = result.result || {};

                // Create a summary of cluster names if available
                let clusterSummary = '';
                if (jobResult.cluster_names) {
                    const names = Object.values(jobResult.cluster_names)
                        .filter(n => n !== 'Uncategorized')
                        .slice(0, 3); // Show top 3
                    if (names.length > 0) {
                        clusterSummary = `: "${names.join('", "')}"` + (Object.keys(jobResult.cluster_names).length > 4 ? '...' : '');
                    }
                }

                // Build notification message with fallbacks for undefined values
                const totalChunks = jobResult.total_chunks ?? 'unknown';
                const totalDocs = jobResult.total_documents ?? 'unknown';
                const numClusters = jobResult.clusters ?? 'unknown';

                showNotification(
                    `Clustered ${totalChunks} chunks from ${totalDocs} documents into ${numClusters} clusters${clusterSummary}`,
                    'success'
                );

                // Refresh cluster dropdown
                await loadClusters();

                // Refresh visualization if active
                if (window.embeddingVisualizer) {
                    await window.embeddingVisualizer.fetchAllEmbeddings3D();
                    window.embeddingVisualizer.renderCorpusPoints();
                }

            } catch (error) {
                console.error('Clustering error:', error);
                showNotification('Clustering failed: ' + error.message, 'error');
            } finally {
                clusterBtn.disabled = false;
                clusterBtn.textContent = originalText;
            }
        });
    }

    /**
     * Poll a job status endpoint until completion or failure.
     * @param {string} jobId - The job ID to poll
     * @param {function} onProgress - Callback for progress updates (receives progress %)
     * @returns {Promise<object>} - The final job result
     */
    async function pollJobStatus(jobId, onProgress) {
        const pollInterval = 500; // Poll every 500ms
        const maxPolls = 600; // Max 5 minutes (600 * 500ms)

        for (let i = 0; i < maxPolls; i++) {
            try {
                const response = await fetch(`${API_URL}/api/jobs/${jobId}`);
                if (!response.ok) throw new Error('Failed to get job status');

                const job = await response.json();

                // Update progress
                if (onProgress && job.progress !== undefined) {
                    onProgress(job.progress);
                }

                // Check if job is done
                if (job.status === 'completed') {
                    return job;
                } else if (job.status === 'failed') {
                    throw new Error(job.error || 'Job failed');
                }

                // Wait before next poll
                await new Promise(resolve => setTimeout(resolve, pollInterval));

            } catch (err) {
                console.error('Polling error:', err);
                throw err;
            }
        }

        throw new Error('Job timed out');
    }


    // Populate Cluster Dropdown
    if (clusterFilter) {
        loadClusters();

        // Sync with Visualizer
        clusterFilter.addEventListener('change', () => {
            if (window.embeddingVisualizer) {
                window.embeddingVisualizer.setClusterFilter(clusterFilter.value);
            }
        });
    }

    async function loadClusters() {
        if (!clusterFilter) return;

        try {
            const response = await fetch(`${API_URL}/api/clusters`);
            const data = await response.json();

            // Save current selection
            const currentSelection = clusterFilter.value;

            // Clear existing options except "All Clusters"
            // Assuming the first option is "All Clusters" with value "all" or ""
            // We'll rebuild from scratch but keep the first one if it's the default
            const defaultOption = clusterFilter.options[0];
            clusterFilter.innerHTML = '';
            if (defaultOption) clusterFilter.appendChild(defaultOption);

            if (data.clusters && data.clusters.length > 0) {
                // Sort clusters: numbered ones first, then -1 (Uncategorized) at the end
                const sortedClusters = data.clusters.sort((a, b) => {
                    if (a.id === -1) return 1;
                    if (b.id === -1) return -1;
                    return a.id - b.id;
                });

                sortedClusters.forEach(cluster => {
                    const option = document.createElement('option');
                    option.value = cluster.id;
                    if (cluster.id === -1) {
                        option.textContent = 'Uncategorized';
                    } else {
                        // Format: "1: Shakespeare & Drama"
                        option.textContent = `${cluster.id}: ${cluster.name}`;
                    }
                    clusterFilter.appendChild(option);
                });

                // Restore selection if it still exists
                if (currentSelection) {
                    const optionExists = Array.from(clusterFilter.options).some(opt => opt.value === currentSelection);
                    if (optionExists) {
                        clusterFilter.value = currentSelection;
                    }
                }
            }
        } catch (err) {
            console.error('Failed to load clusters:', err);
        }
    }

    async function performSearch() {
        const query = searchInput.value.trim();
        if (!query) return;

        // Show loading
        loading.style.display = 'block';
        resultsGrid.innerHTML = '';
        resultCount.textContent = '';

        // Prepare filters
        const filters = {};


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
                    filters: Object.keys(filters).length > 0 ? filters : null,
                    cluster_filter: clusterFilter ? clusterFilter.value : 'all'
                })
            });

            if (!response.ok) throw new Error('Search failed');

            const data = await response.json();

            // Update 3D visualization
            if (window.embeddingVisualizer) {
                // Don't await this to keep UI responsive
                const currentCluster = clusterFilter ? clusterFilter.value : 'all';
                window.embeddingVisualizer.fetchQueryEmbedding3D(query, currentCluster).then(visData => {
                    if (visData) {
                        window.embeddingVisualizer.renderQueryPoint(visData.queryCoords);
                        window.embeddingVisualizer.renderNeighborLines(visData.queryCoords, visData.neighbors);
                    }
                }).catch(err => console.error("Visualizer error:", err));
            }

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
                    ${result.metadata.tags && result.metadata.tags !== 'undefined' ? `<span class="meta-tag"><span class="purple-emoji">🏷️</span> ${escapeHtml(Array.isArray(result.metadata.tags) ? result.metadata.tags.join(', ') : result.metadata.tags)}</span>` : ''}
                    ${result.metadata.category && result.metadata.category !== 'undefined' ? `<span class="meta-tag"><span class="purple-emoji">📚</span> ${escapeHtml(result.metadata.category)}</span>` : ''}
                    ${(() => {
                    if (result.metadata.cluster === undefined || result.metadata.cluster === null) return '';

                    const clusterId = result.metadata.cluster;
                    if (clusterId === -1) return `<span class="meta-tag"><span class="purple-emoji">🔢</span> Uncategorized</span>`;

                    const name = result.metadata.cluster_name || '';
                    // Format: "🔢 Cluster 1: Shakespeare & Drama"
                    return `<span class="meta-tag"><span class="purple-emoji">🔢</span> Cluster ${clusterId}: ${escapeHtml(name)}</span>`;
                })()}
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
