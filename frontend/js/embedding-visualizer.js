/* =======================================================================
 * i3T4AN (Ethan Blair)
 * Project:      Vector Knowledge Base
 * File:         3D Embedding Visualizer
 * ======================================================================= */

import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

export class EmbeddingVisualizer {
    constructor(container, options = {}) {
        if (!container) {
            console.error("EmbeddingVisualizer: Container element is required");
            return;
        }

        this.container = container;
        this.baseUrl = options.baseUrl || 'http://127.0.0.1:8000'; // Default to 8000 matching backend
        this.onLoad = options.onLoad || (() => { });
        this.onError = options.onError || ((err) => console.error(err));

        this.width = container.clientWidth;
        this.height = container.clientHeight;

        // Data state
        this.corpusPoints = [];
        this.queryPoint = null;
        this.neighbors = [];
        this.cameraLine = null; // Line from camera to query point
        this.isLoading = false;
        this.currentClusterFilter = 'all';

        // Scene setup
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0x111111); // Dark background

        // Camera setup
        this.camera = new THREE.PerspectiveCamera(75, this.width / this.height, 0.1, 1000);
        this.camera.position.set(3, 3, 3);
        this.camera.lookAt(0, 0, 0);

        // Renderer setup
        this.renderer = new THREE.WebGLRenderer({ antialias: true });
        this.renderer.setSize(this.width, this.height);
        this.renderer.setPixelRatio(window.devicePixelRatio);
        this.container.appendChild(this.renderer.domElement);

        // Controls
        this.controls = new OrbitControls(this.camera, this.renderer.domElement);
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.05;

        // Lighting
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
        this.scene.add(ambientLight);

        const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
        directionalLight.position.set(5, 10, 7);
        this.scene.add(directionalLight);

        // Bind methods
        this.animate = this.animate.bind(this);
        this.raycaster = new THREE.Raycaster();
        this.mouse = new THREE.Vector2();
        this.hoveredPoint = null;

        // Tooltip
        this.tooltip = document.getElementById('visualizer-tooltip');

        // Bind events
        this.onWindowResize = this.onWindowResize.bind(this);
        this.onMouseMove = this.onMouseMove.bind(this);

        // Event listeners
        window.addEventListener('resize', this.onWindowResize);
        this.container.addEventListener('mousemove', this.onMouseMove);

        // Start loop
        this.animate();

