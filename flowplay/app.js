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
    document.addEventListener("mousemove", (e) => {
      if (!this.activeElement) return;

      const dx = e.clientX - this.startX;
      const dy = e.clientY - this.startY;

      this.activeElement.style.left = `${this.initialLeft + dx}px`;
      this.activeElement.style.top = `${this.initialTop + dy}px`;
    });

    document.addEventListener("mouseup", () => {
      if (this.activeElement) {
        this.activeElement.classList.remove("dragging");
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
    element.classList.add("dragging");
  },
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
    entries = entries.filter(([k, v]) => k.trim() !== "" || v.trim() !== "");
    entries.push(["", ""]);

    return entries
      .map(([key, value], index) => {
        const isEmpty = key === "" && value === "";
        const isLast = index === entries.length - 1;
        const placeholderKey = isLast ? placeholderPrefix : "Key";

        return `
            <div class="cache-row ${isEmpty ? "empty-row" : ""}">
                <textarea class="cache-key" placeholder="${placeholderKey}" data-field="key" data-original-key="${escapeHtml(
          key
        )}">${escapeHtml(key)}</textarea>
                <textarea class="cache-value" placeholder="Value" data-field="value" data-key="${escapeHtml(
                  key
                )}">${escapeHtml(value)}</textarea>
                <button class="delete-cache-btn" data-key="${escapeHtml(
                  key
                )}" style="${isEmpty ? "visibility:hidden" : ""}">×</button>
            </div>
        `;
      })
      .join("");
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
    const row = input.closest(".cache-row");
    const keyInput = row.querySelector(".cache-key");
    const valInput = row.querySelector(".cache-value");

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
        row.querySelector(".delete-cache-btn").dataset.key = currentKey;
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
  },
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
    this.historyIndex = -1; // Current position in history for time-travel
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

    // UI state
    this.searchResults = [];
    this.searchSelectedIndex = -1;
    this.selectedHistoryIndex = -1; // For keyboard navigation in history panel
    this.nodePreviewTooltip = null;
    this.edgeLabelTooltip = null;
    this.autoHideTimeout = null;
    this.lastInteractionTime = Date.now();

    // Settings (with defaults)
    this.settings = {
      showMiniMap: true,
      showProgressIndicator: true,
      showNodePreview: true,
      showEdgeLabels: true,
      darkMode: true,
      animatedEdges: true,
      autoHideControls: true,
      autoSaveState: true,
      confirmNavigation: false,
      defaultZoomLevel: 1.6,
    };
    this.userZoomLevel = null; // User-customized zoom level (set when manually zooming)
    this.loadSettings();

    // Bind methods
    this.handleZoom = this.handleZoom.bind(this);
  }

  async init() {
    try {
      this.showLoading(true);
      await this.loadFlowData();
      this.setupSVG();
      this.renderFlowchart();
      this.setupControls();
      this.setupOverlayControls();
      this.setupSearch();
      this.setupMiniMap();
      this.setupNodePreview();
      this.setupAutoHide();
      this.setupSettingsPanel();
      this.applySettings();
      this.start();
      this.showLoading(false);
    } catch (error) {
      console.error("Failed to initialize FlowPlay:", error);
      document.getElementById("flowchart-name").textContent =
        "Error loading flowchart";
      this.showLoading(false);
    }
  }

  showLoading(show) {
    let indicator = document.getElementById("loading-indicator");
    if (show) {
      if (!indicator) {
        indicator = document.createElement("div");
        indicator.id = "loading-indicator";
        indicator.innerHTML = `
                    <div class="loading-spinner"></div>
                    <div class="loading-text">Loading flowchart...</div>
                `;
        document.getElementById("app").appendChild(indicator);
      }
      indicator.style.display = "flex";
    } else if (indicator) {
      indicator.style.display = "none";
    }
  }

  async loadFlowData() {
    let errorMessage = "Failed to load flowchart";
    try {
      const response = await fetch("./complex_flow.json");
      if (!response.ok) {
        errorMessage = `Failed to load flowchart: ${response.statusText}`;
        this.flowData =
          typeof bundledFlowData !== "undefined" ? bundledFlowData : null;
        if (!this.flowData) {
          throw new Error(errorMessage);
        } else {
          console.log("Using bundled json data!");
        }
      } else {
        this.flowData = await response.json();
      }
    } catch (e) {
      this.flowData =
        typeof bundledFlowData !== "undefined" ? bundledFlowData : null;
      if (!this.flowData) {
        throw new Error(errorMessage);
      } else {
        console.log("Using bundled json data!");
      }
    }

    // Index nodes and edges
    this.flowData.nodes.forEach((node) => {
      this.nodes[node.id] = node;
    });
    this.flowData.edges.forEach((edge) => {
      this.edges[edge.id] = edge;
    });
    this.graph = this.flowData.graph;

    // Set title
    document.getElementById("flowchart-name").textContent = this.flowData.name;
  }

  setupSVG() {
    const container = document.getElementById("flowchart-container");
    const width = container.clientWidth;
    const height = container.clientHeight;

    this.svg = d3
      .select("#flowchart-svg")
      .attr("width", width)
      .attr("height", height);

    // Add defs for arrow markers
    const defs = this.svg.append("defs");

    // Normal arrow - refX adjusted to position arrow at end of line
    defs
      .append("marker")
      .attr("id", "arrow")
      .attr("viewBox", "0 -5 10 10")
      .attr("refX", 10)
      .attr("refY", 0)
      .attr("markerWidth", 8)
      .attr("markerHeight", 8)
      .attr("orient", "auto")
      .append("path")
      .attr("d", "M0,-4L10,0L0,4")
      .attr("class", "edge-arrow");

    // Incoming arrow (highlighted)
    defs
      .append("marker")
      .attr("id", "arrow-incoming")
      .attr("viewBox", "0 -5 10 10")
      .attr("refX", 10)
      .attr("refY", 0)
      .attr("markerWidth", 8)
      .attr("markerHeight", 8)
      .attr("orient", "auto")
      .append("path")
      .attr("d", "M0,-4L10,0L0,4")
      .attr("class", "edge-arrow incoming");

    // Create main group for zoom/pan
    this.g = this.svg.append("g").attr("class", "main-group");

    // Setup zoom behavior with filter to not zoom when over overlay
    this.zoom = d3
      .zoom()
      .scaleExtent([0.1, 4])
      .filter((event) => {
        // Don't zoom/pan when interacting with the overlay
        const overlay = document.getElementById("node-overlay");
        if (overlay && overlay.contains(event.target)) {
          return false;
        }
        return true;
      })
      .on("zoom", this.handleZoom);

    this.svg.call(this.zoom);
  }

  handleZoom(event) {
    this.g.attr("transform", event.transform);
    // Reposition overlay when zooming/panning
    this.positionOverlay();
    // Update minimap viewport
    this.updateMiniMapViewport();
    // Update zoom level indicator
    this.updateZoomLevel(event.transform.k);

    // Track user-initiated zooms (wheel/pinch) to remember preferred zoom level
    // sourceEvent exists for user-initiated zooms, not for programmatic zooms
    if (
      event.sourceEvent &&
      (event.sourceEvent.type === "wheel" ||
        event.sourceEvent.type === "touchmove")
    ) {
      // Debounce the zoom level tracking
      clearTimeout(this.zoomTrackTimeout);
      this.zoomTrackTimeout = setTimeout(() => {
        this.userZoomLevel = event.transform.k;
      }, 200);
    }
  }

  updateZoomLevel(scale) {
    const zoomLevel = document.getElementById("zoom-level");
    if (zoomLevel) {
      zoomLevel.textContent = `${Math.round(scale * 100)}%`;
    }
  }

  renderFlowchart() {
    // Use Dagre for proper hierarchical DAG layout (like Graphviz/Mermaid)
    const g = new dagre.graphlib.Graph();

    // Set graph properties - top-to-bottom layout (vertical)
    g.setGraph({
      rankdir: "LR", // Left to right
      nodesep: 200 * 2, // Horizontal separation between nodes (increased for spread)
      ranksep: 200 * 2, // Vertical separation between ranks
      marginx: 50,
      marginy: 50,
    });

    // Default edge label (required by Dagre)
    g.setDefaultEdgeLabel(() => ({}));

    // Add nodes to the graph
    this.flowData.nodes.forEach((node) => {
      g.setNode(node.id, {
        width: this.nodeWidth,
        height: this.nodeHeight,
        label: node.label,
      });
    });

    // Add edges to the graph
    this.flowData.edges.forEach((edge) => {
      g.setEdge(edge.source, edge.target);
    });

    // Compute the layout
    dagre.layout(g);

    // Copy positions back to our nodes index
    this.flowData.nodes.forEach((node) => {
      const dagreNode = g.node(node.id);
      this.nodes[node.id].x = dagreNode.x;
      this.nodes[node.id].y = dagreNode.y;
    });

    // Draw edges
    const edgeGroup = this.g.append("g").attr("class", "edges");

    // Draw edges using the positioned nodes - make them clickable
    this.flowData.edges.forEach((edge) => {
      const source = this.nodes[edge.source];
      const target = this.nodes[edge.target];

      // Calculate edge path
      const path = this.calculateEdgePath(source, target);

      // Create invisible wider hit area for easier clicking
      edgeGroup
        .append("path")
        .attr("class", "edge-hit-area")
        .attr("id", `edge-hit-${edge.id}`)
        .attr("d", path)
        .datum(edge)
        .style("cursor", "pointer")
        .style("stroke", "transparent")
        .style("stroke-width", "20")
        .style("fill", "none")
        .style("pointer-events", "stroke")
        .on("click", (event) => {
          event.stopPropagation();
          this.handleEdgeClick(edge);
        })
        .on("mouseenter", (event) => {
          this.handleEdgeHover(edge, event, true);
        })
        .on("mousemove", (event) => {
          this.updateTooltipPosition(event);
        })
        .on("mouseleave", () => {
          this.handleEdgeHover(edge, null, false);
        });

      // Visible edge path
      edgeGroup
        .append("path")
        .attr("class", "edge-path")
        .attr("id", `edge-${edge.id}`)
        .attr("d", path)
        .attr("marker-end", "url(#arrow)")
        .datum(edge)
        .style("pointer-events", "none");

      // Edge label
      if (edge.label) {
        const midX = (source.x + target.x) / 2;
        const midY = (source.y + target.y) / 2;

        edgeGroup
          .append("text")
          .attr("class", "edge-label")
          .attr("x", midX)
          .attr("y", midY - 8)
          .attr("text-anchor", "middle")
          .text(edge.label);
      }
    });

    // Draw nodes using our updated nodes index
    const nodeGroup = this.g.append("g").attr("class", "nodes");

    Object.values(this.nodes).forEach((node) => {
      const g = nodeGroup
        .append("g")
        .attr("class", "node-group")
        .attr("id", `node-${node.id}`)
        .attr("transform", `translate(${node.x}, ${node.y})`)
        .on("click", () => this.handleNodeClick(node))
        .on("mouseenter", (event) => {
          // Only show preview when not the current node
          if (!this.currentNode || node.id !== this.currentNode.id) {
            this.showNodePreview(node, event);
          }
        })
        .on("mousemove", (event) => {
          this.updateTooltipPosition(event);
        })
        .on("mouseleave", () => {
          this.hideNodePreview();
        })
        .on("dblclick", () => {
          // Double-click to re-zoom if current node, or navigate
          if (this.currentNode && node.id === this.currentNode.id) {
            // Always re-zoom on double-click of current node
            this.zoomToNode(node);
          } else {
            this.navigateToNode(node.id);
          }
        });

      // Collapsed node shape (visible when not selected)
      const collapsedGroup = g.append("g").attr("class", "node-collapsed");

      if (node.type === "DecisionNode") {
        const size = 50;
        collapsedGroup
          .append("polygon")
          .attr("class", `node-shape ${node.type}`)
          .attr("points", `0,-${size} ${size * 2},0 0,${size} -${size * 2},0`);
      } else {
        collapsedGroup
          .append("rect")
          .attr("class", `node-shape ${node.type}`)
          .attr("x", -this.nodeWidth / 2)
          .attr("y", -this.nodeHeight / 2)
          .attr("width", this.nodeWidth)
          .attr("height", this.nodeHeight)
          .attr(
            "rx",
            node.type === "StartNode" || node.type === "EndNode" ? 35 : 10
          );
      }

      // Node label for collapsed state
      const labelGroup = collapsedGroup
        .append("text")
        .attr("class", `node-label ${node.type}`)
        .attr("text-anchor", "middle");

      const maxCharsPerLine = 28;
      const words = node.label.split(" ");
      const lines = [];
      let currentLine = "";

      words.forEach((word) => {
        if ((currentLine + " " + word).trim().length <= maxCharsPerLine) {
          currentLine = (currentLine + " " + word).trim();
        } else {
          if (currentLine) lines.push(currentLine);
          currentLine = word;
        }
      });
      if (currentLine) lines.push(currentLine);

      const lineHeight = 16;
      const startY = -((lines.length - 1) * lineHeight) / 2;

      lines.forEach((line, i) => {
        labelGroup
          .append("tspan")
          .attr("x", 0)
          .attr("dy", i === 0 ? startY : lineHeight)
          .text(line);
      });
    });

    // Initial fit
    this.fitToView();
  }

  calculateEdgePath(source, target) {
    const dx = target.x - source.x;
    const dy = target.y - source.y;
    const angle = Math.atan2(dy, dx);

    // Calculate intersection points with node boundaries
    const sourcePoint = this.getNodeEdgePoint(source, angle);
    const targetPoint = this.getNodeEdgePoint(target, angle + Math.PI); // opposite direction

    // Curved path
    const midX = (sourcePoint.x + targetPoint.x) / 2;
    const midY = (sourcePoint.y + targetPoint.y) / 2;

    return `M${sourcePoint.x},${sourcePoint.y} Q${midX},${midY} ${targetPoint.x},${targetPoint.y}`;
  }

  /**
   * Calculate the point on the edge of a node where an edge should connect
   * Handles different node shapes: rectangle, rounded rect, and diamond
   */
  getNodeEdgePoint(node, angle) {
    const halfWidth = this.nodeWidth / 2;
    const halfHeight = this.nodeHeight / 2;

    if (node.type === "DecisionNode") {
      // Diamond shape: points at 0, 90, 180, 270 degrees
      // Diamond extends: left/right by size*2, top/bottom by size
      const size = 50;
      const diamondHalfWidth = size * 2;
      const diamondHalfHeight = size;

      // Normalize angle to 0-2π
      let a = angle;
      while (a < 0) a += 2 * Math.PI;
      while (a >= 2 * Math.PI) a -= 2 * Math.PI;

      // Calculate intersection with diamond edges
      // Diamond vertices: right(2s,0), bottom(0,s), left(-2s,0), top(0,-s)
      const cos = Math.cos(a);
      const sin = Math.sin(a);

      // Parameter t where ray intersects diamond edge
      let t;
      if (cos >= 0 && sin >= 0) {
        // Quadrant 1: edge from right to bottom
        t = 1 / (cos / diamondHalfWidth + sin / diamondHalfHeight);
      } else if (cos < 0 && sin >= 0) {
        // Quadrant 2: edge from bottom to left
        t = 1 / (-cos / diamondHalfWidth + sin / diamondHalfHeight);
      } else if (cos < 0 && sin < 0) {
        // Quadrant 3: edge from left to top
        t = 1 / (-cos / diamondHalfWidth - sin / diamondHalfHeight);
      } else {
        // Quadrant 4: edge from top to right
        t = 1 / (cos / diamondHalfWidth - sin / diamondHalfHeight);
      }

      return {
        x: node.x + t * cos,
        y: node.y + t * sin,
      };
    } else {
      // Rectangle (with optional rounded corners - treated as rect for edge calculation)
      const cos = Math.cos(angle);
      const sin = Math.sin(angle);

      // Find intersection with rectangle boundary
      // Check which edge the ray hits first
      let tx = Infinity,
        ty = Infinity;

      if (cos !== 0) {
        tx = (cos > 0 ? halfWidth : -halfWidth) / cos;
      }
      if (sin !== 0) {
        ty = (sin > 0 ? halfHeight : -halfHeight) / sin;
      }

      const t = Math.min(Math.abs(tx), Math.abs(ty));

      return {
        x: node.x + t * cos,
        y: node.y + t * sin,
      };
    }
  }

  truncateLabel(label, maxLength) {
    if (label.length <= maxLength) return label;
    return label.substring(0, maxLength - 2) + "...";
  }

  setupControls() {
    document
      .getElementById("restart-btn")
      .addEventListener("click", () => this.restart());
    document.getElementById("zoom-in").addEventListener("click", () => {
      this.zoomIn();
      // Remember user's zoom preference after a short delay
      setTimeout(() => {
        const transform = d3.zoomTransform(this.svg.node());
        this.userZoomLevel = transform.k;
      }, 350);
    });
    document.getElementById("zoom-out").addEventListener("click", () => {
      this.zoomOut();
      // Remember user's zoom preference after a short delay
      setTimeout(() => {
        const transform = d3.zoomTransform(this.svg.node());
        this.userZoomLevel = transform.k;
      }, 350);
    });
    document
      .getElementById("fit-view")
      .addEventListener("click", () => this.fitToView());

    // Zoom to current node button
    const zoomToNodeBtn = document.getElementById("zoom-to-node");
    if (zoomToNodeBtn) {
      zoomToNodeBtn.addEventListener("click", () => this.zoomToCurrentNode());
    }

    // Export button
    const exportBtn = document.getElementById("export-btn");
    if (exportBtn) {
      exportBtn.addEventListener("click", () => this.exportState());
    }

    // Zoom level click to reset
    const zoomLevel = document.getElementById("zoom-level");
    if (zoomLevel) {
      zoomLevel.addEventListener("click", () => {
        this.userZoomLevel = null; // Reset to default zoom level
        this.svg
          .transition()
          .duration(300)
          .call(this.zoom.scaleTo, this.settings.defaultZoomLevel);
      });
    }

    // Double-click on flowchart container to reset zoom level
    const container = document.getElementById("flowchart-container");
    if (container) {
      container.addEventListener("dblclick", (e) => {
        // Don't reset if clicking on a node or the overlay
        if (
          e.target.closest(".node-group") ||
          e.target.closest("#node-overlay")
        ) {
          return;
        }
        // Reset user zoom level to default
        this.userZoomLevel = null;
        if (this.currentNode) {
          this.zoomToNode(this.currentNode);
        }
      });
    }

    // Help panel toggle
    const helpBtn = document.getElementById("help-btn");
    const shortcutsPanel = document.getElementById("shortcuts-panel");
    if (helpBtn && shortcutsPanel) {
      helpBtn.addEventListener("click", () => {
        shortcutsPanel.classList.toggle("hidden");
        helpBtn.classList.toggle("active");
      });
    }

    // Key bindings - extended for better navigation
    document.addEventListener("keydown", (e) => {
      // Don't capture when typing in inputs
      if (e.target.tagName === "TEXTAREA" || e.target.tagName === "INPUT")
        return;

      switch (e.key.toLowerCase()) {
        case "r":
          this.restart();
          break;
        case "=":
        case "+":
          this.zoomIn();
          break;
        case "-":
          this.zoomOut();
          break;
        case "f":
          this.fitToView();
          break;
        case "z":
          this.zoomToCurrentNode();
          break;
        case "h":
          this.toggleHistoryPanel();
          break;

        // Navigation shortcuts
        case "escape":
          // Close history panel if open, otherwise zoom out
          if (
            !document
              .getElementById("history-panel")
              ?.classList.contains("hidden")
          ) {
            this.toggleHistoryPanel();
          } else {
            this.zoomOut();
          }
          break;
        case "backspace":
        case "b":
          // Go back to previous node
          e.preventDefault();
          this.goBack();
          break;

        // Number keys 1-9 for selecting edges (or history items if panel open)
        case "1":
        case "2":
        case "3":
        case "4":
        case "5":
        case "6":
        case "7":
        case "8":
        case "9":
          if (this.isHistoryPanelOpen()) {
            this.selectHistoryByNumber(parseInt(e.key));
          } else {
            this.selectEdgeByNumber(parseInt(e.key));
          }
          break;

        // Arrow keys for edge selection (or history navigation if panel open)
        case "arrowdown":
        case "arrowright":
          e.preventDefault();
          if (this.isHistoryPanelOpen()) {
            this.selectNextHistoryItem();
          } else {
            this.selectNextEdge();
          }
          break;
        case "arrowup":
        case "arrowleft":
          e.preventDefault();
          if (this.isHistoryPanelOpen()) {
            this.selectPrevHistoryItem();
          } else {
            this.selectPrevEdge();
          }
          break;
        case "enter":
          if (this.isHistoryPanelOpen()) {
            this.activateSelectedHistoryItem();
          } else {
            this.activateSelectedEdge();
          }
          break;
        case "?":
          // Toggle help panel
          const shortcutsPanel = document.getElementById("shortcuts-panel");
          const helpBtn = document.getElementById("help-btn");
          if (shortcutsPanel) {
            shortcutsPanel.classList.toggle("hidden");
            helpBtn?.classList.toggle("active");
          }
          break;
      }
    });

    // Track currently highlighted edge for keyboard nav
    this.selectedEdgeIndex = -1;

    this.setupGlobalCache();
    this.setupHistoryPanel();
  }

  setupOverlayControls() {
    // No close button - user uses Escape or Z to zoom out
  }

  setupHistoryPanel() {
    const toggle = document.getElementById("history-toggle");
    const panel = document.getElementById("history-panel");
    const closeBtn = document.getElementById("history-panel-close");

    if (toggle && panel) {
      toggle.addEventListener("click", () => this.toggleHistoryPanel());
    }

    if (closeBtn) {
      closeBtn.addEventListener("click", () => this.toggleHistoryPanel());
    }
  }

  toggleHistoryPanel() {
    const panel = document.getElementById("history-panel");
    const toggle = document.getElementById("history-toggle");
    if (!panel) return;

    const isHidden = panel.classList.contains("hidden");
    if (isHidden) {
      panel.classList.remove("hidden");
      toggle?.classList.add("active");
      this.updateHistory();
      // Set keyboard focus to current history item
      this.selectedHistoryIndex = this.historyIndex;
      this.highlightHistoryItem(this.selectedHistoryIndex);
    } else {
      panel.classList.add("hidden");
      toggle?.classList.remove("active");
      this.selectedHistoryIndex = -1; // Reset selection when closing
    }
  }

  isHistoryPanelOpen() {
    const panel = document.getElementById("history-panel");
    return panel && !panel.classList.contains("hidden");
  }

  selectNextHistoryItem() {
    if (this.history.length === 0) return;
    if (
      this.selectedHistoryIndex === undefined ||
      this.selectedHistoryIndex < 0
    ) {
      this.selectedHistoryIndex = 0;
    } else {
      this.selectedHistoryIndex = Math.min(
        this.selectedHistoryIndex + 1,
        this.history.length - 1
      );
    }
    this.highlightHistoryItem(this.selectedHistoryIndex);
  }

  selectPrevHistoryItem() {
    if (this.history.length === 0) return;
    if (
      this.selectedHistoryIndex === undefined ||
      this.selectedHistoryIndex < 0
    ) {
      this.selectedHistoryIndex = this.history.length - 1;
    } else {
      this.selectedHistoryIndex = Math.max(this.selectedHistoryIndex - 1, 0);
    }
    this.highlightHistoryItem(this.selectedHistoryIndex);
  }

  selectHistoryByNumber(num) {
    const index = num - 1; // Convert 1-based to 0-based
    if (index >= 0 && index < this.history.length) {
      this.selectedHistoryIndex = index;
      this.highlightHistoryItem(index);
      // Immediately navigate when pressing a number
      this.activateSelectedHistoryItem();
    }
  }

  highlightHistoryItem(index) {
    const container = document.getElementById("history-list");
    if (!container) return;

    // Remove previous keyboard selection
    container.querySelectorAll(".history-list-item").forEach((item, i) => {
      item.classList.remove("keyboard-selected");
      if (i === index) {
        item.classList.add("keyboard-selected");
        item.scrollIntoView({ behavior: "smooth", block: "nearest" });
      }
    });
  }

  activateSelectedHistoryItem() {
    if (
      this.selectedHistoryIndex !== undefined &&
      this.selectedHistoryIndex >= 0 &&
      this.selectedHistoryIndex < this.history.length
    ) {
      this.timeTravel(this.selectedHistoryIndex);
    }
  }

  setupGlobalCache() {
    // Toggle button
    const toggle = document.getElementById("global-cache-toggle");
    const panel = document.getElementById("global-cache-panel");

    if (toggle && panel) {
      toggle.addEventListener("click", () => {
        const isHidden = panel.classList.contains("hidden");
        if (isHidden) {
          panel.classList.remove("hidden");
          toggle.classList.add("active");
          this.renderGlobalCache();
        } else {
          panel.classList.add("hidden");
          toggle.classList.remove("active");
        }
      });

      // Make global cache panel draggable
      this.makeDraggableFromAnywhere(panel);
    }
  }

  // =========================================
  // SEARCH FUNCTIONALITY
  // =========================================
  setupSearch() {
    const searchInput = document.getElementById("node-search");
    const searchResults = document.getElementById("search-results");
    if (!searchInput || !searchResults) return;

    // Keyboard shortcut
    document.addEventListener("keydown", (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "k") {
        e.preventDefault();
        searchInput.focus();
        searchInput.select();
      }
    });

    searchInput.addEventListener("input", () => {
      this.performSearch(searchInput.value);
    });

    searchInput.addEventListener("keydown", (e) => {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        this.searchSelectedIndex = Math.min(
          this.searchSelectedIndex + 1,
          this.searchResults.length - 1
        );
        this.renderSearchResults();
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        this.searchSelectedIndex = Math.max(this.searchSelectedIndex - 1, 0);
        this.renderSearchResults();
      } else if (e.key === "Enter") {
        e.preventDefault();
        if (
          this.searchSelectedIndex >= 0 &&
          this.searchResults[this.searchSelectedIndex]
        ) {
          this.navigateToNode(this.searchResults[this.searchSelectedIndex].id);
          this.clearSearch();
        }
      } else if (e.key === "Escape") {
        this.clearSearch();
        searchInput.blur();
      }
    });

    searchInput.addEventListener("blur", () => {
      // Delay to allow click on results
      setTimeout(() => this.clearSearch(), 200);
    });
  }

  performSearch(query) {
    const searchResults = document.getElementById("search-results");
    if (!query.trim()) {
      searchResults.classList.add("hidden");
      this.searchResults = [];
      return;
    }

    const lowerQuery = query.toLowerCase();
    this.searchResults = Object.values(this.nodes)
      .filter(
        (node) =>
          node.label.toLowerCase().includes(lowerQuery) ||
          node.id.toLowerCase().includes(lowerQuery) ||
          (node.metadata?.description || "").toLowerCase().includes(lowerQuery)
      )
      .slice(0, 10);

    this.searchSelectedIndex = this.searchResults.length > 0 ? 0 : -1;
    this.renderSearchResults();
  }

  renderSearchResults() {
    const searchResults = document.getElementById("search-results");

    if (this.searchResults.length === 0) {
      searchResults.innerHTML =
        '<div class="search-no-results">No nodes found</div>';
      searchResults.classList.remove("hidden");
      return;
    }

    searchResults.innerHTML = this.searchResults
      .map(
        (node, i) => `
            <div class="search-result-item ${
              i === this.searchSelectedIndex ? "selected" : ""
            }" data-node-id="${node.id}">
                <div class="node-type-indicator" style="background: var(--node-${
                  node.type === "StartNode"
                    ? "start"
                    : node.type === "EndNode"
                    ? "end"
                    : node.type === "DecisionNode"
                    ? "decision"
                    : "process"
                })"></div>
                <span class="node-name">${this.escapeHtml(node.label)}</span>
                <span class="node-id">${node.id}</span>
            </div>
        `
      )
      .join("");

    searchResults.querySelectorAll(".search-result-item").forEach((item) => {
      item.addEventListener("click", () => {
        this.navigateToNode(item.dataset.nodeId);
        this.clearSearch();
      });
    });

    searchResults.classList.remove("hidden");
  }

  clearSearch() {
    const searchInput = document.getElementById("node-search");
    const searchResults = document.getElementById("search-results");
    if (searchInput) searchInput.value = "";
    if (searchResults) searchResults.classList.add("hidden");
    this.searchResults = [];
    this.searchSelectedIndex = -1;
  }

  // =========================================
  // MINI-MAP
  // =========================================
  setupMiniMap() {
    const miniMap = document.getElementById("mini-map");
    const canvas = document.getElementById("mini-map-canvas");
    if (!miniMap || !canvas) return;

    this.miniMapCanvas = canvas;
    this.miniMapCtx = canvas.getContext("2d");
    this.miniMapDragging = false;

    // Set canvas size
    canvas.width = 150;
    canvas.height = 100;

    // Click and drag to pan the camera in real-time
    miniMap.addEventListener("mousedown", (e) => {
      const rect = canvas.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      this.miniMapDragging = true;
      this.miniMapPanTo(x, y);
    });

    // Drag to pan in real-time
    miniMap.addEventListener("mousemove", (e) => {
      if (!this.miniMapDragging) return;
      const rect = canvas.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      this.miniMapPanTo(x, y);
    });

    document.addEventListener("mouseup", () => {
      this.miniMapDragging = false;
    });

    // Initial render
    setTimeout(() => this.renderMiniMap(), 100);
  }

  renderMiniMap() {
    if (!this.miniMapCtx || !this.flowData) return;

    const ctx = this.miniMapCtx;
    const canvas = this.miniMapCanvas;
    const width = canvas.width;
    const height = canvas.height;

    // Clear
    ctx.clearRect(0, 0, width, height);

    // Get bounds
    let minX = Infinity,
      minY = Infinity,
      maxX = -Infinity,
      maxY = -Infinity;
    this.flowData.nodes.forEach((node) => {
      minX = Math.min(minX, node.x);
      minY = Math.min(minY, node.y);
      maxX = Math.max(maxX, node.x);
      maxY = Math.max(maxY, node.y);
    });

    const graphWidth = maxX - minX + this.nodeWidth * 2;
    const graphHeight = maxY - minY + this.nodeHeight * 2;

    // Calculate scale to fit
    const scale = Math.min(width / graphWidth, height / graphHeight) * 0.9;
    const offsetX =
      (width - graphWidth * scale) / 2 - minX * scale + this.nodeWidth * scale;
    const offsetY =
      (height - graphHeight * scale) / 2 -
      minY * scale +
      this.nodeHeight * scale;

    this.miniMapScale = scale;
    this.miniMapOffsetX = offsetX;
    this.miniMapOffsetY = offsetY;

    // Draw edges
    ctx.strokeStyle = "rgba(255, 255, 255, 0.15)";
    ctx.lineWidth = 0.5;
    this.flowData.edges.forEach((edge) => {
      const source = this.nodes[edge.source];
      const target = this.nodes[edge.target];
      ctx.beginPath();
      ctx.moveTo(source.x * scale + offsetX, source.y * scale + offsetY);
      ctx.lineTo(target.x * scale + offsetX, target.y * scale + offsetY);
      ctx.stroke();
    });

    // Draw nodes
    this.flowData.nodes.forEach((node) => {
      const x = node.x * scale + offsetX;
      const y = node.y * scale + offsetY;
      const w = this.nodeWidth * scale * 0.8;
      const h = this.nodeHeight * scale * 0.8;

      // Color based on type and state
      if (this.currentNode && node.id === this.currentNode.id) {
        ctx.fillStyle = "#5b5fc7";
      } else if (this.visitedNodes.has(node.id)) {
        ctx.fillStyle = "#2d9c6f";
      } else {
        ctx.fillStyle = "rgba(255, 255, 255, 0.3)";
      }

      ctx.beginPath();
      ctx.roundRect(x - w / 2, y - h / 2, w, h, 2);
      ctx.fill();
    });

    // Draw viewport indicator
    this.updateMiniMapViewport();
  }

  updateMiniMapViewport() {
    const viewport = document.getElementById("mini-map-viewport");
    if (!viewport || !this.svg) return;

    const transform = d3.zoomTransform(this.svg.node());
    const container = document.getElementById("flowchart-container");

    const viewWidth = container.clientWidth / transform.k;
    const viewHeight = container.clientHeight / transform.k;
    const viewX = -transform.x / transform.k;
    const viewY = -transform.y / transform.k;

    const scale = this.miniMapScale || 0.1;
    const offsetX = this.miniMapOffsetX || 0;
    const offsetY = this.miniMapOffsetY || 0;

    viewport.style.left = `${viewX * scale + offsetX}px`;
    viewport.style.top = `${viewY * scale + offsetY}px`;
    viewport.style.width = `${viewWidth * scale}px`;
    viewport.style.height = `${viewHeight * scale}px`;
  }

  miniMapPanTo(x, y) {
    if (!this.miniMapScale) return;

    // Convert minimap coordinates to graph coordinates
    const graphX = (x - this.miniMapOffsetX) / this.miniMapScale;
    const graphY = (y - this.miniMapOffsetY) / this.miniMapScale;

    // Get current transform
    const transform = d3.zoomTransform(this.svg.node());
    const container = document.getElementById("flowchart-container");

    // Calculate new translation to center the clicked point
    const centerX = container.clientWidth / 2;
    const centerY = container.clientHeight / 2;

    const newX = centerX - graphX * transform.k;
    const newY = centerY - graphY * transform.k;

    // Apply transform immediately (no transition for real-time feel)
    this.svg.call(
      this.zoom.transform,
      d3.zoomIdentity.translate(newX, newY).scale(transform.k)
    );
  }

  // =========================================
  // NODE PREVIEW TOOLTIP
  // =========================================
  setupNodePreview() {
    // Create tooltip element
    this.nodePreviewTooltip = document.createElement("div");
    this.nodePreviewTooltip.className = "node-preview-tooltip";
    this.nodePreviewTooltip.style.display = "none";
    document.body.appendChild(this.nodePreviewTooltip);

    // Create edge label tooltip
    this.edgeLabelTooltip = document.createElement("div");
    this.edgeLabelTooltip.className = "edge-label-tooltip";
    this.edgeLabelTooltip.style.display = "none";
    document.body.appendChild(this.edgeLabelTooltip);
  }

  showNodePreview(node, event) {
    if (!this.settings.showNodePreview) return;

    const tooltip = this.nodePreviewTooltip;
    if (!tooltip) return;

    const description = node.metadata?.description || "";
    const shortDesc =
      description.length > 150
        ? description.substring(0, 150) + "..."
        : description;

    tooltip.innerHTML = `
            <div class="preview-header">
                <span class="preview-badge ${node.type}">${this.formatNodeType(
      node.type
    )}</span>
                <span class="preview-title">${this.escapeHtml(
                  node.label
                )}</span>
            </div>
            ${
              shortDesc
                ? `<div class="preview-description">${this.escapeHtml(
                    shortDesc
                  )}</div>`
                : ""
            }
            <div class="preview-hint">Click to navigate</div>
        `;

    tooltip.style.display = "block";
    this.clampToViewport(tooltip, event.clientX, event.clientY, 15);
  }

  hideNodePreview() {
    if (this.nodePreviewTooltip) {
      this.nodePreviewTooltip.style.display = "none";
    }
  }

  showEdgeLabelTooltip(edge, event) {
    const tooltip = this.edgeLabelTooltip;
    if (!tooltip || !edge.label) return;

    tooltip.textContent = edge.label;
    tooltip.style.display = "block";
    this.clampToViewport(tooltip, event.clientX, event.clientY, 10);
  }

  hideEdgeLabelTooltip() {
    if (this.edgeLabelTooltip) {
      this.edgeLabelTooltip.style.display = "none";
    }
  }

  /**
   * Show a combined tooltip with edge label and target node preview
   */
  showEdgeNodeTooltip(edge, targetNode, event) {
    if (!this.settings.showNodePreview) return;

    // Use the nodePreviewTooltip for the combined tooltip
    const tooltip = this.nodePreviewTooltip;
    if (!tooltip) return;

    const description = targetNode.metadata?.description || "";
    const shortDesc =
      description.length > 150
        ? description.substring(0, 150) + "..."
        : description;

    // Build combined tooltip content
    let labelHtml = "";
    if (edge.label) {
      labelHtml = `<div class="edge-label-preview">${this.escapeHtml(
        edge.label
      )}</div>`;
    }

    tooltip.innerHTML = `
            ${labelHtml}
            <div class="preview-header">
                <span class="preview-badge ${
                  targetNode.type
                }">${this.formatNodeType(targetNode.type)}</span>
                <span class="preview-title">${this.escapeHtml(
                  targetNode.label
                )}</span>
            </div>
            ${
              shortDesc
                ? `<div class="preview-description">${this.escapeHtml(
                    shortDesc
                  )}</div>`
                : ""
            }
            <div class="preview-hint">Click to navigate</div>
        `;

    tooltip.style.display = "block";
    this.clampToViewport(tooltip, event.clientX, event.clientY, 15);
  }

  hideEdgeNodeTooltip() {
    if (this.nodePreviewTooltip) {
      this.nodePreviewTooltip.style.display = "none";
    }
    if (this.edgeLabelTooltip) {
      this.edgeLabelTooltip.style.display = "none";
    }
  }

  // =========================================
  // EDGE & NODE INTERACTION HELPERS
  // =========================================

  handleEdgeClick(edge) {
    // If clicking an edge connected to current node, go to the OTHER node
    // Otherwise go to target (follow arrow direction)
    if (this.currentNode) {
      if (edge.source === this.currentNode.id) {
        // Outgoing edge: go to target
        this.navigateToNode(edge.target);
      } else if (edge.target === this.currentNode.id) {
        // Incoming edge: go to source
        this.navigateToNode(edge.source);
      } else {
        // Edge not connected to current: go to target
        this.navigateToNode(edge.target);
      }
    } else {
      this.navigateToNode(edge.target);
    }
  }

  handleEdgeHover(edge, event, isEntering) {
    if (isEntering) {
      // Determine which node to preview (target of the edge, or the OTHER node if connected to current)
      let previewNodeId = edge.target; // Default: follow arrow direction
      if (this.currentNode) {
        if (edge.source === this.currentNode.id) {
          previewNodeId = edge.target;
        } else if (edge.target === this.currentNode.id) {
          previewNodeId = edge.source;
        }
      }

      const previewNode = this.nodes[previewNodeId];
      if (previewNode) {
        // Show combined tooltip with edge label and node preview
        this.showEdgeNodeTooltip(edge, previewNode, event);
      }

      // Highlight the edge
      d3.select(`#edge-${edge.id}`).classed("hovered", true);
    } else {
      this.hideEdgeNodeTooltip();
      d3.select(`#edge-${edge.id}`).classed("hovered", false);
    }
  }

  handleNodeClick(node) {
    // If clicking on the current node while zoomed out, re-zoom to it
    if (this.currentNode && node.id === this.currentNode.id) {
      const transform = d3.zoomTransform(this.svg.node());
      // Check if we're zoomed out (scale below a threshold)
      if (transform.k < 1.2) {
        this.zoomToNode(node);
        return;
      }
    }
    this.navigateToNode(node.id);
  }

  /**
   * Position a tooltip/popup element so it stays within the viewport
   */
  clampToViewport(element, x, y, offset = 15) {
    const rect = element.getBoundingClientRect();
    const width = rect.width || element.offsetWidth || 200;
    const height = rect.height || element.offsetHeight || 100;

    let left = x + offset;
    let top = y + offset;

    // Clamp right edge
    if (left + width > window.innerWidth - 10) {
      left = x - width - offset;
    }
    // Clamp left edge
    if (left < 10) {
      left = 10;
    }
    // Clamp bottom edge
    if (top + height > window.innerHeight - 10) {
      top = y - height - offset;
    }
    // Clamp top edge
    if (top < 10) {
      top = 10;
    }

    element.style.left = `${left}px`;
    element.style.top = `${top}px`;
  }

  updateTooltipPosition(event) {
    if (
      this.nodePreviewTooltip &&
      this.nodePreviewTooltip.style.display !== "none"
    ) {
      this.clampToViewport(
        this.nodePreviewTooltip,
        event.clientX,
        event.clientY,
        15
      );
    }
    if (
      this.edgeLabelTooltip &&
      this.edgeLabelTooltip.style.display !== "none"
    ) {
      this.clampToViewport(
        this.edgeLabelTooltip,
        event.clientX,
        event.clientY,
        10
      );
    }
  }

  // =========================================
  // AUTO-HIDE CONTROLS
  // =========================================
  setupAutoHide() {
    const controls = document.getElementById("controls");
    if (!controls) return;

    const resetAutoHide = () => {
      this.lastInteractionTime = Date.now();
      controls.classList.remove("auto-hidden");

      clearTimeout(this.autoHideTimeout);
      this.autoHideTimeout = setTimeout(() => {
        const elapsed = Date.now() - this.lastInteractionTime;
        if (elapsed >= 5000) {
          controls.classList.add("auto-hidden");
        }
      }, 5000);
    };

    // Reset on any interaction
    document.addEventListener("mousemove", resetAutoHide);
    document.addEventListener("keydown", resetAutoHide);
    document.addEventListener("click", resetAutoHide);

    // Initial timer
    resetAutoHide();
  }

  // =========================================
  // PROGRESS TRACKING
  // =========================================
  updateProgress() {
    const progressText = document.getElementById("progress-text");
    const progressFill = document.getElementById("progress-fill");
    if (!progressText || !progressFill) return;

    const total = this.flowData.nodes.length;
    const visited = this.visitedNodes.size;

    progressText.textContent = `${visited} / ${total} visited`;
    progressFill.style.width = `${(visited / total) * 100}%`;
  }

  start() {
    // Try to restore saved state first
    if (this.loadState()) {
      return;
    }

    // Otherwise, find start node
    const startNode = this.flowData.nodes.find((n) => n.type === "StartNode");
    if (startNode) {
      this.navigateToNode(startNode.id);
    }
  }

  restart() {
    // Clear state
    this.history = [];
    this.historyIndex = -1;
    this.visitedNodes.clear();
    this.nodeCache.clear();
    this.userZoomLevel = null; // Reset custom zoom

    // Clear saved state
    this.clearSavedState();

    // Reset visual state
    this.g
      .selectAll(".node-group")
      .classed("current", false)
      .classed("visited", false);
    this.g.selectAll(".node-collapsed").style("opacity", 1);
    this.g
      .selectAll(".edge-path")
      .classed("incoming", false)
      .classed("outgoing", false);

    // Hide overlay
    document.getElementById("node-overlay").classList.add("hidden");

    // Start fresh
    this.start();
  }

  navigateToNode(nodeId) {
    const node = this.nodes[nodeId];
    if (!node) return;

    // Fork history: only truncate if navigating to a DIFFERENT node than what's next in history
    if (this.historyIndex < this.history.length - 1) {
      // Check if next item in history is the same node we're going to
      if (this.history[this.historyIndex + 1] === nodeId) {
        // Same node - just move forward in history without adding
        this.historyIndex = this.historyIndex + 1;
      } else {
        // Different node - truncate future and add new path
        this.history = this.history.slice(0, this.historyIndex + 1);
        this.history.push(nodeId);
        this.historyIndex = this.history.length - 1;
      }
    } else {
      // At the end of history, add new node
      this.history.push(nodeId);
      this.historyIndex = this.history.length - 1;
    }

    // Use shared navigation logic
    this.goToNode(node, true);
  }

  /**
   * Core navigation function - handles all the visual/state updates for going to a node
   * @param {Object} node - The node object to navigate to
   * @param {boolean} addToVisited - Whether to mark the previous node as visited
   */
  goToNode(node, addToVisited = true) {
    // Reset keyboard edge selection to first edge
    this.selectedEdgeIndex = 0;

    // Hide overlay during transition
    document.getElementById("node-overlay").classList.add("hidden");

    // Hide node preview tooltip
    this.hideNodePreview();

    // Restore visibility of previous node's collapsed shape and reset edge paths
    if (this.currentNode) {
      d3.select(`#node-${this.currentNode.id} .node-collapsed`).style(
        "opacity",
        1
      );
      if (addToVisited) {
        this.visitedNodes.add(this.currentNode.id);
      }
      d3.select(`#node-${this.currentNode.id}`)
        .classed("current", false)
        .classed("visited", true);
      // Reset edge paths for the old current node
      this.resetEdgesForNode(this.currentNode.id);
    }

    this.currentNode = node;

    // Update visual state
    d3.select(`#node-${node.id}`).classed("current", true);

    // Highlight edges
    this.updateEdgeHighlights();

    // Update UI content (before zoom so it's ready when zoom completes)
    this.updateCurrentNodePanel();
    this.updateHistory();
    this.updateProgress();
    this.renderMiniMap();

    // Save state to localStorage
    this.saveState();

    // Zoom to node (overlay shown after zoom completes)
    this.zoomToNode(node);
  }

  updateEdgeHighlights() {
    // Reset all edges
    this.g
      .selectAll(".edge-path")
      .classed("incoming", false)
      .classed("outgoing", false)
      .attr("marker-end", "url(#arrow)");

    if (!this.currentNode) return;

    // Highlight incoming edges
    const incomingEdgeIds = this.graph.incomingEdges[this.currentNode.id] || [];
    incomingEdgeIds.forEach((edgeId) => {
      d3.select(`#edge-${edgeId}`)
        .classed("incoming", true)
        .attr("marker-end", "url(#arrow-incoming)");
    });

    // Highlight outgoing edges
    const outgoingEdgeIds = this.graph.outgoingEdges[this.currentNode.id] || [];
    outgoingEdgeIds.forEach((edgeId) => {
      d3.select(`#edge-${edgeId}`).classed("outgoing", true);
    });
  }

  zoomToNode(node) {
    const container = document.getElementById("flowchart-container");
    const width = container.clientWidth;
    const height = container.clientHeight;

    // Use a fixed zoom level for consistency across all nodes
    // User can override this by manually zooming, which sets userZoomLevel
    let targetScale = this.userZoomLevel || this.settings.defaultZoomLevel;

    // Clamp scale to reasonable limits
    targetScale = Math.max(0.4, Math.min(targetScale, 4.0));

    // Center node in viewport
    const centerX = width / 2;
    const centerY = height / 2;

    // Calculate translation to center the node
    const x = centerX - node.x * targetScale;
    const y = centerY - node.y * targetScale;

    this.svg
      .transition()
      .duration(600)
      .call(
        this.zoom.transform,
        d3.zoomIdentity.translate(x, y).scale(targetScale)
      )
      .on("end", () => {
        // Position and show overlay after zoom completes
        this.positionOverlay();
      });
  }

  positionOverlay() {
    if (!this.currentNode) return;

    const overlay = document.getElementById("node-overlay");

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
    overlay.style.transformOrigin = "center center";
    overlay.classList.remove("hidden");

    // Hide the collapsed SVG node so only overlay shows
    d3.select(`#node-${this.currentNode.id} .node-collapsed`).style(
      "opacity",
      0
    );

    // Auto-select first edge button for keyboard navigation
    const buttons = document.querySelectorAll("#overlay-actions .edge-btn");
    if (buttons.length > 0 && this.selectedEdgeIndex >= 0) {
      this.highlightEdgeButton(buttons);
    }

    // Recalculate edge positions for the expanded overlay size
    this.updateEdgesForExpandedNode(overlay);
  }

  /**
   * Update edge paths to connect to the expanded overlay instead of the collapsed node
   */
  updateEdgesForExpandedNode(overlay) {
    if (!this.currentNode) return;

    // Get overlay dimensions and convert to SVG coordinate space
    // The overlay is scaled by transform.k / 1.6, so in SVG space it's overlaySize / 1.6
    const overlayWidth = overlay.offsetWidth / 1.6;
    const overlayHeight = overlay.offsetHeight / 1.6;

    const nodeId = this.currentNode.id;

    // Get all edges connected to the current node
    const incomingEdgeIds = this.graph.incomingEdges[nodeId] || [];
    const outgoingEdgeIds = this.graph.outgoingEdges[nodeId] || [];

    // Update incoming edges (target is current node)
    incomingEdgeIds.forEach((edgeId) => {
      const edge = this.edges[edgeId];
      const source = this.nodes[edge.source];
      const path = this.calculateEdgePathWithExpandedTarget(
        source,
        this.currentNode,
        overlayWidth,
        overlayHeight
      );

      d3.select(`#edge-${edgeId}`).attr("d", path);
      d3.select(`#edge-hit-${edgeId}`).attr("d", path);
    });

    // Update outgoing edges (source is current node)
    outgoingEdgeIds.forEach((edgeId) => {
      const edge = this.edges[edgeId];
      const target = this.nodes[edge.target];
      const path = this.calculateEdgePathWithExpandedSource(
        this.currentNode,
        target,
        overlayWidth,
        overlayHeight
      );

      d3.select(`#edge-${edgeId}`).attr("d", path);
      d3.select(`#edge-hit-${edgeId}`).attr("d", path);
    });
  }

  /**
   * Calculate edge path when the source node is expanded
   */
  calculateEdgePathWithExpandedSource(
    source,
    target,
    expandedWidth,
    expandedHeight
  ) {
    const dx = target.x - source.x;
    const dy = target.y - source.y;
    const angle = Math.atan2(dy, dx);

    // Source uses expanded dimensions
    const sourcePoint = this.getExpandedNodeEdgePoint(
      source,
      angle,
      expandedWidth,
      expandedHeight
    );
    // Target uses normal dimensions
    const targetPoint = this.getNodeEdgePoint(target, angle + Math.PI);

    const midX = (sourcePoint.x + targetPoint.x) / 2;
    const midY = (sourcePoint.y + targetPoint.y) / 2;

    return `M${sourcePoint.x},${sourcePoint.y} Q${midX},${midY} ${targetPoint.x},${targetPoint.y}`;
  }

  /**
   * Calculate edge path when the target node is expanded
   */
  calculateEdgePathWithExpandedTarget(
    source,
    target,
    expandedWidth,
    expandedHeight
  ) {
    const dx = target.x - source.x;
    const dy = target.y - source.y;
    const angle = Math.atan2(dy, dx);

    // Source uses normal dimensions
    const sourcePoint = this.getNodeEdgePoint(source, angle);
    // Target uses expanded dimensions
    const targetPoint = this.getExpandedNodeEdgePoint(
      target,
      angle + Math.PI,
      expandedWidth,
      expandedHeight
    );

    const midX = (sourcePoint.x + targetPoint.x) / 2;
    const midY = (sourcePoint.y + targetPoint.y) / 2;

    return `M${sourcePoint.x},${sourcePoint.y} Q${midX},${midY} ${targetPoint.x},${targetPoint.y}`;
  }

  /**
   * Get edge point for an expanded (overlay) node - always rectangular
   */
  getExpandedNodeEdgePoint(node, angle, expandedWidth, expandedHeight) {
    const halfWidth = expandedWidth / 2;
    const halfHeight = expandedHeight / 2;

    const cos = Math.cos(angle);
    const sin = Math.sin(angle);

    // Find intersection with rectangle boundary
    let tx = Infinity,
      ty = Infinity;

    if (cos !== 0) {
      tx = (cos > 0 ? halfWidth : -halfWidth) / cos;
    }
    if (sin !== 0) {
      ty = (sin > 0 ? halfHeight : -halfHeight) / sin;
    }

    const t = Math.min(Math.abs(tx), Math.abs(ty));

    return {
      x: node.x + t * cos,
      y: node.y + t * sin,
    };
  }

  updateCurrentNodePanel() {
    const overlay = document.getElementById("node-overlay");
    const node = this.currentNode;

    // Update type badge
    const badge = document.getElementById("overlay-badge");
    badge.textContent = this.formatNodeType(node.type);
    badge.className = `node-badge ${node.type}`;

    // Update title
    document.getElementById("overlay-title").textContent = node.label;

    // Update overlay type class for styling
    overlay.className = `node-overlay ${node.type}`;

    // Update description
    const descEl = document.getElementById("overlay-description");
    const description = node.metadata?.description || "";
    if (description) {
      descEl.innerHTML = marked.parse(description.trim());
      descEl.style.display = "block";
    } else {
      descEl.style.display = "none";
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
    const container = document.getElementById("overlay-cache-entries");
    const headerSpan = document.querySelector(
      ".overlay-cache .section-header span"
    );
    if (headerSpan) headerSpan.textContent = "Data";

    const cache = this.nodeCache.get(this.currentNode.id) || {};
    container.innerHTML = CacheEditorHelpers.generateRows(
      cache,
      "Add key...",
      this.escapeHtml.bind(this)
    );

    // Use event delegation - attach once to container instead of per-element
    this.setupCacheEditorDelegation(container, "node");
  }

  renderOverlayActions() {
    const container = document.getElementById("overlay-actions");
    container.innerHTML = "";

    if (this.currentNode.type === "EndNode") {
      container.innerHTML =
        '<div class="flow-complete">Flow completed! 🎉</div>';
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

      const btn = document.createElement("button");
      btn.className = "edge-btn";

      const label = edge.label || "Continue";
      const shortcutHint =
        index < 9 ? `<span class="shortcut-hint">${index + 1}</span>` : "";
      btn.innerHTML = `${shortcutHint}<span class="arrow">→</span>${label}<span class="target">${this.truncateLabel(
        targetNode.label,
        20
      )}</span>`;

      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        this.navigateToNode(edge.target);
      });
      container.appendChild(btn);
    });
  }

  formatNodeType(type) {
    return type.replace("Node", "").toUpperCase();
  }

  escapeHtml(str) {
    if (typeof str !== "string") return str;
    const div = document.createElement("div");
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
    newContainer.addEventListener("input", (e) => {
      if (
        e.target.classList.contains("cache-key") ||
        e.target.classList.contains("cache-value")
      ) {
        const cache =
          cacheType === "node"
            ? this.nodeCache.get(this.currentNode.id) || {}
            : this.globalCache;
        const keyPrefix = cacheType === "node" ? "key_" : "global_";

        const needsRerender = CacheEditorHelpers.handleEdit(
          e,
          cache,
          keyPrefix
        );

        if (cacheType === "node") {
          this.nodeCache.set(this.currentNode.id, cache);
        }

        if (needsRerender) {
          const input = e.target;
          const renderFn =
            cacheType === "node" ? "renderOverlayData" : "renderGlobalCache";
          this[renderFn]();

          // Focus restoration after re-render
          const containerSelector =
            cacheType === "node"
              ? "#overlay-cache-entries"
              : "#global-cache-entries";
          const updatedContainer = document.querySelector(containerSelector);
          const newRows = updatedContainer.querySelectorAll(".cache-row");
          const targetRow = newRows[newRows.length - 2];
          if (targetRow) {
            const selector = input.classList.contains("cache-key")
              ? ".cache-key"
              : ".cache-value";
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
    newContainer.addEventListener("click", (e) => {
      if (e.target.classList.contains("delete-cache-btn")) {
        e.stopPropagation();
        const cache =
          cacheType === "node"
            ? this.nodeCache.get(this.currentNode.id) || {}
            : this.globalCache;

        if (CacheEditorHelpers.handleDelete(e, cache)) {
          if (cacheType === "node") {
            this.nodeCache.set(this.currentNode.id, cache);
            this.renderOverlayData();
          } else {
            this.renderGlobalCache();
          }
        }
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
    html += "</tbody></table>";
    return html;
  }

  makeDraggable(element) {
    const dragHandle = element.querySelector(".drag-handle") || element;

    dragHandle.addEventListener("mousedown", (e) => {
      // Use singleton drag manager state
      DragManager.startDrag(element, e.clientX, e.clientY);
      e.preventDefault();
    });
  }

  /**
   * Make an element draggable from anywhere on its surface
   * Used for panels that should be draggable except on interactive content
   */
  makeDraggableFromAnywhere(element) {
    element.addEventListener("mousedown", (e) => {
      // Don't start drag if clicking on interactive elements or selectable text
      if (e.target.closest("button, a, input, textarea, .incoming-source")) {
        return;
      }
      // Allow text selection in cache tables and other text content
      if (
        e.target.closest(".cache-table, .cache-key, .cache-value, .empty-cache")
      ) {
        return;
      }
      DragManager.startDrag(element, e.clientX, e.clientY);
      e.preventDefault();
    });
  }

  updateHistory() {
    const container = document.getElementById("history-list");
    if (!container) return;

    container.innerHTML = "";

    // Show all history items in a vertical list
    this.history.forEach((nodeId, index) => {
      const node = this.nodes[nodeId];
      if (!node) return;

      const item = document.createElement("div");
      item.className = "history-list-item";

      const isCurrent = index === this.historyIndex;
      const isFuture = index > this.historyIndex;

      if (isCurrent) item.classList.add("current");
      if (isFuture) item.classList.add("future");

      const number = document.createElement("span");
      number.className = "history-list-number";
      number.textContent = `${index + 1}.`;

      const label = document.createElement("span");
      label.className = "history-list-label";
      label.textContent = node.label;
      label.title = node.label;

      const badge = document.createElement("span");
      badge.className = `history-list-badge ${node.type}`;
      badge.textContent = this.formatNodeType(node.type).charAt(0);

      item.appendChild(number);
      item.appendChild(label);
      item.appendChild(badge);

      // Make clickable - time travel to that point
      item.addEventListener("click", () => {
        this.timeTravel(index);
      });

      container.appendChild(item);
    });

    // Scroll current item into view
    const currentItem = container.querySelector(".history-list-item.current");
    if (currentItem) {
      currentItem.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }

  zoomIn() {
    this.svg.transition().duration(300).call(this.zoom.scaleBy, 1.3);
  }

  zoomOut() {
    this.svg.transition().duration(300).call(this.zoom.scaleBy, 0.7);
  }

  zoomToCurrentNode() {
    if (this.currentNode) {
      this.userZoomLevel = null; // Reset to default zoom level
      this.zoomToNode(this.currentNode);
    }
  }

  // Navigation helper methods
  goBack() {
    if (this.historyIndex > 0) {
      this.timeTravel(this.historyIndex - 1);
    }
  }

  /**
   * Time travel to a specific point in history without truncating
   * @param {number} index - The history index to travel to
   */
  timeTravel(index) {
    if (index < 0 || index >= this.history.length) return;
    if (index === this.historyIndex) return;

    const nodeId = this.history[index];
    const node = this.nodes[nodeId];
    if (!node) return;

    // Update history index (don't modify history array)
    this.historyIndex = index;

    // Use shared navigation logic
    this.goToNode(node, false);
  }

  closeOverlay() {
    const overlay = document.getElementById("node-overlay");
    overlay.classList.add("hidden");
    // Restore the current node's collapsed shape
    if (this.currentNode) {
      d3.select(`#node-${this.currentNode.id} .node-collapsed`).style(
        "opacity",
        1
      );
      // Reset edge paths to use collapsed node dimensions
      this.resetEdgesToCollapsedNode();
    }
    this.fitToView();
  }

  /**
   * Reset edge paths to use the collapsed node dimensions
   */
  resetEdgesToCollapsedNode() {
    if (!this.currentNode) return;
    this.resetEdgesForNode(this.currentNode.id);
  }

  /**
   * Reset edge paths for a specific node to use collapsed dimensions
   */
  resetEdgesForNode(nodeId) {
    // Get all edges connected to the node
    const incomingEdgeIds = this.graph.incomingEdges[nodeId] || [];
    const outgoingEdgeIds = this.graph.outgoingEdges[nodeId] || [];

    // Reset all connected edges
    [...incomingEdgeIds, ...outgoingEdgeIds].forEach((edgeId) => {
      const edge = this.edges[edgeId];
      const source = this.nodes[edge.source];
      const target = this.nodes[edge.target];
      const path = this.calculateEdgePath(source, target);

      d3.select(`#edge-${edgeId}`).attr("d", path);
      d3.select(`#edge-hit-${edgeId}`).attr("d", path);
    });
  }

  selectEdgeByNumber(num) {
    const outgoingEdgeIds =
      this.graph.outgoingEdges[this.currentNode?.id] || [];
    if (num <= outgoingEdgeIds.length) {
      const edgeId = outgoingEdgeIds[num - 1];
      const edge = this.edges[edgeId];
      this.navigateToNode(edge.target);
    }
  }

  selectNextEdge() {
    const buttons = document.querySelectorAll("#overlay-actions .edge-btn");
    if (buttons.length === 0) return;

    this.selectedEdgeIndex = Math.min(
      this.selectedEdgeIndex + 1,
      buttons.length - 1
    );
    this.highlightEdgeButton(buttons);
  }

  selectPrevEdge() {
    const buttons = document.querySelectorAll("#overlay-actions .edge-btn");
    if (buttons.length === 0) return;

    if (this.selectedEdgeIndex < 0) this.selectedEdgeIndex = 0;
    this.selectedEdgeIndex = Math.max(this.selectedEdgeIndex - 1, 0);
    this.highlightEdgeButton(buttons);
  }

  highlightEdgeButton(buttons) {
    buttons.forEach((btn, i) => {
      btn.classList.toggle("keyboard-selected", i === this.selectedEdgeIndex);
    });
  }

  activateSelectedEdge() {
    const buttons = document.querySelectorAll("#overlay-actions .edge-btn");
    if (
      this.selectedEdgeIndex >= 0 &&
      this.selectedEdgeIndex < buttons.length
    ) {
      buttons[this.selectedEdgeIndex].click();
    }
  }

  fitToView() {
    const container = document.getElementById("flowchart-container");
    const width = container.clientWidth;
    const height = container.clientHeight;

    // Get bounds of all nodes
    let minX = Infinity,
      minY = Infinity,
      maxX = -Infinity,
      maxY = -Infinity;
    this.flowData.nodes.forEach((node) => {
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

    this.svg
      .transition()
      .duration(750)
      .call(this.zoom.transform, d3.zoomIdentity.translate(x, y).scale(scale));
  }
  // Global Cache Methods
  renderGlobalCache() {
    const container = document.getElementById("global-cache-entries");
    if (!container) return;

    // Use shared helper to generate rows (reuse same structure as node cache)
    container.innerHTML = CacheEditorHelpers.generateRows(
      this.globalCache,
      "Add global key...",
      this.escapeHtml.bind(this)
    );

    // Use event delegation - same as node cache
    this.setupCacheEditorDelegation(container, "global");

    // Update toggle button to show count
    this.updateGlobalCacheToggle();
  }

  updateGlobalCacheToggle() {
    const toggle = document.getElementById("global-cache-toggle");
    if (!toggle) return;

    const count = Object.keys(this.globalCache).length;
    const countBadge =
      count > 0 ? ` <span class="cache-count">(${count})</span>` : "";
    toggle.innerHTML = `Global Data${countBadge}`;
  }

  // =========================================
  // STATE PERSISTENCE (localStorage)
  // =========================================
  saveState() {
    if (!this.flowData) return;

    const state = {
      flowName: this.flowData.name,
      currentNodeId: this.currentNode?.id,
      history: this.history,
      historyIndex: this.historyIndex,
      visitedNodes: Array.from(this.visitedNodes),
      globalCache: this.globalCache,
      nodeCache: Object.fromEntries(this.nodeCache),
    };

    try {
      localStorage.setItem(
        `flowplay_${this.flowData.name}`,
        JSON.stringify(state)
      );
    } catch (e) {
      console.warn("Failed to save state to localStorage:", e);
    }
  }

  loadState() {
    if (!this.flowData) return false;

    try {
      const saved = localStorage.getItem(`flowplay_${this.flowData.name}`);
      if (!saved) return false;

      const state = JSON.parse(saved);
      if (state.flowName !== this.flowData.name) return false;

      this.history = state.history || [];
      this.historyIndex = state.historyIndex ?? -1;
      this.visitedNodes = new Set(state.visitedNodes || []);
      this.globalCache = state.globalCache || {};
      this.nodeCache = new Map(Object.entries(state.nodeCache || {}));

      // Restore visited visual state
      this.visitedNodes.forEach((nodeId) => {
        d3.select(`#node-${nodeId}`).classed("visited", true);
      });

      // Navigate to saved current node
      if (state.currentNodeId && this.nodes[state.currentNodeId]) {
        this.currentNode = null; // Prevent adding to history
        this.navigateToNodeDirect(state.currentNodeId);
        return true;
      }
    } catch (e) {
      console.warn("Failed to load state from localStorage:", e);
    }
    return false;
  }

  /**
   * Navigate without adding to history (for state restoration)
   */
  navigateToNodeDirect(nodeId) {
    const node = this.nodes[nodeId];
    if (!node) return;

    // Use shared navigation logic, but don't add to visited (state restoration)
    this.goToNode(node, false);
  }

  clearSavedState() {
    if (this.flowData) {
      localStorage.removeItem(`flowplay_${this.flowData.name}`);
    }
  }

  // =========================================
  // EXPORT STATE
  // =========================================
  exportState() {
    const state = {
      flowName: this.flowData?.name,
      exportDate: new Date().toISOString(),
      currentNode: this.currentNode?.id,
      history: this.history,
      visitedNodes: Array.from(this.visitedNodes),
      globalCache: this.globalCache,
      nodeCache: Object.fromEntries(this.nodeCache),
    };

    const json = JSON.stringify(state, null, 2);
    const blob = new Blob([json], { type: "application/json" });
    const url = URL.createObjectURL(blob);

    const a = document.createElement("a");
    a.href = url;
    a.download = `flowplay-state-${
      this.flowData?.name || "export"
    }-${Date.now()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  // =========================================
  // SETTINGS PANEL
  // =========================================
  loadSettings() {
    try {
      const saved = localStorage.getItem("flowplay_settings");
      if (saved) {
        this.settings = { ...this.settings, ...JSON.parse(saved) };
      }
    } catch (e) {
      console.warn("Failed to load settings:", e);
    }
  }

  saveSettings() {
    try {
      localStorage.setItem("flowplay_settings", JSON.stringify(this.settings));
    } catch (e) {
      console.warn("Failed to save settings:", e);
    }
  }

  setupSettingsPanel() {
    const settingsBtn = document.getElementById("settings-btn");
    const settingsOverlay = document.getElementById("settings-overlay");
    const settingsPanel = document.getElementById("settings-panel");
    const settingsClose = document.getElementById("settings-close");
    if (!settingsBtn || !settingsOverlay || !settingsPanel) return;

    // Open modal
    settingsBtn.addEventListener("click", () => {
      settingsOverlay.classList.remove("hidden");
    });

    // Close modal
    const closeModal = () => {
      settingsOverlay.classList.add("hidden");
    };

    if (settingsClose) {
      settingsClose.addEventListener("click", closeModal);
    }

    // Close when clicking overlay background
    settingsOverlay.addEventListener("click", (e) => {
      if (e.target === settingsOverlay) {
        closeModal();
      }
    });

    // Close on Escape key
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && !settingsOverlay.classList.contains("hidden")) {
        closeModal();
      }
    });

    // Setup toggle handlers
    const toggles = settingsPanel.querySelectorAll(".setting-toggle");
    toggles.forEach((toggle) => {
      const settingKey = toggle.dataset.setting;
      if (settingKey && this.settings.hasOwnProperty(settingKey)) {
        toggle.checked = this.settings[settingKey];
        toggle.addEventListener("change", () => {
          this.settings[settingKey] = toggle.checked;
          this.saveSettings();
          this.applySettings();
        });
      }
    });

    // Setup default zoom input
    const zoomInput = document.getElementById("default-zoom-input");
    if (zoomInput) {
      zoomInput.value = this.settings.defaultZoomLevel;
      zoomInput.addEventListener("change", () => {
        const value = parseFloat(zoomInput.value);
        if (!isNaN(value) && value >= 0.5 && value <= 3) {
          this.settings.defaultZoomLevel = value;
          this.saveSettings();
        }
      });
    }
  }

  applySettings() {
    // Mini-map
    const miniMap = document.getElementById("mini-map");
    if (miniMap) {
      miniMap.style.display = this.settings.showMiniMap ? "block" : "none";
    }

    // Progress indicator
    const progressIndicator = document.getElementById("progress-indicator");
    if (progressIndicator) {
      progressIndicator.style.display = this.settings.showProgressIndicator
        ? "flex"
        : "none";
    }

    // Dark mode
    document.body.classList.toggle("light-mode", !this.settings.darkMode);

    // Animated edges
    document.body.classList.toggle(
      "no-edge-animation",
      !this.settings.animatedEdges
    );

    // Auto-hide controls
    const controls = document.getElementById("controls");
    if (controls) {
      if (this.settings.autoHideControls) {
        // Re-enable auto-hide
        this.setupAutoHide();
      } else {
        controls.classList.remove("auto-hidden");
        clearTimeout(this.autoHideTimeout);
      }
    }
  }

  setSetting(key, value) {
    if (this.settings.hasOwnProperty(key)) {
      this.settings[key] = value;
      this.saveSettings();
      this.applySettings();
    }
  }
}

// Initialize on load
document.addEventListener("DOMContentLoaded", () => {
  const app = new FlowPlay();
  app.init();
});
