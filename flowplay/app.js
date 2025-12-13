/**
 * FlowPlay - Interactive Flowchart Visualizer
 * Main Application Logic
 */

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
        
        // K/V Cache per node
        this.nodeCache = new Map();
        
        // D3 elements
        this.svg = null;
        this.history = [];
        this.historyExpanded = false;
        this.globalCache = {};
        
        // Configuration
        this.nodeWidth = 160;
        this.nodeHeight = 70;
        this.simulation = null;
        
        // Bind methods
        this.handleZoom = this.handleZoom.bind(this);
    }
    
    async init() {
        try {
            await this.loadFlowData();
            this.setupSVG();
            this.renderFlowchart();
            this.setupControls();
            this.start();
        } catch (error) {
            console.error('Failed to initialize FlowPlay:', error);
            document.getElementById('flowchart-name').textContent = 'Error loading flowchart';
        }
    }
    
    async loadFlowData() {
        const response = await fetch('./complex_flow.json');
        if (!response.ok) {
            throw new Error(`Failed to load flowchart: ${response.statusText}`);
        }
        this.flowData = await response.json();
        
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
            rankdir: 'TB',  // Top to bottom
            nodesep: 200,   // Horizontal separation between nodes (increased for spread)
            ranksep: 120,   // Vertical separation between ranks
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
        
        // Draw edges using the positioned nodes
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
                .datum(edge);
            
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
        const cx = midX - dy * curvature;
        const cy = midY + dx * curvature;
        
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
        
        // Key bindings
        document.addEventListener('keydown', (e) => {
            if (e.target.tagName === 'TEXTAREA' || e.target.tagName === 'INPUT') return;
            
            switch(e.key) {
                case 'r': this.restart(); break;
                case '=':
                case '+': this.zoomIn(); break;
                case '-': this.zoomOut(); break;
                case 'f': this.fitToView(); break;
            }
        });
        
        this.setupGlobalCache();
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
        const header = document.querySelector('.overlay-cache .section-header');
        if (header) header.textContent = 'Data';
        
        const cache = this.nodeCache.get(this.currentNode.id) || {};
        
        // Convert to array
        let entries = Object.entries(cache);
        
        // Always ensure one empty row at the end
        // Prune extra empty rows if any (where key and value are both empty), except the last one
        entries = entries.filter(([k, v]) => k.trim() !== '' || v.trim() !== '');
        entries.push(['', '']); 
        
        container.innerHTML = entries.map(([key, value], index) => {
            const isEmpty = key === '' && value === '';
            const isLast = index === entries.length - 1;
            const placeholderKey = isLast ? 'Add key...' : 'Key';
            
            return `
            <div class="cache-row ${isEmpty ? 'empty-row' : ''}">
                <textarea class="cache-key" placeholder="${placeholderKey}" data-field="key" data-original-key="${this.escapeHtml(key)}">${this.escapeHtml(key)}</textarea>
                <textarea class="cache-value" placeholder="Value" data-field="value" data-key="${this.escapeHtml(key)}">${this.escapeHtml(value)}</textarea>
                <button class="delete-cache-btn" data-key="${this.escapeHtml(key)}" style="${isEmpty ? 'visibility:hidden' : ''}">×</button>
            </div>
        `}).join('');
        
        // Bind events
        container.querySelectorAll('.cache-key, .cache-value').forEach(textarea => {
            textarea.addEventListener('input', (e) => this.handleDataEdit(e));
        });
        
        container.querySelectorAll('.delete-cache-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.handleDataDelete(e);
            });
        });
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
        
        outgoingEdgeIds.forEach(edgeId => {
            const edge = this.edges[edgeId];
            const targetNode = this.nodes[edge.target];
            
            const btn = document.createElement('button');
            btn.className = 'edge-btn';
            
            const label = edge.label || 'Continue';
            btn.innerHTML = `<span class="arrow">→</span>${label}<span class="target">${this.truncateLabel(targetNode.label, 20)}</span>`;
            
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
    
    handleDataEdit(event) {
        const input = event.target;
        // Find row inputs
        const row = input.closest('.cache-row');
        const keyInput = row.querySelector('.cache-key');
        const valInput = row.querySelector('.cache-value');
        
        const originalKey = keyInput.dataset.originalKey;
        const currentKey = keyInput.value;
        const currentValue = valInput.value;
        
        const cache = this.nodeCache.get(this.currentNode.id) || {};
        
        // Logic:
        // 1. If modifying an existing key (originalKey exists and is not empty):
        //    - rename property if key changed
        //    - update value if value changed
        // 2. If this was the empty row (originalKey is empty):
        //    - Add new entry to cache
        //    - Trigger re-render to add new empty row
        
        if (originalKey) {
            // Modification of existing entry
            if (currentKey !== originalKey) {
                // Key change: remove old, set new
                const val = cache[originalKey];
                delete cache[originalKey];
                // Only set new if key not empty
                if (currentKey) cache[currentKey] = val; // keep old value
                keyInput.dataset.originalKey = currentKey;
                valInput.dataset.key = currentKey;
                row.querySelector('.delete-cache-btn').dataset.key = currentKey;
            }
            // Value change
            if (currentKey && cache.hasOwnProperty(currentKey)) {
                cache[currentKey] = currentValue;
            }
            this.nodeCache.set(this.currentNode.id, cache);
            
            // If user cleared the key of an existing row, we might need re-render to handle state
            // mostly handled by delete button, but let's be safe
        } else {
            // New entry creation (filling empty row)
            if (currentKey || currentValue) {
                // Determine a safe key if empty
                const safeKey = currentKey || `key_${Date.now()}`;
                cache[safeKey] = currentValue;
                this.nodeCache.set(this.currentNode.id, cache);
                
                // We must re-render to establish this as a real row and add a new empty one
                // But we want to keep focus. 
                // Simple approach: re-render, then restore focus (tricky).
                // Better: Just set the data attributes and manually append a new row if needed?
                // Re-rendering is safest for consistency.
                this.renderOverlayData();
                
                // Restore focus? (Complex, skipping optimization for now unless requested)
                // Actually, let's just let it be "live" editing of the cache object
                // and only re-render if we need to add the NEW empty row.
                // We just converted the empty row to a real row.
                // So we need to add a new empty row at the bottom.
                
                // Let's implement full re-render for simplicity 
                // But finding the element to focus is important
                // We'll skip focus restoration for this step to keep it simple, checking if it annoys user
            }
        }
        
        // Auto-refresh logic:
        // Ideally we only re-render if the state structure changes (count of rows)
        // If we just edited values, we don't need re-render.
        // If we filled the empty row, we DO need re-render to add a new empty row.
        
        const wasEmptyRow = !originalKey;
        if (wasEmptyRow && (currentKey || currentValue)) {
             this.renderOverlayData();
             // Try to focus the same input in the now non-empty row (index = length - 2)
             const newRows = document.querySelectorAll('.cache-row');
             const targetRow = newRows[newRows.length - 2]; 
             if (targetRow) {
                 const selector = input.classList.contains('cache-key') ? '.cache-key' : '.cache-value';
                 const toFocus = targetRow.querySelector(selector);
                 if (toFocus) {
                     toFocus.focus();
                     // move cursor to end
                     const len = toFocus.value.length;
                     toFocus.setSelectionRange(len, len);
                 }
             }
        }
    }
    
    handleDataDelete(event) {
        const key = event.target.dataset.key;
        if (!key) return; // ignore delete on empty row
        
        const cache = this.nodeCache.get(this.currentNode.id) || {};
        delete cache[key];
        this.nodeCache.set(this.currentNode.id, cache);
        this.renderOverlayData();
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

    makeDraggable(element) {
        let isDragging = false;
        let startX, startY, initialLeft, initialTop;
        
        const dragHandle = element.querySelector('.drag-handle');
        
        // Only allow dragging from the specific handle or header
        if (!dragHandle) return;
        
        dragHandle.addEventListener('mousedown', (e) => {
            isDragging = true;
            startX = e.clientX;
            startY = e.clientY;
            initialLeft = element.offsetLeft;
            initialTop = element.offsetTop;
            element.classList.add('dragging');
            e.preventDefault();
        });
        
        document.addEventListener('mousemove', (e) => {
            if (!isDragging) return;
            
            const dx = e.clientX - startX;
            const dy = e.clientY - startY;
            
            element.style.left = `${initialLeft + dx}px`;
            element.style.top = `${initialTop + dy}px`;
        });
        
        document.addEventListener('mouseup', () => {
            if (isDragging) {
                isDragging = false;
                element.classList.remove('dragging');
            }
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
        let isDragging = false;
        let startX, startY, initialLeft, initialTop;
        
        const dragHandle = element.querySelector('.drag-handle') || element;
        
        dragHandle.addEventListener('mousedown', (e) => {
            isDragging = true;
            startX = e.clientX;
            startY = e.clientY;
            initialLeft = element.offsetLeft;
            initialTop = element.offsetTop;
            element.classList.add('dragging');
            e.preventDefault();
        });
        
        document.addEventListener('mousemove', (e) => {
            if (!isDragging) return;
            
            const dx = e.clientX - startX;
            const dy = e.clientY - startY;
            
            element.style.left = `${initialLeft + dx}px`;
            element.style.top = `${initialTop + dy}px`;
        });
        
        document.addEventListener('mouseup', () => {
            if (isDragging) {
                isDragging = false;
                element.classList.remove('dragging');
            }
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
        
        // Convert to array
        let entries = Object.entries(this.globalCache);
        
        // Always ensure one empty row at the end
        entries = entries.filter(([k, v]) => k.trim() !== '' || v.trim() !== '');
        entries.push(['', '']); 
        
        container.innerHTML = entries.map(([key, value], index) => {
            const isEmpty = key === '' && value === '';
            const isLast = index === entries.length - 1;
            const placeholderKey = isLast ? 'Add global key...' : 'Key';
            
            return `
            <table class="cache-table" style="margin-bottom:0">
            <tr class="cache-row ${isEmpty ? 'empty-row' : ''}">
                <td style="width: 35%;">
                    <textarea class="cache-key" placeholder="${placeholderKey}" data-field="key" data-original-key="${this.escapeHtml(key)}">${this.escapeHtml(key)}</textarea>
                </td>
                <td>
                    <textarea class="cache-value" placeholder="Value" data-field="value" data-key="${this.escapeHtml(key)}">${this.escapeHtml(value)}</textarea>
                </td>
                <td style="width: 20px;">
                    <button class="delete-cache-btn" data-key="${this.escapeHtml(key)}" style="${isEmpty ? 'visibility:hidden' : ''}">×</button>
                </td>
            </tr>
            </table>
        `}).join('');
        
        // Bind events
        container.querySelectorAll('.cache-key, .cache-value').forEach(textarea => {
            textarea.addEventListener('input', (e) => this.handleGlobalDataEdit(e));
        });
        
        container.querySelectorAll('.delete-cache-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.handleGlobalDataDelete(e);
            });
        });
    }

    handleGlobalDataEdit(event) {
        const input = event.target;
        // Find row inputs
        const row = input.closest('tr');
        const keyInput = row.querySelector('.cache-key');
        const valInput = row.querySelector('.cache-value');
        
        const originalKey = keyInput.dataset.originalKey;
        const currentKey = keyInput.value;
        const currentValue = valInput.value;
        
        const cache = this.globalCache;
        
        if (originalKey) {
            // Modification of existing entry
            if (currentKey !== originalKey) {
                const val = cache[originalKey];
                delete cache[originalKey];
                if (currentKey) cache[currentKey] = val;
                keyInput.dataset.originalKey = currentKey;
                valInput.dataset.key = currentKey;
                const delBtn = row.querySelector('.delete-cache-btn');
                if (delBtn) delBtn.dataset.key = currentKey;
            }
            if (currentKey && cache.hasOwnProperty(currentKey)) {
                cache[currentKey] = currentValue;
            }
        } else {
            // New entry creation
            if (currentKey || currentValue) {
                const safeKey = currentKey || `global_${Date.now()}`;
                cache[safeKey] = currentValue;
                this.renderGlobalCache();
            }
        }
        
        const wasEmptyRow = !originalKey;
        if (wasEmptyRow && (currentKey || currentValue)) {
             this.renderGlobalCache();
        }
    }
    
    handleGlobalDataDelete(event) {
        const key = event.target.dataset.key;
        if (!key) return;
        delete this.globalCache[key];
        this.renderGlobalCache();
    }
}

// Initialize on load
document.addEventListener('DOMContentLoaded', () => {
    const app = new FlowPlay();
    app.init();
});