        console.log("EmbeddingVisualizer initialized");
    }

    setClusterFilter(clusterFilter) {
        this.currentClusterFilter = clusterFilter;
        // Re-fetch or re-render?
        // If we want to filter existing points without re-fetching, we can do that if we have all points.
        // But the backend now supports filtering, which might be better for large datasets.
        // However, for smooth UX, if we already have all points, we can just filter client-side.
        // Let's try client-side filtering first if we have data, otherwise fetch.
        // Actually, the plan said "Modify fetchAllEmbeddings3D to accept an optional cluster filter parameter".
        // Let's do that to be consistent with the plan and scalable.
        this.fetchAllEmbeddings3D(clusterFilter).then(() => {
            this.renderCorpusPoints();
        });
    }

    async fetchAllEmbeddings3D(clusterFilter = null) {
        this.isLoading = true;
        // Use instance filter if not provided
        const filter = clusterFilter !== null ? clusterFilter : this.currentClusterFilter;

        try {
            const url = filter === 'all' || !filter
                ? `${this.baseUrl}/api/embeddings/3d`
                : `${this.baseUrl}/api/embeddings/3d?cluster=${filter}`;

            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`Failed to fetch embeddings: ${response.statusText}`);
            }

            const data = await response.json();
            this.corpusPoints = data.points || [];
            this.onLoad(this.corpusPoints);
            return this.corpusPoints;
        } catch (error) {
            this.onError(error);
            return [];
        } finally {
            this.isLoading = false;
        }
    }

    async fetchQueryEmbedding3D(queryText, clusterFilter = null) {
        this.isLoading = true;
        // Use instance filter if not provided
        const filter = clusterFilter !== null ? clusterFilter : this.currentClusterFilter;

        try {
            const response = await fetch(`${this.baseUrl}/api/embeddings/3d/query`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    query: queryText,
                    cluster_filter: filter
                })
            });

            if (!response.ok) {
                throw new Error(`Failed to fetch query embedding: ${response.statusText}`);
            }

            const data = await response.json();
            this.queryPoint = data.query_coordinates;
            this.neighbors = data.top_k_neighbors || [];

            return {
                queryCoords: this.queryPoint,
                neighbors: this.neighbors
            };
        } catch (error) {
            this.onError(error);
            return null;
        } finally {
            this.isLoading = false;
        }
    }

    renderCorpusPoints() {
        if (!this.corpusPoints || this.corpusPoints.length === 0) return;

        // Clear existing points
        if (this.corpusMesh) {
            this.scene.remove(this.corpusMesh);
            this.corpusMesh.geometry.dispose();
            this.corpusMesh.material.dispose();
            this.corpusMesh = null;
        }

        const geometry = new THREE.SphereGeometry(0.05, 16, 16);
        const material = new THREE.MeshStandardMaterial({
            color: 0xffffff,
            roughness: 0.5,
            metalness: 0.1
        });

        const count = this.corpusPoints.length;
        this.corpusMesh = new THREE.InstancedMesh(geometry, material, count);
        this.corpusMesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);

        const dummy = new THREE.Object3D();
        const color = new THREE.Color();

        // Calculate bounds for auto-scaling
        const bounds = {
            minX: Infinity, maxX: -Infinity,
            minY: Infinity, maxY: -Infinity,
            minZ: Infinity, maxZ: -Infinity
        };

        // First pass: Calculate initial bounds
        for (let i = 0; i < count; i++) {
            const point = this.corpusPoints[i];
            const [x, y, z] = point.coordinates;

            bounds.minX = Math.min(bounds.minX, x);
            bounds.maxX = Math.max(bounds.maxX, x);
            bounds.minY = Math.min(bounds.minY, y);
            bounds.maxY = Math.max(bounds.maxY, y);
            bounds.minZ = Math.min(bounds.minZ, z);
            bounds.maxZ = Math.max(bounds.maxZ, z);
        }

        // Calculate adaptive scaling
        const currentRangeX = bounds.maxX - bounds.minX;
        const currentRangeY = bounds.maxY - bounds.minY;
        const currentRangeZ = bounds.maxZ - bounds.minZ;
        const currentMaxRange = Math.max(currentRangeX, currentRangeY, currentRangeZ);

        const pointDiameter = 0.05 * 2;
        const safetyMargin = 0.02;
        const minSpacing = pointDiameter + safetyMargin;
        const targetRange = Math.sqrt(count) * minSpacing;

        const scaleFactor = currentMaxRange > 0 ? targetRange / currentMaxRange : 1.0;

        // Center point for scaling
        const originX = (bounds.minX + bounds.maxX) / 2;
        const originY = (bounds.minY + bounds.maxY) / 2;
        const originZ = (bounds.minZ + bounds.maxZ) / 2;

        // Save scaling params for query/neighbor rendering
        this.scalingParams = { originX, originY, originZ, scaleFactor };

        // Reset bounds for scaled points
        bounds.minX = Infinity; bounds.maxX = -Infinity;
        bounds.minY = Infinity; bounds.maxY = -Infinity;
        bounds.minZ = Infinity; bounds.maxZ = -Infinity;

        // Second pass: Apply scaling and set positions
        for (let i = 0; i < count; i++) {
            const point = this.corpusPoints[i];
            const [x, y, z] = point.coordinates;

            // Scale from center
            const scaledX = (x - originX) * scaleFactor + originX;
            const scaledY = (y - originY) * scaleFactor + originY;
            const scaledZ = (z - originZ) * scaleFactor + originZ;

            // Update bounds with scaled coordinates
            bounds.minX = Math.min(bounds.minX, scaledX);
            bounds.maxX = Math.max(bounds.maxX, scaledX);
            bounds.minY = Math.min(bounds.minY, scaledY);
            bounds.maxY = Math.max(bounds.maxY, scaledY);
            bounds.minZ = Math.min(bounds.minZ, scaledZ);
            bounds.maxZ = Math.max(bounds.maxZ, scaledZ);

            dummy.position.set(scaledX, scaledY, scaledZ);
            dummy.updateMatrix();
            this.corpusMesh.setMatrixAt(i, dummy.matrix);

            // Color based on cluster or default
            if (point.cluster !== undefined && point.cluster !== null) {
                // Generate color from cluster ID (simple HSL)
                const hue = (point.cluster * 137.5) % 360;
                color.setHSL(hue / 360, 0.7, 0.5);
            } else {
                color.setHex(0x4488ff); // Default blue
            }
            this.corpusMesh.setColorAt(i, color);
        }

        this.corpusMesh.instanceMatrix.needsUpdate = true;
        if (this.corpusMesh.instanceColor) this.corpusMesh.instanceColor.needsUpdate = true;

        this.scene.add(this.corpusMesh);

        // Auto-scale camera to fit
        // Simple approximation: center camera and move back
        const centerX = (bounds.minX + bounds.maxX) / 2;
        const centerY = (bounds.minY + bounds.maxY) / 2;
        const centerZ = (bounds.minZ + bounds.maxZ) / 2;

        const maxDim = Math.max(
            bounds.maxX - bounds.minX,
            bounds.maxY - bounds.minY,
            bounds.maxZ - bounds.minZ
        );

        // Position camera
        // Distance needed to see maxDim with fov
        const fov = this.camera.fov * (Math.PI / 180);
        let cameraZ = Math.abs(maxDim / 2 / Math.tan(fov / 2));
        cameraZ *= 1.5; // Zoomed out slightly (padding)

        // Smoothly move camera if desired, but for now just set it
        // We'll keep the angle but adjust distance
        const currentPos = this.camera.position.clone();

        // If current distance is very different, adjust
        this.controls.target.set(centerX, centerY, centerZ);

        // Adjust camera position to be at reasonable distance
        // Maintain direction
        const direction = currentPos.sub(this.controls.target).normalize();
        if (direction.lengthSq() < 0.001) direction.set(0, 0, 1); // Fallback

        this.camera.position.copy(this.controls.target).add(direction.multiplyScalar(Math.max(cameraZ, 0.1)));

        this.controls.update();
    }

    clearQuery() {
        if (this.queryMesh) {
            this.scene.remove(this.queryMesh);
            this.queryMesh.geometry.dispose();
            this.queryMesh.material.dispose();
            this.queryMesh = null;
        }

        if (this.neighborLines) {
            this.scene.remove(this.neighborLines);
            this.neighborLines.geometry.dispose();
            this.neighborLines.material.dispose();
            this.neighborLines = null;
        }

        if (this.cameraLine) {
            this.scene.remove(this.cameraLine);
            this.cameraLine.geometry.dispose();
            this.cameraLine.material.dispose();
            this.cameraLine = null;
        }
    }

    renderQueryPoint(coordinates) {
        this.clearQuery();

        if (!coordinates) return;

        let [x, y, z] = coordinates;

        // Apply scaling if available
        if (this.scalingParams) {
            const { originX, originY, originZ, scaleFactor } = this.scalingParams;
            x = (x - originX) * scaleFactor + originX;
            y = (y - originY) * scaleFactor + originY;
            z = (z - originZ) * scaleFactor + originZ;
        }

        const geometry = new THREE.SphereGeometry(0.08, 16, 16);
        const material = new THREE.MeshStandardMaterial({
            color: 0xffaa00, // Gold/Yellow
            emissive: 0x442200,
            roughness: 0.3,
            metalness: 0.8
        });

        this.queryMesh = new THREE.Mesh(geometry, material);
        this.queryMesh.position.set(x, y, z);

        this.scene.add(this.queryMesh);

        // Add guide line from camera to query point
        const lineGeometry = new THREE.BufferGeometry().setFromPoints([
            this.camera.position,
            this.queryMesh.position
        ]);

        const lineMaterial = new THREE.LineBasicMaterial({
            color: 0xffff00, // Neon Yellow
            opacity: 0.8,
            linewidth: 2,
            transparent: true
        });

        this.cameraLine = new THREE.Line(lineGeometry, lineMaterial);
        this.scene.add(this.cameraLine);
    }

    renderNeighborLines(queryCoords, neighbors) {
        if (!queryCoords || !neighbors || neighbors.length === 0) return;

        const positions = [];
        const colors = [];
        let [qx, qy, qz] = queryCoords;

        // Apply scaling to query point
        if (this.scalingParams) {
            const { originX, originY, originZ, scaleFactor } = this.scalingParams;
            qx = (qx - originX) * scaleFactor + originX;
            qy = (qy - originY) * scaleFactor + originY;
            qz = (qz - originZ) * scaleFactor + originZ;
        }

        // Color gradient: Red (low sim) -> Green (high sim)
        const colorHigh = new THREE.Color(0x00ff00);
        const colorLow = new THREE.Color(0xff0000);

        neighbors.forEach(neighbor => {
            if (!neighbor.coordinates) return;

            let [nx, ny, nz] = neighbor.coordinates;

            // Apply scaling to neighbor point
            if (this.scalingParams) {
                const { originX, originY, originZ, scaleFactor } = this.scalingParams;
                nx = (nx - originX) * scaleFactor + originX;
                ny = (ny - originY) * scaleFactor + originY;
                nz = (nz - originZ) * scaleFactor + originZ;
            }

            // Add line segment
            positions.push(qx, qy, qz);
            positions.push(nx, ny, nz);

            // Calculate color based on similarity (assuming 0-1 range, or close to it)
            // Cosine similarity is usually -1 to 1, but for embeddings usually 0-1 or 0.5-1
            // Let's assume 0.5 to 1.0 mapping to Red->Green
            let score = neighbor.similarity || 0;
            // Normalize score for visualization if needed. 
            // Often scores are like 0.7-0.9. Let's map 0.6->1.0 to 0->1
            const normalizedScore = Math.max(0, Math.min(1, (score - 0.6) / 0.4));

            const color = colorLow.clone().lerp(colorHigh, normalizedScore);

            // Push color for both vertices of the line segment
            colors.push(color.r, color.g, color.b);
            colors.push(color.r, color.g, color.b);
        });

        const geometry = new THREE.BufferGeometry();
        geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
        geometry.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));

        const material = new THREE.LineBasicMaterial({
            vertexColors: true,
            transparent: true,
            opacity: 0.8,
            linewidth: 2 // Note: linewidth only works in WebGL2 or some browsers
        });

        this.neighborLines = new THREE.LineSegments(geometry, material);
        this.scene.add(this.neighborLines);
    }

    onMouseMove(event) {
        event.preventDefault();

        const rect = this.container.getBoundingClientRect();
        this.mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
        this.mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

        this.checkIntersection(event.clientX, event.clientY);
    }

    checkIntersection(clientX, clientY) {
        this.raycaster.setFromCamera(this.mouse, this.camera);

        let hit = null;

        // Check query point first (priority)
        if (this.queryMesh) {
            const queryIntersects = this.raycaster.intersectObject(this.queryMesh);
            if (queryIntersects.length > 0) {
                hit = {
                    point: { filename: "Query", id: "query", coordinates: this.queryPoint },
                    object: this.queryMesh
                };
            }
        }

        // Check corpus points if no query hit
        if (!hit && this.corpusMesh) {
            const corpusIntersects = this.raycaster.intersectObject(this.corpusMesh);
            if (corpusIntersects.length > 0) {
                const instanceId = corpusIntersects[0].instanceId;
                if (instanceId !== undefined && this.corpusPoints[instanceId]) {
                    hit = {
                        point: this.corpusPoints[instanceId],
                        object: this.corpusMesh,
                        instanceId: instanceId
                    };
                }
            }
        }

        if (hit) {
            this.showTooltip(hit.point, clientX, clientY);
            this.highlightPoint(hit);
        } else {
            this.hideTooltip();
            this.resetHighlight();
        }
    }

    showTooltip(point, x, y) {
        if (!this.tooltip) return;

        const filename = point.filename || 'Unknown';
        const id = point.id || 'N/A';
        const cluster = point.cluster !== undefined ? `Cluster: ${point.cluster}` : '';

        this.tooltip.innerHTML = `
            <div style="font-weight: 600; margin-bottom: 4px;">${filename}</div>
            <div style="font-size: 0.75rem; opacity: 0.8;">ID: ${id.substring(0, 8)}...</div>
            ${cluster ? `<div style="font-size: 0.75rem; color: #818cf8;">${cluster}</div>` : ''}
        `;

        this.tooltip.style.display = 'block';

        // Position relative to viewport, but we need to account for container
        // Actually, tooltip is inside container which is relative.
        // So we need coordinates relative to container.
        const rect = this.container.getBoundingClientRect();
        const relX = x - rect.left;
        const relY = y - rect.top;

        // Offset
        this.tooltip.style.left = `${relX + 15}px`;
        this.tooltip.style.top = `${relY + 15}px`;
    }

    hideTooltip() {
        if (this.tooltip) {
            this.tooltip.style.display = 'none';
        }
    }

    highlightPoint(hit) {
        // For now, just change cursor
        this.container.style.cursor = 'pointer';

        // If it's an instanced mesh, we could change color
        if (hit.object === this.corpusMesh && hit.instanceId !== undefined) {
            // We could set a specific color for the highlighted instance
            // But updating instance color requires re-uploading buffer which might be slow if frequent
            // For now, simple cursor change is enough for MVP
        }
    }

    resetHighlight() {
        this.container.style.cursor = 'default';
    }

    animate() {
        requestAnimationFrame(this.animate);

        this.controls.update();

        // Update camera guide line
        if (this.cameraLine && this.queryMesh) {
            const positions = this.cameraLine.geometry.attributes.position.array;

            // Update start point (camera position)
            // Note: We offset slightly below camera to make it look like a laser pointer
            positions[0] = this.camera.position.x;
            positions[1] = this.camera.position.y - 0.2;
            positions[2] = this.camera.position.z;

            // End point is fixed at query mesh (already set, but good to ensure)
            // positions[3] = this.queryMesh.position.x;
            // positions[4] = this.queryMesh.position.y;
            // positions[5] = this.queryMesh.position.z;

            this.cameraLine.geometry.attributes.position.needsUpdate = true;
        }

        this.renderer.render(this.scene, this.camera);
    }

    onWindowResize() {
        if (!this.container) return;

        this.width = this.container.clientWidth;
        this.height = this.container.clientHeight;

        this.camera.aspect = this.width / this.height;
        this.camera.updateProjectionMatrix();

        this.renderer.setSize(this.width, this.height);
    }

    cleanup() {
        window.removeEventListener('resize', this.onWindowResize);
        this.container.removeEventListener('mousemove', this.onMouseMove);
        this.container.removeChild(this.renderer.domElement);
        this.renderer.dispose();
        this.controls.dispose();
    }
}
