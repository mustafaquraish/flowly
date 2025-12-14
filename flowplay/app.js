/**
 * FlowPlay - Interactive Flowchart Visualizer
 * Main Application Logic
 */

/**
 * Singleton DragManager - handles document-level drag listeners
 * to avoid accumulating listeners per draggable element
 */
const DragManager = {
    activeElement: null,
    startX: 0,
    startY: 0,
    initialLeft: 0,
    initialTop: 0,
    
    init() {
        document.addEventListener('mousemove', (e) => {
            if (!this.activeElement) return;
            
            const dx = e.clientX - this.startX;
            const dy = e.clientY - this.startY;
            
            this.activeElement.style.left = `${this.initialLeft + dx}px`;
            this.activeElement.style.top = `${this.initialTop + dy}px`;
        });
        
        document.addEventListener('mouseup', () => {
            if (this.activeElement) {
                this.activeElement.classList.remove('dragging');
                this.activeElement = null;
            }
        });
    },
    
    startDrag(element, clientX, clientY) {
        this.activeElement = element;
        this.startX = clientX;
        this.startY = clientY;
        this.initialLeft = element.offsetLeft;
        this.initialTop = element.offsetTop;
        element.classList.add('dragging');
    }
};

// Initialize DragManager once
DragManager.init();

/**
 * Unified cache editor helper functions.
 * These handle the edit/delete logic for both node cache and global cache.
 */
const CacheEditorHelpers = {
    /**
     * Generates HTML rows for a cache editor
     * @param {Object} cache - The cache object (key-value pairs)
     * @param {string} placeholderPrefix - Prefix for placeholder text (e.g., 'Add key...' or 'Add global key...')
     * @param {Function} escapeHtml - HTML escaping function
     * @returns {string} HTML string
     */
    generateRows(cache, placeholderPrefix, escapeHtml) {
        let entries = Object.entries(cache);
        entries = entries.filter(([k, v]) => k.trim() !== '' || v.trim() !== '');
        entries.push(['', '']);
        
        return entries.map(([key, value], index) => {
            const isEmpty = key === '' && value === '';
            const isLast = index === entries.length - 1;
            const placeholderKey = isLast ? placeholderPrefix : 'Key';
            
            return `
            <div class="cache-row ${isEmpty ? 'empty-row' : ''}">
                <textarea class="cache-key" placeholder="${placeholderKey}" data-field="key" data-original-key="${escapeHtml(key)}">${escapeHtml(key)}</textarea>
                <textarea class="cache-value" placeholder="Value" data-field="value" data-key="${escapeHtml(key)}">${escapeHtml(value)}</textarea>
                <button class="delete-cache-btn" data-key="${escapeHtml(key)}" style="${isEmpty ? 'visibility:hidden' : ''}">×</button>
            </div>
        `}).join('');
    },
    
    /**
     * Handles edit events for a cache editor (key rename, value change, new entry)
     * @param {Event} event - The input event
     * @param {Object} cache - The cache object to modify
     * @param {string} keyPrefix - Prefix for auto-generated keys (e.g., 'key_' or 'global_')
     * @returns {boolean} Whether a re-render is needed (new entry was created)
     */
    handleEdit(event, cache, keyPrefix) {
        const input = event.target;
        const row = input.closest('.cache-row');
        const keyInput = row.querySelector('.cache-key');
        const valInput = row.querySelector('.cache-value');
        
        const originalKey = keyInput.dataset.originalKey;
        const currentKey = keyInput.value;
        const currentValue = valInput.value;
        
        if (originalKey) {
            // Modification of existing entry
            if (currentKey !== originalKey) {
                // Key change: remove old, set new
                const val = cache[originalKey];
                delete cache[originalKey];
                if (currentKey) cache[currentKey] = val;
                keyInput.dataset.originalKey = currentKey;
                valInput.dataset.key = currentKey;
                row.querySelector('.delete-cache-btn').dataset.key = currentKey;
            }
            // Value change
            if (currentKey && cache.hasOwnProperty(currentKey)) {
                cache[currentKey] = currentValue;
            }
            return false; // No re-render needed
        } else {
            // New entry creation (filling empty row)
            if (currentKey || currentValue) {
                const safeKey = currentKey || `${keyPrefix}${Date.now()}`;
                cache[safeKey] = currentValue;
                return true; // Re-render needed to add new empty row
            }
            return false;
        }
    },
    
    /**
     * Handles delete events for a cache editor
     * @param {Event} event - The click event
     * @param {Object} cache - The cache object to modify
     * @returns {boolean} Whether a re-render is needed
     */
    handleDelete(event, cache) {
        const key = event.target.dataset.key;
        if (!key) return false;
        delete cache[key];
        return true;
    }
};

class FlowPlay {
    constructor() {
        // Flow data
        this.flowData = null;
        this.nodes = {};
        this.edges = {};
        this.graph = null;
        
        // Navigation state
        this.currentNode = null;
        this.history = [];
        this.visitedNodes = new Set();
        this.historyExpanded = false;
        
        // K/V Cache per node
        this.nodeCache = new Map();
        this.globalCache = {};
        
        // D3 elements
        this.svg = null;
        
        // Configuration
        this.nodeWidth = 160;
        this.nodeHeight = 70;
        
        // Bind methods
        this.handleZoom = this.handleZoom.bind(this);
    }
    
    async init() {
        try {
            await this.loadFlowData();
            this.setupSVG();
            this.renderFlowchart();
            this.setupControls();
            this.setupOverlayControls();
            this.start();
        } catch (error) {
            console.error('Failed to initialize FlowPlay:', error);
            document.getElementById('flowchart-name').textContent = 'Error loading flowchart';
        }
    }
    
    async loadFlowData() {
        let errorMessage = 'Failed to load flowchart';
        try {
            const response = await fetch('./complex_flow.json');
            if (!response.ok) {
                errorMessage = `Failed to load flowchart: ${response.statusText}`;
                this.flowData = typeof bundledFlowData !== 'undefined' ? bundledFlowData : null;
                if (!this.flowData) {
                    throw new Error(errorMessage);
                } else {
                    console.log('Using bundled json data!');
                }
            } else {
                this.flowData = await response.json();
            }
        } catch (e) {
            this.flowData = typeof bundledFlowData !== 'undefined' ? bundledFlowData : null;
            if (!this.flowData) {
                throw new Error(errorMessage);
            } else {
                console.log('Using bundled json data!');
            }
        }
        
        // Index nodes and edges
        this.flowData.nodes.forEach(node => {
            this.nodes[node.id] = node;
        });
        this.flowData.edges.forEach(edge => {
            this.edges[edge.id] = edge;
        });
        this.graph = this.flowData.graph;
        
        // Set title
        document.getElementById('flowchart-name').textContent = this.flowData.name;
    }
    
    setupSVG() {
        const container = document.getElementById('flowchart-container');
        const width = container.clientWidth;
        const height = container.clientHeight;
        
        this.svg = d3.select('#flowchart-svg')
            .attr('width', width)
            .attr('height', height);
        
        // Add defs for arrow markers
        const defs = this.svg.append('defs');
        
        // Normal arrow
        defs.append('marker')
            .attr('id', 'arrow')
            .attr('viewBox', '0 -5 10 10')
            .attr('refX', 8)
            .attr('refY', 0)
            .attr('markerWidth', 6)
            .attr('markerHeight', 6)
            .attr('orient', 'auto')
            .append('path')
            .attr('d', 'M0,-5L10,0L0,5')
            .attr('class', 'edge-arrow');
        
        // Incoming arrow (highlighted)
        defs.append('marker')
            .attr('id', 'arrow-incoming')
            .attr('viewBox', '0 -5 10 10')
            .attr('refX', 8)
            .attr('refY', 0)
            .attr('markerWidth', 6)
            .attr('markerHeight', 6)
            .attr('orient', 'auto')
            .append('path')
            .attr('d', 'M0,-5L10,0L0,5')
            .attr('class', 'edge-arrow incoming');
        
        // Create main group for zoom/pan
        this.g = this.svg.append('g').attr('class', 'main-group');
        
        // Setup zoom behavior with filter to not zoom when over overlay
        this.zoom = d3.zoom()
            .scaleExtent([0.1, 4])
            .filter((event) => {
                // Don't zoom/pan when interacting with the overlay
                const overlay = document.getElementById('node-overlay');
                if (overlay && overlay.contains(event.target)) {
                    return false;
                }
                return true;
            })
            .on('zoom', this.handleZoom);
        
        this.svg.call(this.zoom);
    }
    
    handleZoom(event) {
        this.g.attr('transform', event.transform);
        // Reposition overlay when zooming/panning
        this.positionOverlay();
        // Reposition incoming caches
        this.positionIncomingCaches();
    }
    
    renderFlowchart() {
        // Use Dagre for proper hierarchical DAG layout (like Graphviz/Mermaid)
        const g = new dagre.graphlib.Graph();
        
        // Set graph properties - top-to-bottom layout (vertical)
        g.setGraph({
            rankdir: 'LR',  // Left to right
            nodesep: 200 * 2,   // Horizontal separation between nodes (increased for spread)
            ranksep: 200 * 2,   // Vertical separation between ranks
            marginx: 50,
            marginy: 50
        });
        
        // Default edge label (required by Dagre)
        g.setDefaultEdgeLabel(() => ({}));
        
        // Add nodes to the graph
        this.flowData.nodes.forEach(node => {
            g.setNode(node.id, {
                width: this.nodeWidth,
                height: this.nodeHeight,
                label: node.label
            });
        });
        
        // Add edges to the graph
        this.flowData.edges.forEach(edge => {
            g.setEdge(edge.source, edge.target);
        });
        
        // Compute the layout
        dagre.layout(g);
        
        // Copy positions back to our nodes index
        this.flowData.nodes.forEach(node => {
            const dagreNode = g.node(node.id);
            this.nodes[node.id].x = dagreNode.x;
            this.nodes[node.id].y = dagreNode.y;
        });
        
        // Draw edges
        const edgeGroup = this.g.append('g').attr('class', 'edges');
        
        // Draw edges using the positioned nodes - make them clickable
        this.flowData.edges.forEach(edge => {
            const source = this.nodes[edge.source];
            const target = this.nodes[edge.target];
            
            // Calculate edge path
            const path = this.calculateEdgePath(source, target);
            
            edgeGroup.append('path')
                .attr('class', 'edge-path')
                .attr('id', `edge-${edge.id}`)
                .attr('d', path)
                .attr('marker-end', 'url(#arrow)')
                .datum(edge)
                .style('cursor', 'pointer')
                .on('click', (event) => {
                    event.stopPropagation();
                    // Navigate to the target node (follow the arrow direction)
                    this.navigateToNode(edge.target);
                })
                .append('title')
                .text(`Click to go to: ${target.label}`);
            
            // Edge label
            if (edge.label) {
                const midX = (source.x + target.x) / 2;
                const midY = (source.y + target.y) / 2;
                
                edgeGroup.append('text')
                    .attr('class', 'edge-label')
                    .attr('x', midX)
                    .attr('y', midY - 8)
                    .attr('text-anchor', 'middle')
                    .text(edge.label);
            }
        });
        
        // Draw nodes using our updated nodes index
        const nodeGroup = this.g.append('g').attr('class', 'nodes');
        
        Object.values(this.nodes).forEach(node => {
            const g = nodeGroup.append('g')
                .attr('class', 'node-group')
                .attr('id', `node-${node.id}`)
                .attr('transform', `translate(${node.x}, ${node.y})`)
                .on('click', () => this.navigateToNode(node.id));
            
            // Add tooltip on hover
            g.append('title')
                .text(`${this.formatNodeType(node.type)}: ${node.label}\nClick to navigate`);
            
            // Collapsed node shape (visible when not selected)
            const collapsedGroup = g.append('g').attr('class', 'node-collapsed');
            
            if (node.type === 'DecisionNode') {
                const size = 50;
                collapsedGroup.append('polygon')
                    .attr('class', `node-shape ${node.type}`)
                    .attr('points', `0,-${size} ${size * 2},0 0,${size} -${size * 2},0`);
            } else {
                collapsedGroup.append('rect')
                    .attr('class', `node-shape ${node.type}`)
                    .attr('x', -this.nodeWidth / 2)
                    .attr('y', -this.nodeHeight / 2)
                    .attr('width', this.nodeWidth)
                    .attr('height', this.nodeHeight)
                    .attr('rx', node.type === 'StartNode' || node.type === 'EndNode' ? 35 : 10);
            }
            
            // Node label for collapsed state
            const labelGroup = collapsedGroup.append('text')
                .attr('class', `node-label ${node.type}`)
                .attr('text-anchor', 'middle');
            
            const maxCharsPerLine = 28;
            const words = node.label.split(' ');
            const lines = [];
            let currentLine = '';
            
            words.forEach(word => {
                if ((currentLine + ' ' + word).trim().length <= maxCharsPerLine) {
                    currentLine = (currentLine + ' ' + word).trim();
                } else {
                    if (currentLine) lines.push(currentLine);
                    currentLine = word;
                }
            });
            if (currentLine) lines.push(currentLine);
            
            const lineHeight = 16;
            const startY = -((lines.length - 1) * lineHeight) / 2;
            
            lines.forEach((line, i) => {
                labelGroup.append('tspan')
                    .attr('x', 0)
                    .attr('dy', i === 0 ? startY : lineHeight)
                    .text(line);
            });
        });
        
        // Initial fit
        this.fitToView();
    }
    
    calculateEdgePath(source, target) {
        const dx = target.x - source.x;
        const dy = target.y - source.y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        
        // Offset to avoid overlapping with node shapes (increased for larger nodes)
        const sourceOffset = 60;
        const targetOffset = 65;
        
        const sx = source.x + (dx / dist) * sourceOffset;
        const sy = source.y + (dy / dist) * sourceOffset;
        const tx = target.x - (dx / dist) * targetOffset;
        const ty = target.y - (dy / dist) * targetOffset;
        
        // Curved path
        const midX = (sx + tx) / 2;
        const midY = (sy + ty) / 2;
        const curvature = 0.2;
        const cx = midX; // - dy * curvature;
        const cy = midY; // + dx * curvature;
        
        return `M${sx},${sy} Q${cx},${cy} ${tx},${ty}`;
    }
    
    truncateLabel(label, maxLength) {
        if (label.length <= maxLength) return label;
        return label.substring(0, maxLength - 2) + '...';
    }
    
    setupControls() {
        document.getElementById('restart-btn').addEventListener('click', () => this.restart());
        document.getElementById('zoom-in').addEventListener('click', () => this.zoomIn());
        document.getElementById('zoom-out').addEventListener('click', () => this.zoomOut());
        document.getElementById('fit-view').addEventListener('click', () => this.fitToView());
        
        // Help panel toggle
        const helpBtn = document.getElementById('help-btn');
        const shortcutsPanel = document.getElementById('shortcuts-panel');
        if (helpBtn && shortcutsPanel) {
            helpBtn.addEventListener('click', () => {
                shortcutsPanel.classList.toggle('hidden');
                helpBtn.classList.toggle('active');
            });
        }
        
        // Key bindings - extended for better navigation
        document.addEventListener('keydown', (e) => {
            // Don't capture when typing in inputs
            if (e.target.tagName === 'TEXTAREA' || e.target.tagName === 'INPUT') return;
            
            switch(e.key) {
                case 'r': this.restart(); break;
                case '=':
                case '+': this.zoomIn(); break;
                case '-': this.zoomOut(); break;
                case 'f': this.fitToView(); break;
                
                // Navigation shortcuts
                case 'Escape':
                    // Close overlay and fit to view
                    this.closeOverlay();
                    break;
                case 'Backspace':
                case 'b':
                    // Go back to previous node
                    e.preventDefault();
                    this.goBack();
                    break;
                    
                // Number keys 1-9 for selecting edges
                case '1': case '2': case '3': case '4': case '5':
                case '6': case '7': case '8': case '9':
                    this.selectEdgeByNumber(parseInt(e.key));
                    break;
                    
                // Arrow keys for edge selection  
                case 'ArrowDown':
                case 'ArrowRight':
                    e.preventDefault();
                    this.selectNextEdge();
                    break;
                case 'ArrowUp':
                case 'ArrowLeft':
                    e.preventDefault();
                    this.selectPrevEdge();
                    break;
                case 'Enter':
                    this.activateSelectedEdge();
                    break;
                case '?':
                    // Toggle help panel
                    const shortcutsPanel = document.getElementById('shortcuts-panel');
                    const helpBtn = document.getElementById('help-btn');
                    if (shortcutsPanel) {
                        shortcutsPanel.classList.toggle('hidden');
                        helpBtn?.classList.toggle('active');
                    }
                    break;
            }
        });
        
        // Track currently highlighted edge for keyboard nav
        this.selectedEdgeIndex = -1;
        
        this.setupGlobalCache();
    }
    
    setupOverlayControls() {
        const closeBtn = document.getElementById('overlay-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.closeOverlay();
            });
        }
        
        const backBtn = document.getElementById('overlay-back');
        if (backBtn) {
            backBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.goBack();
            });
        }
    }
    
    setupGlobalCache() {
        // Toggle button
        const toggle = document.getElementById('global-cache-toggle');
        const panel = document.getElementById('global-cache-panel');
        
        if (toggle && panel) {
            toggle.addEventListener('click', () => {
                const isHidden = panel.classList.contains('hidden');
                if (isHidden) {
                    panel.classList.remove('hidden');
                    toggle.classList.add('active');
                    this.renderGlobalCache();
                } else {
                    panel.classList.add('hidden');
                    toggle.classList.remove('active');
                }
            });
        }
    }
    
    start() {
        // Find start node
        const startNode = this.flowData.nodes.find(n => n.type === 'StartNode');
        if (startNode) {
            this.navigateToNode(startNode.id);
        }
    }
    
    restart() {
        // Clear state
        this.history = [];
        this.visitedNodes.clear();
        this.nodeCache.clear();
        
        // Reset visual state
        this.g.selectAll('.node-group').classed('current', false).classed('visited', false);
        this.g.selectAll('.node-collapsed').style('opacity', 1);
        this.g.selectAll('.edge-path').classed('incoming', false).classed('outgoing', false);
        
        // Clear incoming caches
        document.getElementById('incoming-caches-container').innerHTML = '';
        
        // Hide overlay
        document.getElementById('node-overlay').classList.add('hidden');
        
        // Start fresh
        this.start();
    }
    
    navigateToNode(nodeId) {
        const node = this.nodes[nodeId];
        if (!node) return;
        
        // Reset keyboard edge selection
        this.selectedEdgeIndex = -1;
        
        // Hide overlay during transition
        document.getElementById('node-overlay').classList.add('hidden');
        
        // Restore visibility of previous node's collapsed shape
        if (this.currentNode) {
            d3.select(`#node-${this.currentNode.id} .node-collapsed`).style('opacity', 1);
            this.visitedNodes.add(this.currentNode.id);
            d3.select(`#node-${this.currentNode.id}`).classed('current', false).classed('visited', true);
        }
        
        this.currentNode = node;
        this.history.push(nodeId);
        
        // Update visual state
        d3.select(`#node-${nodeId}`).classed('current', true);
        
        // Highlight edges
        this.updateEdgeHighlights();
        
        // Update UI content (before zoom so it's ready when zoom completes)
        this.updateCurrentNodePanel();
        this.updateIncomingCaches();
        this.updateHistory();
        
        // Zoom to node (overlay shown after zoom completes)
        this.zoomToNode(node);
    }
    
    updateEdgeHighlights() {
        // Reset all edges
        this.g.selectAll('.edge-path')
            .classed('incoming', false)
            .classed('outgoing', false)
            .attr('marker-end', 'url(#arrow)');
        
        if (!this.currentNode) return;
        
        // Highlight incoming edges
        const incomingEdgeIds = this.graph.incomingEdges[this.currentNode.id] || [];
        incomingEdgeIds.forEach(edgeId => {
            d3.select(`#edge-${edgeId}`)
                .classed('incoming', true)
                .attr('marker-end', 'url(#arrow-incoming)');
        });
        
        // Highlight outgoing edges
        const outgoingEdgeIds = this.graph.outgoingEdges[this.currentNode.id] || [];
        outgoingEdgeIds.forEach(edgeId => {
            d3.select(`#edge-${edgeId}`).classed('outgoing', true);
        });
    }
    
    zoomToNode(node) {
        const container = document.getElementById('flowchart-container');
        const width = container.clientWidth;
        const height = container.clientHeight;
        
        // Measure the overlay to determine best fit
        const overlay = document.getElementById('node-overlay');
        // Temporarily make visible (but hidden) to measure
        const wasHidden = overlay.classList.contains('hidden');
        overlay.style.visibility = 'hidden';
        overlay.classList.remove('hidden');
        
        const overlayWidth = overlay.offsetWidth || 360;
        const overlayHeight = overlay.offsetHeight || 400;
        
        // Restore state
        overlay.classList.add('hidden');
        overlay.style.visibility = '';
        if (!wasHidden) overlay.classList.remove('hidden');
        
        // Calculate target scale to fit 60% of viewport
        // We want the overlay to appear as 60% of the smallest viewport dimension
        // OR 60% of its own dimension relative to viewport (fitting logic)
        
        // Let's implement key requirement: "60% of height/width depending on smallest constrained dimension"
        
        // Calculate scale factors for both dimensions
        // transform.k = scale * 1.6
        // size_on_screen = size_base * (transform.k / 1.6)
        // target_size = viewport_size * 0.6
        // target_k = (viewport_size * 0.6 / size_base) * 1.6
        
        const targetK_w = (width * 0.6 / overlayWidth) * 1.6;
        const targetK_h = (height * 0.6 / overlayHeight) * 1.6;
        
        // Use the smaller scale to ensure it fits within 60% bounds of both constraints if needed
        let targetScale = Math.min(targetK_w, targetK_h);
        
        // Clamp scale to reasonable limits
        targetScale = Math.max(0.4, Math.min(targetScale, 4.0));
        
        // Center node in viewport
        const centerX = width / 2;
        const centerY = height / 2;
        
        // Calculate translation to center the node
        const x = centerX - node.x * targetScale;
        const y = centerY - node.y * targetScale;
        
        this.svg.transition()
            .duration(600)
            .call(this.zoom.transform, d3.zoomIdentity.translate(x, y).scale(targetScale))
            .on('end', () => {
                // Position and show overlay after zoom completes
                this.positionOverlay();
            });
    }
    
    positionOverlay() {
        if (!this.currentNode) return;
        
        const overlay = document.getElementById('node-overlay');
        
        // Get current transform
        const transform = d3.zoomTransform(this.svg.node());
        
        // Calculate node center position in screen coordinates
        // Transform converts SVG coordinates to screen coordinates
        const nodeScreenX = this.currentNode.x * transform.k + transform.x;
        const nodeScreenY = this.currentNode.y * transform.k + transform.y;
        
        // Position overlay exactly centered on the node
        // We use translate(-50%, -50%) to handle centering dynamically based on content size
        overlay.style.left = `${nodeScreenX}px`;
        overlay.style.top = `${nodeScreenY}px`;
        
        // Scale with zoom without limit
        // Current overlay scale relative to its natural size
        const currentScale = transform.k / 1.6;
        
        overlay.style.transform = `translate(-50%, -50%) scale(${currentScale})`;
        overlay.style.transformOrigin = 'center center';
        overlay.classList.remove('hidden');
        
        // Hide the collapsed SVG node so only overlay shows
        d3.select(`#node-${this.currentNode.id} .node-collapsed`).style('opacity', 0);
    }
    
    updateCurrentNodePanel() {
        const overlay = document.getElementById('node-overlay');
        const node = this.currentNode;
        
        // Update type badge
        const badge = document.getElementById('overlay-badge');
        badge.textContent = this.formatNodeType(node.type);
        badge.className = `node-badge ${node.type}`;
        
        // Update title
        document.getElementById('overlay-title').textContent = node.label;
        
        // Update overlay type class for styling
        overlay.className = `node-overlay ${node.type}`;
        
        // Show/hide back button based on history
        const backBtn = document.getElementById('overlay-back');
        if (backBtn) {
            backBtn.classList.toggle('hidden', this.history.length <= 1);
        }
        
        // Update description
        const descEl = document.getElementById('overlay-description');
        const description = node.metadata?.description || '';
        if (description) {
            descEl.innerHTML = marked.parse(description.trim());
            descEl.style.display = 'block';
        } else {
            descEl.style.display = 'none';
        }
        
        // Update cache entries
        this.renderOverlayData();
        
        // Update actions
        this.renderOverlayActions();
        
        // Bind add cache button (NO - using dynamic empty row now)
        // const addBtn = document.getElementById('overlay-add-cache');
        // if (addBtn) addBtn.onclick = ...; 
    }
    
    renderOverlayData() {
        const container = document.getElementById('overlay-cache-entries');
        const headerSpan = document.querySelector('.overlay-cache .section-header span');
        if (headerSpan) headerSpan.textContent = 'Data';
        
        const cache = this.nodeCache.get(this.currentNode.id) || {};
        container.innerHTML = CacheEditorHelpers.generateRows(cache, 'Add key...', this.escapeHtml.bind(this));
        
        // Use event delegation - attach once to container instead of per-element
        this.setupCacheEditorDelegation(container, 'node');
    }
    
    renderOverlayActions() {
        const container = document.getElementById('overlay-actions');
        container.innerHTML = '';
        
        if (this.currentNode.type === 'EndNode') {
            container.innerHTML = '<div class="flow-complete">Flow completed! 🎉</div>';
            return;
        }
        
        const outgoingEdgeIds = this.graph.outgoingEdges[this.currentNode.id] || [];
        
        if (outgoingEdgeIds.length === 0) {
            container.innerHTML = '<div class="flow-complete">Dead end</div>';
            return;
        }
        
        outgoingEdgeIds.forEach((edgeId, index) => {
            const edge = this.edges[edgeId];
            const targetNode = this.nodes[edge.target];
            
            const btn = document.createElement('button');
            btn.className = 'edge-btn';
            
            const label = edge.label || 'Continue';
            const shortcutHint = index < 9 ? `<span class="shortcut-hint">${index + 1}</span>` : '';
            btn.innerHTML = `${shortcutHint}<span class="arrow">→</span>${label}<span class="target">${this.truncateLabel(targetNode.label, 20)}</span>`;
            
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.navigateToNode(edge.target);
            });
            container.appendChild(btn);
        });
    }
    
    formatNodeType(type) {
        return type.replace('Node', '').toUpperCase();
    }
    
    escapeHtml(str) {
        if (typeof str !== 'string') return str;
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
    
    /**
     * Sets up event delegation for cache editors (handles both node and global cache)
     * @param {HTMLElement} container - The container element for cache rows
     * @param {string} cacheType - 'node' or 'global'
     */
    setupCacheEditorDelegation(container, cacheType) {
        // Remove any existing listeners by cloning (event delegation means we set once)
        const newContainer = container.cloneNode(true);
        container.parentNode.replaceChild(newContainer, container);
        
        // Input event delegation
        newContainer.addEventListener('input', (e) => {
            if (e.target.classList.contains('cache-key') || e.target.classList.contains('cache-value')) {
                const cache = cacheType === 'node' 
                    ? this.nodeCache.get(this.currentNode.id) || {}
                    : this.globalCache;
                const keyPrefix = cacheType === 'node' ? 'key_' : 'global_';
                
                const needsRerender = CacheEditorHelpers.handleEdit(e, cache, keyPrefix);
                
                if (cacheType === 'node') {
                    this.nodeCache.set(this.currentNode.id, cache);
                }
                
                if (needsRerender) {
                    const input = e.target;
                    const renderFn = cacheType === 'node' ? 'renderOverlayData' : 'renderGlobalCache';
                    this[renderFn]();
                    
                    // Focus restoration after re-render
                    const containerSelector = cacheType === 'node' ? '#overlay-cache-entries' : '#global-cache-entries';
                    const updatedContainer = document.querySelector(containerSelector);
                    const newRows = updatedContainer.querySelectorAll('.cache-row');
                    const targetRow = newRows[newRows.length - 2];
                    if (targetRow) {
                        const selector = input.classList.contains('cache-key') ? '.cache-key' : '.cache-value';
                        const toFocus = targetRow.querySelector(selector);
                        if (toFocus) {
                            toFocus.focus();
                            const len = toFocus.value.length;
                            toFocus.setSelectionRange(len, len);
                        }
                    }
                }
            }
        });
        
        // Click event delegation for delete buttons
        newContainer.addEventListener('click', (e) => {
            if (e.target.classList.contains('delete-cache-btn')) {
                e.stopPropagation();
                const cache = cacheType === 'node'
                    ? this.nodeCache.get(this.currentNode.id) || {}
                    : this.globalCache;
                
                if (CacheEditorHelpers.handleDelete(e, cache)) {
                    if (cacheType === 'node') {
                        this.nodeCache.set(this.currentNode.id, cache);
                        this.renderOverlayData();
                    } else {
                        this.renderGlobalCache();
                    }
                }
            }
        });
    }

    
    updateIncomingCaches() {
        const container = document.getElementById('incoming-caches-container');
        container.innerHTML = '';
        
        const incomingEdgeIds = this.graph.incomingEdges[this.currentNode.id] || [];
        
        incomingEdgeIds.forEach((edgeId, index) => {
            const edge = this.edges[edgeId];
            const sourceNode = this.nodes[edge.source];
            const cache = this.nodeCache.get(sourceNode.id) || {};
            
            // Create panel
            const panel = document.createElement('div');
            // Add source node type class for styling
            panel.className = `incoming-cache-panel glass-panel draggable ${sourceNode.type}`;
            panel.dataset.edgeId = edgeId;
            
            const sourceId = sourceNode.id;
            panel.innerHTML = `
                <div class="drag-handle">⋮⋮</div>
                <div class="incoming-source" data-node-id="${sourceId}">
                    <span class="arrow">←</span>
                    <span class="source-label">${this.truncateLabel(sourceNode.label, 22)}</span>
                </div>
                ${this.renderReadOnlyCache(cache)}
            `;
            
            // Make source clickable
            panel.querySelector('.incoming-source').addEventListener('click', () => {
                this.navigateToNode(sourceId);
            });
            
            // Allow text selection without triggering drag
            // We do this by stopping propagation of mousedown events on the content
            const content = panel.querySelector('.cache-table');
            if (content) {
                content.addEventListener('mousedown', (e) => {
                    e.stopPropagation();
                });
            }
            
            // Make panel draggable
            this.makeDraggable(panel);
            
            container.appendChild(panel);
        });
        
        // Initial position
        this.positionIncomingCaches();
    }
    
    positionIncomingCaches() {
        const panels = document.querySelectorAll('.incoming-cache-panel');
        if (panels.length === 0) return;
        
        const transform = d3.zoomTransform(this.svg.node());
        const containerRect = document.getElementById('flowchart-container').getBoundingClientRect();
        
        panels.forEach(panel => {
            // If user is dragging this panel, don't auto-position it
            if (panel.classList.contains('dragging')) return;
            
            const edgeId = panel.dataset.edgeId;
            const edge = this.edges[edgeId];
            if (!edge) return;
            
            const sourceNode = this.nodes[edge.source];
            const targetNode = this.nodes[edge.target];
            
            // 1. Calculate angles and positions
            const containerWidth = containerRect.width;
            const containerHeight = containerRect.height;
            const padding = 20;
            const panelWidth = panel.offsetWidth || 260; // Update default width
            const panelHeight = panel.offsetHeight || 140;
            
            // Current node screen position (center of screen typically, but robust to check)
            const targetScreenX = targetNode.x * transform.k + transform.x;
            const targetScreenY = targetNode.y * transform.k + transform.y;
            
            // Source node screen position
            const sourceScreenX = sourceNode.x * transform.k + transform.x;
            const sourceScreenY = sourceNode.y * transform.k + transform.y;
            
            // Vector from target (center) to source
            const vecX = sourceScreenX - targetScreenX;
            const vecY = sourceScreenY - targetScreenY;
            
            // If nodes are effectively same position (unlikely), default to left
            if (Math.abs(vecX) < 1 && Math.abs(vecY) < 1) {
                panel.style.left = `${padding}px`;
                panel.style.top = `${containerHeight/2}px`;
                return;
            }
            
            // Ray casting to viewport bounds
            // We want to find where the ray (target -> source) hits the bounding box [padding, width-padding, height-padding]
            // The bounding box for the CENTER of the panel needs to account for panel size
            
            const minX = padding;
            const maxX = containerWidth - panelWidth - padding;
            const minY = padding;
            const maxY = containerHeight - panelHeight - padding;
            
            // Slope
            const m = vecY / vecX;
            
            let finalX, finalY;
            
            if (Math.abs(vecX) > Math.abs(vecY)) {
                // Horizontal dominant - hits left or right wall first
                if (vecX > 0) {
                    // Right wall
                    finalX = maxX;
                    finalY = targetScreenY + (finalX - targetScreenX) * m;
                } else {
                    // Left wall
                    finalX = minX;
                    finalY = targetScreenY + (finalX - targetScreenX) * m;
                }
                
                // Clamp Y if it went out of bounds (corner case)
                finalY = Math.max(minY, Math.min(finalY, maxY));
            } else {
                // Vertical dominant - hits top or bottom wall first
                if (vecY > 0) {
                    // Bottom wall
                    finalY = maxY;
                    // x = (y - y1)/m + x1
                    // avoid div by zero if vertical, but handled by if branch
                    finalX = targetScreenX + (finalY - targetScreenY) / m;
                } else {
                    // Top wall
                    finalY = minY;
                    finalX = targetScreenX + (finalY - targetScreenY) / m;
                }
                
                // Clamp X if it went out of bounds
                finalX = Math.max(minX, Math.min(finalX, maxX));
            }
            
            // Apply coordinates
            panel.style.left = `${finalX}px`;
            panel.style.top = `${finalY}px`;
        });
    }

    renderReadOnlyCache(cache) {
        const entries = Object.entries(cache);
        if (entries.length === 0) {
            return '<div class="empty-cache" style="padding:4px; font-style:italic; opacity:0.6;">No data</div>';
        }
        
        // Ensure proper HTML table structure
        let html = '<table class="cache-table"><tbody>';
        entries.forEach(([key, value]) => {
            html += `<tr>
                <td class="cache-key">${this.escapeHtml(key)}</td>
                <td class="cache-value">${this.escapeHtml(value)}</td>
            </tr>`;
        });
        html += '</tbody></table>';
        return html;
    }
    
    makeDraggable(element) {
        const dragHandle = element.querySelector('.drag-handle') || element;
        
        dragHandle.addEventListener('mousedown', (e) => {
            // Use singleton drag manager state
            DragManager.startDrag(element, e.clientX, e.clientY);
            e.preventDefault();
        });
    }
    
    updateHistory() {
        const container = document.getElementById('history-trail');
        container.innerHTML = '';
        
        let displayHistory = this.history;
        let truncated = false;
        
        if (!this.historyExpanded && this.history.length > 5) {
            displayHistory = this.history.slice(-5);
            truncated = true;
        }
        
        if (truncated) {
             const expandBtn = document.createElement('span');
             expandBtn.className = 'history-expand';
             expandBtn.textContent = `+${this.history.length - 5} more`;
             expandBtn.title = "Show full history";
             expandBtn.addEventListener('click', () => {
                 this.historyExpanded = true;
                 this.updateHistory();
             });
             container.appendChild(expandBtn);
             
             const sep = document.createElement('span');
             sep.className = 'history-separator';
             sep.textContent = '→';
             container.appendChild(sep);
        } else if (this.historyExpanded && this.history.length > 5) {
             const collapseBtn = document.createElement('span');
             collapseBtn.className = 'history-expand';
             collapseBtn.textContent = `Show less`;
             collapseBtn.addEventListener('click', () => {
                 this.historyExpanded = false;
                 this.updateHistory();
             });
             container.appendChild(collapseBtn);
             
             const sep = document.createElement('span');
             sep.className = 'history-separator';
             sep.textContent = '→';
             container.appendChild(sep);
        }
        
        displayHistory.forEach((nodeId, index) => {
            const node = this.nodes[nodeId];
            
            if (index > 0) {
                const sep = document.createElement('span');
                sep.className = 'history-separator';
                sep.textContent = '→';
                container.appendChild(sep);
            }
            
            const item = document.createElement('span');
            item.className = 'history-item';
            
            // Check if this is the actual last item of the full history
            const isLast = (truncated ? index + (this.history.length - 5) : index) === this.history.length - 1;
            
            if (isLast) {
                item.classList.add('current');
            }
            item.textContent = this.truncateLabel(node.label, 12);
            item.title = node.label;
            item.dataset.nodeId = nodeId;
            
            // Make clickable
            item.addEventListener('click', () => {
                this.navigateToNode(nodeId);
            });
            
            container.appendChild(item);
        });
    }
    
    zoomIn() {
        this.svg.transition().duration(300).call(this.zoom.scaleBy, 1.3);
    }
    
    zoomOut() {
        this.svg.transition().duration(300).call(this.zoom.scaleBy, 0.7);
    }
    
    // Navigation helper methods
    goBack() {
        if (this.history.length > 1) {
            // Remove current node from history
            this.history.pop();
            // Get previous node
            const prevNodeId = this.history[this.history.length - 1];
            // Remove it too (navigateToNode will re-add it)
            this.history.pop();
            this.navigateToNode(prevNodeId);
        }
    }
    
    closeOverlay() {
        const overlay = document.getElementById('node-overlay');
        overlay.classList.add('hidden');
        // Restore the current node's collapsed shape
        if (this.currentNode) {
            d3.select(`#node-${this.currentNode.id} .node-collapsed`).style('opacity', 1);
        }
        this.fitToView();
    }
    
    selectEdgeByNumber(num) {
        const outgoingEdgeIds = this.graph.outgoingEdges[this.currentNode?.id] || [];
        if (num <= outgoingEdgeIds.length) {
            const edgeId = outgoingEdgeIds[num - 1];
            const edge = this.edges[edgeId];
            this.navigateToNode(edge.target);
        }
    }
    
    selectNextEdge() {
        const buttons = document.querySelectorAll('#overlay-actions .edge-btn');
        if (buttons.length === 0) return;
        
        this.selectedEdgeIndex = Math.min(this.selectedEdgeIndex + 1, buttons.length - 1);
        this.highlightEdgeButton(buttons);
    }
    
    selectPrevEdge() {
        const buttons = document.querySelectorAll('#overlay-actions .edge-btn');
        if (buttons.length === 0) return;
        
        if (this.selectedEdgeIndex < 0) this.selectedEdgeIndex = 0;
        this.selectedEdgeIndex = Math.max(this.selectedEdgeIndex - 1, 0);
        this.highlightEdgeButton(buttons);
    }
    
    highlightEdgeButton(buttons) {
        buttons.forEach((btn, i) => {
            btn.classList.toggle('keyboard-selected', i === this.selectedEdgeIndex);
        });
    }
    
    activateSelectedEdge() {
        const buttons = document.querySelectorAll('#overlay-actions .edge-btn');
        if (this.selectedEdgeIndex >= 0 && this.selectedEdgeIndex < buttons.length) {
            buttons[this.selectedEdgeIndex].click();
        }
    }
    
    fitToView() {
        const container = document.getElementById('flowchart-container');
        const width = container.clientWidth;
        const height = container.clientHeight;
        
        // Get bounds of all nodes
        let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
        this.flowData.nodes.forEach(node => {
            minX = Math.min(minX, node.x - this.nodeWidth);
            minY = Math.min(minY, node.y - this.nodeHeight);
            maxX = Math.max(maxX, node.x + this.nodeWidth);
            maxY = Math.max(maxY, node.y + this.nodeHeight);
        });
        
        const graphWidth = maxX - minX;
        const graphHeight = maxY - minY;
        
        const scale = Math.min(
            (width - 100) / graphWidth,
            (height - 100) / graphHeight,
            1.5
        );
        
        const centerX = (minX + maxX) / 2;
        const centerY = (minY + maxY) / 2;
        
        const x = width / 2 - centerX * scale;
        const y = height / 2 - centerY * scale;
        
        this.svg.transition()
            .duration(750)
            .call(this.zoom.transform, d3.zoomIdentity.translate(x, y).scale(scale));
    }
    // Global Cache Methods
    renderGlobalCache() {
        const container = document.getElementById('global-cache-entries');
        if (!container) return;
        
        // Use shared helper to generate rows (reuse same structure as node cache)
        container.innerHTML = CacheEditorHelpers.generateRows(this.globalCache, 'Add global key...', this.escapeHtml.bind(this));
        
        // Use event delegation - same as node cache
        this.setupCacheEditorDelegation(container, 'global');
        
        // Update toggle button to show count
        this.updateGlobalCacheToggle();
    }
    
    updateGlobalCacheToggle() {
        const toggle = document.getElementById('global-cache-toggle');
        if (!toggle) return;
        
        const count = Object.keys(this.globalCache).length;
        const countBadge = count > 0 ? ` <span class="cache-count">(${count})</span>` : '';
        toggle.innerHTML = `Global Data${countBadge}`;
    }
}

// Initialize on load
document.addEventListener('DOMContentLoaded', () => {
    const app = new FlowPlay();
    app.init();
});
