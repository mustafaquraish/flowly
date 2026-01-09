/**
 * FlowPlay - Interactive Flowchart Visualizer
 * Main Application Logic
 */

// =========================================
// UTILITY FUNCTIONS
// =========================================

/**
 * Escape HTML special characters
 */
function escapeHtml(str) {
  if (typeof str !== "string") return str;
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/**
 * Format node type for display (e.g., "ProcessNode" -> "PROCESS")
 */
function formatNodeType(type) {
  return type.replace("Node", "").toUpperCase();
}

/**
 * Truncate a label to a maximum length
 */
function truncateLabel(label, maxLength) {
  if (label.length <= maxLength) return label;
  return label.substring(0, maxLength - 2) + "...";
}

// =========================================
// DRAG MANAGER (Singleton)
// =========================================

const DragManager = {
  activeElement: null,
  startX: 0,
  startY: 0,
  initialLeft: 0,
  initialTop: 0,

  init() {
    document.addEventListener("mousemove", (e) => {
      if (!this.activeElement) return;
      this.activeElement.style.left = `${
        this.initialLeft + e.clientX - this.startX
      }px`;
      this.activeElement.style.top = `${
        this.initialTop + e.clientY - this.startY
      }px`;
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

DragManager.init();

// =========================================
// SETTINGS MANAGER
// =========================================

const SettingsManager = {
  defaults: {
    showMiniMap: true,
    showProgressIndicator: true,
    showNodePreview: true,
    darkMode: true,
    animatedEdges: true,
    autoHideControls: true,
    autoSaveState: true,
    alwaysExpandNodes: false,
    defaultZoomLevel: 2.0,
  },

  current: null,

  load() {
    try {
      const saved = localStorage.getItem("flowplay_settings");
      this.current = { ...this.defaults, ...(saved ? JSON.parse(saved) : {}) };
    } catch (e) {
      console.warn("Failed to load settings:", e);
      this.current = { ...this.defaults };
    }
    return this.current;
  },

  save() {
    try {
      localStorage.setItem("flowplay_settings", JSON.stringify(this.current));
    } catch (e) {
      console.warn("Failed to save settings:", e);
    }
  },

  set(key, value) {
    if (this.current.hasOwnProperty(key)) {
      this.current[key] = value;
      this.save();
    }
  },

  get(key) {
    return this.current?.[key] ?? this.defaults[key];
  },
};

// =========================================
// COMMAND PALETTE
// =========================================

const CommandPalette = {
  element: null,
  inputElement: null,
  resultsElement: null,
  isOpen: false,
  mode: "commands", // 'commands' or 'nodes'
  keyboardIndex: 0, // Keyboard focus index (separate from hover)
  hoverIndex: -1, // Hover focus index (-1 means no hover)
  isCommandKeyHeld: false, // Track if command/ctrl key is held
  results: [],
  app: null, // Reference to FlowPlay instance

  // Command definitions with shortcuts
  commands: [
    // Settings toggles
    {
      id: "toggle-minimap",
      label: "Toggle Mini-map",
      category: "Display",
      settingKey: "showMiniMap",
    },
    {
      id: "toggle-progress",
      label: "Toggle Progress Indicator",
      category: "Display",
      settingKey: "showProgressIndicator",
    },
    {
      id: "toggle-preview",
      label: "Toggle Node Preview on Hover",
      category: "Display",
      settingKey: "showNodePreview",
    },
    {
      id: "toggle-dark-mode",
      label: "Toggle Dark Mode",
      category: "Appearance",
      settingKey: "darkMode",
    },
    {
      id: "toggle-animated-edges",
      label: "Toggle Animated Edges",
      category: "Appearance",
      settingKey: "animatedEdges",
    },
    {
      id: "toggle-auto-hide",
      label: "Toggle Auto-hide Controls",
      category: "Behavior",
      settingKey: "autoHideControls",
    },
    {
      id: "toggle-auto-save",
      label: "Toggle Auto-save Progress",
      category: "Behavior",
      settingKey: "autoSaveState",
    },
    {
      id: "toggle-expand-nodes",
      label: "Toggle Always Expand Nodes",
      category: "Display",
      settingKey: "alwaysExpandNodes",
    },
    // Actions with shortcuts
    {
      id: "restart",
      label: "Restart Flow",
      category: "Navigation",
      action: "restart",
      shortcut: "R",
    },
    {
      id: "zoom-in",
      label: "Zoom In",
      category: "View",
      action: "zoomIn",
      shortcut: "+",
    },
    {
      id: "zoom-out",
      label: "Zoom Out",
      category: "View",
      action: "zoomOut",
      shortcut: "-",
    },
    {
      id: "fit-view",
      label: "Fit All Nodes in View",
      category: "View",
      action: "fitView",
      shortcut: "F",
    },
    {
      id: "zoom-to-node",
      label: "Zoom to Current Node",
      category: "View",
      action: "zoomToCurrentNode",
      shortcut: "Z",
    },
    {
      id: "go-back",
      label: "Go Back in History",
      category: "Navigation",
      action: "goBack",
      shortcut: "B",
    },
    {
      id: "toggle-history",
      label: "Toggle History Panel",
      category: "Panels",
      action: "toggleHistoryPanel",
      shortcut: "H",
    },
    {
      id: "export-state",
      label: "Export Session State",
      category: "Data",
      action: "exportState",
    },
    {
      id: "open-file",
      label: "Open Flow File...",
      category: "Data",
      action: "openFile",
      shortcut: "⌘O",
    },
    {
      id: "search-nodes",
      label: "Search Nodes...",
      category: "Navigation",
      action: "openNodeSearch",
      shortcut: "⌘P",
    },
  ],

  init(app) {
    this.app = app;
    this.createDOM();
    this.setupKeyboardShortcuts();
    this.setupCommandKeyTracking();
  },

  setupCommandKeyTracking() {
    // Track when command/ctrl key is held for quick number selection
    // Use a CSS class on the modal to show/hide numbers without re-rendering
    document.addEventListener("keydown", (e) => {
      if ((e.metaKey || e.ctrlKey) && this.isOpen) {
        // Only show numbers if the key is pressed AFTER the palette is open
        // (not during the Cmd+P that opened it)
        if (!this.isCommandKeyHeld && this.hasReleasedCommandKey) {
          this.isCommandKeyHeld = true;
          this.element.classList.add("show-quick-numbers");
        }
        // Handle command+number quick selection
        const num = parseInt(e.key);
        if (num >= 1 && num <= 9 && this.hasReleasedCommandKey) {
          e.preventDefault();
          const index = num - 1;
          if (index < this.results.length) {
            this.keyboardIndex = index;
            this.executeSelected();
          }
        }
      }
    });

    document.addEventListener("keyup", (e) => {
      // Track when command key is released after opening
      if (!e.metaKey && !e.ctrlKey) {
        if (this.isOpen && !this.hasReleasedCommandKey) {
          // First release after opening - now allow quick numbers
          this.hasReleasedCommandKey = true;
        }
        if (this.isCommandKeyHeld) {
          this.isCommandKeyHeld = false;
          this.element.classList.remove("show-quick-numbers");
        }
      }
    });
  },

  createDOM() {
    // Create palette container
    this.element = document.createElement("div");
    this.element.id = "command-palette";
    this.element.className = "command-palette hidden";
    this.element.innerHTML = `
      <div class="command-palette-backdrop"></div>
      <div class="command-palette-modal">
        <div class="command-palette-input-wrapper">
          <span class="command-palette-icon">⌘</span>
          <input type="text" class="command-palette-input" placeholder="Type a command..." autocomplete="off" />
        </div>
        <div class="command-palette-results"></div>
      </div>
    `;
    document.body.appendChild(this.element);

    this.inputElement = this.element.querySelector(".command-palette-input");
    this.resultsElement = this.element.querySelector(
      ".command-palette-results"
    );

    // Event listeners
    this.element
      .querySelector(".command-palette-backdrop")
      .addEventListener("click", () => this.close());

    this.inputElement.addEventListener("input", () => this.onInput());
    this.inputElement.addEventListener("keydown", (e) => this.onKeyDown(e));
  },

  setupKeyboardShortcuts() {
    document.addEventListener("keydown", (e) => {
      // Cmd+Shift+P or Ctrl+Shift+P for command palette
      if (
        (e.metaKey || e.ctrlKey) &&
        e.shiftKey &&
        e.key.toLowerCase() === "p"
      ) {
        e.preventDefault();
        this.open("commands");
      }
      // Cmd+P or Ctrl+P for node search (also keep Cmd+K)
      else if (
        (e.metaKey || e.ctrlKey) &&
        !e.shiftKey &&
        e.key.toLowerCase() === "p"
      ) {
        e.preventDefault();
        this.open("nodes");
      }
      // Cmd+O or Ctrl+O for opening file
      else if (
        (e.metaKey || e.ctrlKey) &&
        !e.shiftKey &&
        e.key.toLowerCase() === "o"
      ) {
        e.preventDefault();
        if (this.app) {
          this.app.openFile();
        }
      }
      // Escape to close
      else if (e.key === "Escape" && this.isOpen) {
        e.preventDefault();
        this.close();
      }
    });
  },

  open(mode = "commands") {
    this.mode = mode;
    this.isOpen = true;
    this.keyboardIndex = 0;
    this.hoverIndex = -1;
    this.isCommandKeyHeld = false;
    this.hasReleasedCommandKey = false; // Don't allow quick numbers until Cmd is released once
    this.element.classList.remove("hidden");
    this.element.classList.remove("show-quick-numbers");
    this.inputElement.value = "";
    this.inputElement.placeholder =
      mode === "commands"
        ? "Type a command..."
        : "Search nodes by name or ID...";
    this.element.querySelector(".command-palette-icon").textContent =
      mode === "commands" ? "⌘" : "🔍";
    this.inputElement.focus();
    this.updateResults();
  },

  close() {
    this.isOpen = false;
    this.isCommandKeyHeld = false;
    this.hasReleasedCommandKey = false;
    this.element.classList.add("hidden");
    this.element.classList.remove("show-quick-numbers");
    this.inputElement.value = "";
    this.results = [];
  },

  onInput() {
    this.keyboardIndex = 0;
    this.hoverIndex = -1;
    this.updateResults();
  },

  onKeyDown(e) {
    switch (e.key) {
      case "ArrowDown":
        e.preventDefault();
        this.keyboardIndex = Math.min(
          this.keyboardIndex + 1,
          this.results.length - 1
        );
        this.hoverIndex = -1; // Clear hover on keyboard nav
        this.updateSelectionClasses();
        this.scrollSelectedIntoView();
        break;
      case "ArrowUp":
        e.preventDefault();
        this.keyboardIndex = Math.max(this.keyboardIndex - 1, 0);
        this.hoverIndex = -1; // Clear hover on keyboard nav
        this.updateSelectionClasses();
        this.scrollSelectedIntoView();
        break;
      case "Enter":
        e.preventDefault();
        this.executeSelected();
        break;
      case "Escape":
        e.preventDefault();
        this.close();
        break;
    }
  },

  scrollSelectedIntoView() {
    const selected = this.resultsElement.querySelector(
      ".command-item.selected"
    );
    if (selected) {
      selected.scrollIntoView({ block: "nearest" });
    }
  },

  updateResults() {
    const query = this.inputElement.value.toLowerCase().trim();

    if (this.mode === "commands") {
      this.results = this.filterCommands(query);
    } else {
      this.results = this.filterNodes(query);
    }

    this.renderResults();
  },

  filterCommands(query) {
    if (!query) {
      return this.commands.map((cmd) => ({ ...cmd, type: "command" }));
    }

    // Fuzzy match
    return this.commands
      .map((cmd) => {
        const searchText = `${cmd.label} ${cmd.category}`.toLowerCase();
        const score = this.fuzzyScore(query, searchText);
        return { ...cmd, type: "command", score };
      })
      .filter((cmd) => cmd.score > 0)
      .sort((a, b) => b.score - a.score);
  },

  filterNodes(query) {
    const nodes = Object.values(FlowState.nodes);

    if (!query) {
      // Show recent/current nodes first, then all nodes
      const currentId = FlowState.currentNode?.id;
      const historyIds = new Set(FlowState.history.slice(-5));

      return nodes
        .map((node) => ({
          ...node,
          type: "node",
          nodeType: node.type, // Preserve original node type for coloring
          score: node.id === currentId ? 100 : historyIds.has(node.id) ? 50 : 0,
        }))
        .sort((a, b) => b.score - a.score)
        .slice(0, 20);
    }

    return nodes
      .map((node) => {
        const searchText = `${node.label} ${node.id} ${
          node.metadata?.description || ""
        }`.toLowerCase();
        const score = this.fuzzyScore(query, searchText);
        return { ...node, type: "node", nodeType: node.type, score };
      })
      .filter((node) => node.score > 0)
      .sort((a, b) => b.score - a.score)
      .slice(0, 20);
  },

  fuzzyScore(query, text) {
    // Simple fuzzy matching - consecutive character matching with bonuses
    let score = 0;
    let queryIdx = 0;
    let consecutive = 0;

    for (let i = 0; i < text.length && queryIdx < query.length; i++) {
      if (text[i] === query[queryIdx]) {
        score += 1 + consecutive;
        consecutive++;
        queryIdx++;
      } else {
        consecutive = 0;
      }
    }

    // Must match all query characters
    if (queryIdx < query.length) return 0;

    // Bonus for matching at word boundaries
    if (text.startsWith(query)) score += 10;
    if (text.includes(" " + query)) score += 5;

    return score;
  },

  /**
   * Extract first sentence from a markdown description
   */
  getFirstSentence(markdown) {
    if (!markdown) return "";
    // Strip markdown formatting and get first sentence
    const plain = markdown
      .replace(/[#*_`~\[\]]/g, "")
      .replace(/\n+/g, " ")
      .trim();
    // Find first sentence-ending punctuation
    const match = plain.match(/^[^.!?]*[.!?]/);
    if (match) {
      const sentence = match[0].trim();
      return sentence.length > 80
        ? sentence.substring(0, 77) + "..."
        : sentence;
    }
    // No sentence end found, truncate
    return plain.length > 80 ? plain.substring(0, 77) + "..." : plain;
  },

  /**
   * Get the effective selected index (keyboard takes precedence over hover)
   */
  getEffectiveIndex() {
    return this.hoverIndex >= 0 ? this.hoverIndex : this.keyboardIndex;
  },

  renderResults() {
    if (this.results.length === 0) {
      this.resultsElement.innerHTML = `
        <div class="command-empty">
          ${this.mode === "commands" ? "No commands found" : "No nodes found"}
        </div>
      `;
      return;
    }

    this.resultsElement.innerHTML = this.results
      .map((item, idx) => {
        const isKeyboardSelected = idx === this.keyboardIndex;
        const isHoverSelected = idx === this.hoverIndex;
        const selectedClass = isKeyboardSelected
          ? "selected"
          : isHoverSelected
          ? "hover"
          : "";
        // Always include quick number span for items 1-9 (hidden by CSS, shown when Cmd held)
        const quickNumber =
          idx < 9 ? `<span class="quick-number">${idx + 1}</span>` : "";

        if (item.type === "command") {
          const icon = item.settingKey
            ? this.app.settings[item.settingKey]
              ? "✓"
              : "○"
            : "›";
          // Show shortcut if available
          const shortcutHtml = item.shortcut
            ? `<span class="command-shortcut">${escapeHtml(
                item.shortcut
              )}</span>`
            : "";
          return `
            <div class="command-item ${selectedClass}" data-index="${idx}">
              ${quickNumber}
              <span class="command-icon">${icon}</span>
              <span class="command-label">${escapeHtml(item.label)}</span>
              <span class="command-category">${escapeHtml(item.category)}</span>
              ${shortcutHtml}
            </div>
          `;
        } else {
          // Node item - get color based on node type
          const nodeType = item.nodeType || item.type;
          const nodeTypeClass =
            nodeType === "StartNode"
              ? "start"
              : nodeType === "EndNode"
              ? "end"
              : nodeType === "DecisionNode"
              ? "decision"
              : "process";
          const isCurrent = item.id === FlowState.currentNode?.id;
          // Show first sentence of description instead of raw ID
          const description = this.getFirstSentence(item.metadata?.description);
          const secondaryText = description || item.id;
          return `
            <div class="command-item node-item ${selectedClass}" data-index="${idx}">
              ${quickNumber}
              <span class="node-type-dot ${nodeTypeClass}"></span>
              <span class="command-label">${escapeHtml(item.label)}${
            isCurrent ? " <em>(current)</em>" : ""
          }</span>
              <span class="command-category">${escapeHtml(secondaryText)}</span>
            </div>
          `;
        }
      })
      .join("");

    // Attach event listeners
    this.attachResultListeners();
  },

  /**
   * Attach click/hover listeners to result items
   * Separated to allow updating visual state without full re-render
   */
  attachResultListeners() {
    this.resultsElement.querySelectorAll(".command-item").forEach((el) => {
      const idx = parseInt(el.dataset.index, 10);

      // Click to execute
      el.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        this.keyboardIndex = idx;
        this.executeSelected();
      });

      // Mouseenter/leave only update visual state, don't re-render
      el.addEventListener("mouseenter", () => {
        // Just update visual classes, don't call renderResults
        this.resultsElement
          .querySelectorAll(".command-item")
          .forEach((item, i) => {
            item.classList.toggle("hover", i === idx);
          });
        this.hoverIndex = idx;
      });

      el.addEventListener("mouseleave", () => {
        el.classList.remove("hover");
        this.hoverIndex = -1;
      });
    });
  },

  /**
   * Update just the selection classes without full re-render
   */
  updateSelectionClasses() {
    this.resultsElement.querySelectorAll(".command-item").forEach((el, idx) => {
      el.classList.toggle("selected", idx === this.keyboardIndex);
      el.classList.toggle("hover", idx === this.hoverIndex);
    });
  },

  executeSelected() {
    // Use keyboard index for execution (not hover)
    const item = this.results[this.keyboardIndex];
    if (!item) return;

    this.close();

    if (item.type === "command") {
      if (item.settingKey) {
        // Toggle setting
        const newValue = !this.app.settings[item.settingKey];
        this.app.settings[item.settingKey] = newValue;
        SettingsManager.save(this.app.settings);
        this.app.applySettings();
      } else if (item.action) {
        // Execute action
        switch (item.action) {
          case "restart":
            this.app.restart();
            break;
          case "zoomIn":
            this.app.zoomIn();
            break;
          case "zoomOut":
            this.app.zoomOut();
            break;
          case "fitView":
            this.app.fitToView();
            break;
          case "zoomToCurrentNode":
            if (this.app.currentNode) this.app.zoomToNode(this.app.currentNode);
            break;
          case "goBack":
            this.app.goBack();
            break;
          case "toggleHistoryPanel":
            this.app.toggleHistoryPanel();
            break;
          case "exportState":
            this.app.exportState();
            break;
          case "openFile":
            this.app.openFile();
            break;
          case "openNodeSearch":
            setTimeout(() => this.open("nodes"), 50);
            break;
        }
      }
    } else {
      // Navigate to node
      this.app.navigateToNode(item.id);
    }
  },
};

// =========================================
// FLOW STATE MANAGER
// =========================================

const FlowState = {
  // Flow data (loaded from JSON)
  flowData: null,
  nodes: {},
  edges: {},
  graph: null,

  // Navigation state
  currentNode: null,
  history: [],
  historyIndex: -1,
  visitedNodes: new Set(),

  // Caches
  nodeCache: new Map(),
  globalCache: {},

  // User zoom preference
  userZoomLevel: null,

  /**
   * Initialize state from flow data
   */
  init(flowData) {
    this.flowData = flowData;
    this.nodes = {};
    this.edges = {};

    flowData.nodes.forEach((node) => {
      this.nodes[node.id] = node;
    });
    flowData.edges.forEach((edge) => {
      this.edges[edge.id] = edge;
    });
    this.graph = flowData.graph;
  },

  /**
   * Reset all navigation state
   */
  reset() {
    this.currentNode = null;
    this.history = [];
    this.historyIndex = -1;
    this.visitedNodes.clear();
    this.nodeCache.clear();
    this.userZoomLevel = null;
  },

  /**
   * Navigate to a node, updating history
   */
  navigateTo(nodeId) {
    const node = this.nodes[nodeId];
    if (!node) return null;

    // Update history
    if (
      this.historyIndex < this.history.length - 1 &&
      this.history[this.historyIndex + 1] === nodeId
    ) {
      this.historyIndex++;
    } else {
      this.history = this.history.slice(0, this.historyIndex + 1);
      this.history.push(nodeId);
      this.historyIndex = this.history.length - 1;
    }

    // Mark previous node as visited
    if (this.currentNode) {
      this.visitedNodes.add(this.currentNode.id);
    }

    this.currentNode = node;
    return node;
  },

  /**
   * Time travel to a specific history index
   */
  timeTravel(index) {
    if (
      index < 0 ||
      index >= this.history.length ||
      index === this.historyIndex
    ) {
      return null;
    }
    this.historyIndex = index;
    this.currentNode = this.nodes[this.history[index]];
    return this.currentNode;
  },

  /**
   * Go back in history
   */
  goBack() {
    return this.historyIndex > 0
      ? this.timeTravel(this.historyIndex - 1)
      : null;
  },

  /**
   * Get start node
   */
  getStartNode() {
    return this.flowData?.nodes.find((n) => n.type === "StartNode") || null;
  },

  /**
   * Save state to localStorage
   */
  saveToStorage() {
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
      console.warn("Failed to save state:", e);
    }
  },

  /**
   * Load state from localStorage
   */
  loadFromStorage() {
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

      if (state.currentNodeId && this.nodes[state.currentNodeId]) {
        this.currentNode = this.nodes[state.currentNodeId];
        return true;
      }
    } catch (e) {
      console.warn("Failed to load state:", e);
    }
    return false;
  },

  /**
   * Clear saved state
   */
  clearStorage() {
    if (this.flowData) {
      localStorage.removeItem(`flowplay_${this.flowData.name}`);
    }
  },

  /**
   * Get/set node cache
   */
  getNodeCache(nodeId) {
    return this.nodeCache.get(nodeId) || {};
  },

  setNodeCache(nodeId, cache) {
    this.nodeCache.set(nodeId, cache);
  },
};

// =========================================
// CACHE EDITOR HELPERS
// =========================================

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
    // Configuration
    this.nodeWidth = 160;
    this.nodeHeight = 70;

    // D3 elements
    this.svg = null;
    this.g = null;
    this.zoom = null;

    // UI state
    this.selectedHistoryIndex = -1;
    this.selectedEdgeIndex = 0;
    this.nodePreviewTooltip = null;
    this.autoHideTimeout = null;
    this.zoomTrackTimeout = null;
    this.lastInteractionTime = Date.now();

    // Load settings
    this.settings = SettingsManager.load();

    // Bind methods
    this.handleZoom = this.handleZoom.bind(this);
  }

  // Convenience accessors for FlowState
  get flowData() {
    return FlowState.flowData;
  }
  get nodes() {
    return FlowState.nodes;
  }
  get edges() {
    return FlowState.edges;
  }
  get graph() {
    return FlowState.graph;
  }
  get currentNode() {
    return FlowState.currentNode;
  }
  get history() {
    return FlowState.history;
  }
  get historyIndex() {
    return FlowState.historyIndex;
  }
  get visitedNodes() {
    return FlowState.visitedNodes;
  }
  get nodeCache() {
    return FlowState.nodeCache;
  }
  get globalCache() {
    return FlowState.globalCache;
  }
  get userZoomLevel() {
    return FlowState.userZoomLevel;
  }
  set userZoomLevel(value) {
    FlowState.userZoomLevel = value;
  }

  async init() {
    try {
      this.showLoading(true);
      await this.loadFlowData();
      this.setupSVG();
      this.renderFlowchart();
      this.setupControls();
      this.setupSearch();
      this.setupMiniMap();
      this.setupNodePreview();
      this.setupAutoHide();
      this.setupSettingsPanel();
      CommandPalette.init(this);
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
    let flowData = null;
    let errorMessage = "Failed to load flowchart";

    // First, check for bundled data (standalone HTML export)
    if (typeof bundledFlowJSON !== "undefined" && bundledFlowJSON !== null) {
      flowData = bundledFlowJSON;
      console.log("Using bundled flow JSON data");
    }

    // Fall back to fetching from file (development mode)
    if (!flowData) {
      try {
        const response = await fetch("./complex_flow.json");
        if (response.ok) {
          flowData = await response.json();
          console.log("Loaded flow data from complex_flow.json");
        }
      } catch (e) {
        // Fall through to error
      }
    }

    if (!flowData) {
      throw new Error(errorMessage);
    }

    // Initialize state with flow data
    FlowState.init(flowData);

    // Set title
    document.getElementById("flowchart-name").textContent = flowData.name;
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
    // Reposition expanded overlays if enabled
    this.positionExpandedOverlays();
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
          // Double-click to reset zoom to default level and re-center
          if (this.currentNode && node.id === this.currentNode.id) {
            // Reset user zoom level to default on double-click of current node
            this.userZoomLevel = null;
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

  // =========================================
  // EXPANDED OVERLAYS (Always Expand Mode)
  // =========================================

  /**
   * Create or update expanded overlays for all nodes
   * Called when alwaysExpandNodes setting changes
   */
  setupExpandedOverlays() {
    const container = document.getElementById("flowchart-container");

    // Remove existing expanded overlays
    container
      .querySelectorAll(".expanded-node-overlay")
      .forEach((el) => el.remove());

    if (!this.settings.alwaysExpandNodes) {
      // Restore collapsed node visibility (except current node which shows main overlay)
      Object.values(this.nodes).forEach((node) => {
        const isCurrentNode =
          this.currentNode && node.id === this.currentNode.id;
        d3.select(`#node-${node.id} .node-collapsed`).style(
          "opacity",
          isCurrentNode ? 0 : 1
        );
      });
      // Reset all edges to collapsed node dimensions, then update for current node
      this.resetAllEdgesToCollapsed();
      // If there's a current node, update its edges for the main overlay
      if (this.currentNode) {
        const overlay = document.getElementById("node-overlay");
        if (overlay && !overlay.classList.contains("hidden")) {
          this.updateEdgesForExpandedNode(overlay);
        }
      }
      return;
    }

    // Hide all collapsed nodes
    this.g.selectAll(".node-collapsed").style("opacity", 0);

    // Create an overlay for each node - using EXACT same structure as main overlay
    Object.values(this.nodes).forEach((node) => {
      const overlay = document.createElement("div");
      // Use node-overlay class for identical styling, plus expanded-node-overlay for positioning
      overlay.className = `node-overlay expanded-node-overlay ${node.type}`;
      overlay.id = `expanded-overlay-${node.id}`;
      overlay.dataset.nodeId = node.id;

      // Exact same HTML structure as main overlay in index.html
      // Plus a click-blocker overlay for non-current nodes
      overlay.innerHTML = `
        <div class="overlay-click-blocker"></div>
        <div class="overlay-header">
          <span class="node-badge ${node.type}">${formatNodeType(
        node.type
      )}</span>
          <h3>${escapeHtml(node.label)}</h3>
        </div>
        <div class="overlay-description"></div>
        <div class="overlay-cache">
          <div class="section-header">
            <span>Data</span>
          </div>
          <div class="cache-entries"></div>
        </div>
        <div class="overlay-actions"></div>
      `;

      // Click blocker - covers the whole overlay for non-current nodes
      const clickBlocker = overlay.querySelector(".overlay-click-blocker");
      clickBlocker.addEventListener("click", (e) => {
        e.stopPropagation();
        this.navigateToNode(node.id);
      });

      // Populate using same logic as main overlay
      const descEl = overlay.querySelector(".overlay-description");
      const description = node.metadata?.description || "";
      if (description) {
        descEl.innerHTML = marked.parse(description.trim());
        // Make all links open in new tab
        descEl.querySelectorAll("a").forEach((a) => {
          a.setAttribute("target", "_blank");
          a.setAttribute("rel", "noopener noreferrer");
        });
        descEl.style.display = "block";
      } else {
        descEl.style.display = "none";
      }

      // Render cache - same as renderOverlayData
      const cacheContainer = overlay.querySelector(".cache-entries");
      const cache = this.nodeCache.get(node.id) || {};
      cacheContainer.innerHTML = CacheEditorHelpers.generateRows(
        cache,
        "Add key...",
        escapeHtml
      );
      this.setupCacheEditorDelegation(cacheContainer, "expanded-" + node.id);

      // Render actions - same as renderOverlayActions
      const actionsContainer = overlay.querySelector(".overlay-actions");
      if (node.type === "EndNode") {
        actionsContainer.innerHTML =
          '<div class="flow-complete">Flow completed! 🎉</div>';
      } else {
        const outgoingEdgeIds = this.graph.outgoingEdges[node.id] || [];
        if (outgoingEdgeIds.length === 0) {
          actionsContainer.innerHTML =
            '<div class="flow-complete">Dead end</div>';
        } else {
          outgoingEdgeIds.forEach((edgeId, index) => {
            const edge = this.edges[edgeId];
            const targetNode = this.nodes[edge.target];
            const btn = document.createElement("button");
            btn.className = "edge-btn";
            const label = edge.label || "Continue";
            const shortcutHint =
              index < 9
                ? `<span class="shortcut-hint">${index + 1}</span>`
                : "";
            btn.innerHTML = `${shortcutHint}<span class="arrow">→</span>${label}<span class="target">${truncateLabel(
              targetNode.label,
              20
            )}</span>`;
            btn.addEventListener("click", (e) => {
              e.stopPropagation();
              this.navigateToNode(edge.target);
            });
            actionsContainer.appendChild(btn);
          });
        }
      }

      container.appendChild(overlay);
    });

    // Position all overlays and update edges
    this.positionExpandedOverlays();
    this.updateAllEdgesForExpandedOverlays();
  }

  /**
   * Position all expanded overlays based on current zoom/pan
   */
  positionExpandedOverlays() {
    if (!this.settings.alwaysExpandNodes) return;

    const transform = d3.zoomTransform(this.svg.node());
    const currentScale = transform.k / 1.6;

    Object.values(this.nodes).forEach((node) => {
      const overlay = document.getElementById(`expanded-overlay-${node.id}`);
      if (!overlay) return;

      const screenX = node.x * transform.k + transform.x;
      const screenY = node.y * transform.k + transform.y;

      overlay.style.left = `${screenX}px`;
      overlay.style.top = `${screenY}px`;
      overlay.style.transform = `translate(-50%, -50%) scale(${currentScale})`;
      overlay.style.transformOrigin = "center center";

      // Mark current node's overlay
      overlay.classList.toggle("current", this.currentNode?.id === node.id);
      overlay.classList.toggle("visited", this.visitedNodes.has(node.id));
    });
  }

  /**
   * Update all edge paths to connect to expanded overlays instead of collapsed nodes
   */
  updateAllEdgesForExpandedOverlays() {
    if (!this.settings.alwaysExpandNodes) return;

    // Build a map of expanded dimensions for each node
    const expandedDimsMap = new Map();
    Object.values(this.nodes).forEach((node) => {
      const overlay = document.getElementById(`expanded-overlay-${node.id}`);
      if (overlay) {
        expandedDimsMap.set(node.id, {
          width: overlay.offsetWidth / 1.6,
          height: overlay.offsetHeight / 1.6,
        });
      }
    });

    // Update all edges using expanded dimensions
    Object.values(this.edges).forEach((edge) => {
      const source = this.nodes[edge.source];
      const target = this.nodes[edge.target];
      const sourceDims = expandedDimsMap.get(edge.source) || null;
      const targetDims = expandedDimsMap.get(edge.target) || null;

      const path = this.calculateEdgePath(
        source,
        target,
        sourceDims,
        targetDims
      );
      d3.select(`#edge-${edge.id}`).attr("d", path);
      d3.select(`#edge-hit-${edge.id}`).attr("d", path);
    });
  }

  /**
   * Reset all edge paths to use collapsed node dimensions
   */
  resetAllEdgesToCollapsed() {
    Object.values(this.edges).forEach((edge) => {
      const source = this.nodes[edge.source];
      const target = this.nodes[edge.target];
      // Pass null for dimensions to use default collapsed size
      const path = this.calculateEdgePath(source, target, null, null);
      d3.select(`#edge-${edge.id}`).attr("d", path);
      d3.select(`#edge-hit-${edge.id}`).attr("d", path);
    });
  }

  /**
   * Calculate edge path between two nodes.
   * @param {Object} source - Source node
   * @param {Object} target - Target node
   * @param {Object} [sourceDims] - Override dimensions for source {width, height}
   * @param {Object} [targetDims] - Override dimensions for target {width, height}
   */
  calculateEdgePath(source, target, sourceDims = null, targetDims = null) {
    const dx = target.x - source.x;
    const dy = target.y - source.y;
    const angle = Math.atan2(dy, dx);

    const sourcePoint = this.getNodeEdgePoint(source, angle, sourceDims);
    const targetPoint = this.getNodeEdgePoint(
      target,
      angle + Math.PI,
      targetDims
    );

    const midX = (sourcePoint.x + targetPoint.x) / 2;
    const midY = (sourcePoint.y + targetPoint.y) / 2;

    return `M${sourcePoint.x},${sourcePoint.y} Q${midX},${midY} ${targetPoint.x},${targetPoint.y}`;
  }

  /**
   * Calculate the point on the edge of a node where an edge should connect.
   * Handles different node shapes: rectangle, rounded rect, and diamond.
   * @param {Object} node - The node object
   * @param {number} angle - The angle from node center
   * @param {Object} [dims] - Override dimensions {width, height}
   */
  getNodeEdgePoint(node, angle, dims = null) {
    const halfWidth = (dims?.width ?? this.nodeWidth) / 2;
    const halfHeight = (dims?.height ?? this.nodeHeight) / 2;

    if (node.type === "DecisionNode" && !dims) {
      // Diamond shape only when using default dimensions
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

    // Open file button
    const openFileBtn = document.getElementById("open-file-btn");
    if (openFileBtn) {
      openFileBtn.addEventListener("click", () => this.openFile());
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
    if (!searchInput) return;

    // Clicking the search bar opens the command palette in node search mode
    searchInput.addEventListener("focus", (e) => {
      e.preventDefault();
      searchInput.blur();
      CommandPalette.open("nodes");
    });

    // Keyboard shortcut Cmd+K also opens node search
    document.addEventListener("keydown", (e) => {
      if ((e.ctrlKey || e.metaKey) && !e.shiftKey && e.key === "k") {
        e.preventDefault();
        CommandPalette.open("nodes");
      }
    });
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
    // Create tooltip element for node previews and edge hover
    this.nodePreviewTooltip = document.createElement("div");
    this.nodePreviewTooltip.className = "node-preview-tooltip";
    this.nodePreviewTooltip.style.display = "none";
    document.body.appendChild(this.nodePreviewTooltip);
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
                <span class="preview-badge ${node.type}">${formatNodeType(
      node.type
    )}</span>
                <span class="preview-title">${escapeHtml(node.label)}</span>
            </div>
            ${
              shortDesc
                ? `<div class="preview-description">${escapeHtml(
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
      labelHtml = `<div class="edge-label-preview">${escapeHtml(
        edge.label
      )}</div>`;
    }

    tooltip.innerHTML = `
            ${labelHtml}
            <div class="preview-header">
                <span class="preview-badge ${targetNode.type}">${formatNodeType(
      targetNode.type
    )}</span>
                <span class="preview-title">${escapeHtml(
                  targetNode.label
                )}</span>
            </div>
            ${
              shortDesc
                ? `<div class="preview-description">${escapeHtml(
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
    if (FlowState.loadFromStorage()) {
      // Restore visited visual state
      this.visitedNodes.forEach((nodeId) => {
        d3.select(`#node-${nodeId}`).classed("visited", true);
      });
      this.goToNode(this.currentNode, null, false);
      // Update global cache toggle count after loading state
      this.updateGlobalCacheToggle();
      return;
    }

    // Otherwise, find start node
    const startNode = FlowState.getStartNode();
    if (startNode) {
      this.navigateToNode(startNode.id);
    }
  }

  restart() {
    // Clear state
    FlowState.reset();
    FlowState.clearStorage();

    // Reset visual state
    this.g
      .selectAll(".node-group")
      .classed("current", false)
      .classed("visited", false);

    // Only show collapsed nodes if not in alwaysExpandNodes mode
    if (!this.settings.alwaysExpandNodes) {
      this.g.selectAll(".node-collapsed").style("opacity", 1);
    }

    this.g
      .selectAll(".edge-path")
      .classed("incoming", false)
      .classed("outgoing", false);

    // Hide overlay
    document.getElementById("node-overlay").classList.add("hidden");

    // Reset expanded overlay states if enabled
    if (this.settings.alwaysExpandNodes) {
      document.querySelectorAll(".expanded-node-overlay").forEach((el) => {
        el.classList.remove("current", "visited");
      });
    }

    // Start fresh
    this.start();
  }

  navigateToNode(nodeId) {
    const prevNode = this.currentNode;
    const node = FlowState.navigateTo(nodeId);
    if (!node) return;
    this.goToNode(node, prevNode, true);
  }

  /**
   * Core navigation function - handles all the visual/state updates for going to a node
   * @param {Object} node - The node object to navigate to
   * @param {Object} prevNode - The previous current node (may be null)
   * @param {boolean} addToVisited - Whether to mark the previous node as visited
   */
  goToNode(node, prevNode = null, addToVisited = true) {
    // Reset keyboard edge selection to first edge
    this.selectedEdgeIndex = 0;

    // Hide main overlay during transition (only used when not in always-expand mode)
    if (!this.settings.alwaysExpandNodes) {
      document.getElementById("node-overlay").classList.add("hidden");
    }

    // Hide node preview tooltip
    this.hideNodePreview();

    // Restore visibility of previous node's collapsed shape and reset edge paths
    if (prevNode && !this.settings.alwaysExpandNodes) {
      d3.select(`#node-${prevNode.id} .node-collapsed`).style("opacity", 1);
      this.resetEdgesForNode(prevNode.id);
    }

    // Update SVG node classes
    if (prevNode) {
      d3.select(`#node-${prevNode.id}`)
        .classed("current", false)
        .classed("visited", true);
    }

    // Update visual state
    d3.select(`#node-${node.id}`).classed("current", true);

    // Update expanded overlay states if enabled
    if (this.settings.alwaysExpandNodes) {
      if (prevNode) {
        const prevOverlay = document.getElementById(
          `expanded-overlay-${prevNode.id}`
        );
        if (prevOverlay) {
          prevOverlay.classList.remove("current");
          prevOverlay.classList.add("visited");
        }
      }
      const currentOverlay = document.getElementById(
        `expanded-overlay-${node.id}`
      );
      if (currentOverlay) {
        currentOverlay.classList.add("current");
      }
    }

    // Highlight edges
    this.updateEdgeHighlights();

    // Update UI content (before zoom so it's ready when zoom completes)
    this.updateCurrentNodePanel();
    this.updateHistory();
    this.updateProgress();
    this.renderMiniMap();

    // Save state to localStorage
    FlowState.saveToStorage();

    // Zoom to node (overlay shown after zoom completes)
    this.zoomToNode(node);

    // In always-expand mode, highlight the first edge button of the new current node
    if (this.settings.alwaysExpandNodes) {
      // Clear keyboard-selected from all edge buttons first
      document
        .querySelectorAll(".expanded-node-overlay .edge-btn.keyboard-selected")
        .forEach((btn) => {
          btn.classList.remove("keyboard-selected");
        });
      // Highlight the first edge button of the current node
      const buttons = this.getCurrentEdgeButtons();
      if (buttons.length > 0) {
        this.highlightEdgeButton(buttons);
      }
    }
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

    // Hide the collapsed SVG node so only overlay shows (unless alwaysExpandNodes is on)
    if (!this.settings.alwaysExpandNodes) {
      d3.select(`#node-${this.currentNode.id} .node-collapsed`).style(
        "opacity",
        0
      );
    }

    // Auto-select first edge button for keyboard navigation
    const buttons = document.querySelectorAll("#overlay-actions .edge-btn");
    if (buttons.length > 0 && this.selectedEdgeIndex >= 0) {
      this.highlightEdgeButton(buttons);
    }

    // Recalculate edge positions for the expanded overlay size
    // Skip in alwaysExpandNodes mode - edges are already calculated for all expanded overlays
    if (!this.settings.alwaysExpandNodes) {
      this.updateEdgesForExpandedNode(overlay);
    }
  }

  /**
   * Update edge paths to connect to the expanded overlay instead of the collapsed node
   * Only used in normal mode - in alwaysExpandNodes mode, use updateAllEdgesForExpandedOverlays()
   */
  updateEdgesForExpandedNode(overlay) {
    if (!this.currentNode) return;
    // Skip in alwaysExpandNodes mode - edges are managed by updateAllEdgesForExpandedOverlays
    if (this.settings.alwaysExpandNodes) return;

    // Get overlay dimensions in SVG coordinate space (scaled by 1/1.6)
    const expandedDims = {
      width: overlay.offsetWidth / 1.6,
      height: overlay.offsetHeight / 1.6,
    };

    const nodeId = this.currentNode.id;
    const incomingEdgeIds = this.graph.incomingEdges[nodeId] || [];
    const outgoingEdgeIds = this.graph.outgoingEdges[nodeId] || [];

    // Update incoming edges (target is current node - use expanded dims for target)
    incomingEdgeIds.forEach((edgeId) => {
      const edge = this.edges[edgeId];
      const source = this.nodes[edge.source];
      const path = this.calculateEdgePath(
        source,
        this.currentNode,
        null,
        expandedDims
      );
      d3.select(`#edge-${edgeId}`).attr("d", path);
      d3.select(`#edge-hit-${edgeId}`).attr("d", path);
    });

    // Update outgoing edges (source is current node - use expanded dims for source)
    outgoingEdgeIds.forEach((edgeId) => {
      const edge = this.edges[edgeId];
      const target = this.nodes[edge.target];
      const path = this.calculateEdgePath(
        this.currentNode,
        target,
        expandedDims,
        null
      );
      d3.select(`#edge-${edgeId}`).attr("d", path);
      d3.select(`#edge-hit-${edgeId}`).attr("d", path);
    });
  }

  // Edge path methods unified - see calculateEdgePath() above

  updateCurrentNodePanel() {
    const overlay = document.getElementById("node-overlay");
    const node = this.currentNode;

    // Update type badge
    const badge = document.getElementById("overlay-badge");
    badge.textContent = formatNodeType(node.type);
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
      escapeHtml
    );

    // Use event delegation - attach once to container instead of per-element
    this.setupCacheEditorDelegation(container, "node");

    // Also update the global cache panel if it's open
    const globalPanel = document.getElementById("global-cache-panel");
    if (globalPanel && !globalPanel.classList.contains("hidden")) {
      this.renderGlobalCache();
    }
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
      btn.innerHTML = `${shortcutHint}<span class="arrow">→</span>${label}<span class="target">${truncateLabel(
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

  /**
   * Sets up event delegation for cache editors (handles both node and global cache).
   * Uses a marker to avoid duplicate listener setup.
   * @param {HTMLElement} container - The container element for cache rows
   * @param {string} cacheType - 'node' or 'global'
   */
  setupCacheEditorDelegation(container, cacheType) {
    // Skip if already set up for this cache type
    if (container.dataset.cacheType === cacheType) return;
    container.dataset.cacheType = cacheType;

    // Input event delegation
    container.addEventListener("input", (e) => {
      if (
        !e.target.classList.contains("cache-key") &&
        !e.target.classList.contains("cache-value")
      )
        return;

      const cache =
        cacheType === "node"
          ? this.nodeCache.get(this.currentNode.id) || {}
          : this.globalCache;
      const keyPrefix = cacheType === "node" ? "key_" : "global_";

      const needsRerender = CacheEditorHelpers.handleEdit(e, cache, keyPrefix);

      if (cacheType === "node") {
        this.nodeCache.set(this.currentNode.id, cache);
      }

      // Save state to localStorage after each edit
      FlowState.saveToStorage();
      
      // Update global cache toggle count
      this.updateGlobalCacheToggle();

      // Always update global cache panel if it's open (for real-time sync)
      if (cacheType === "node") {
        const globalPanel = document.getElementById("global-cache-panel");
        if (globalPanel && !globalPanel.classList.contains("hidden")) {
          this.renderGlobalCache();
        }
      }

      if (needsRerender) {
        const wasKey = e.target.classList.contains("cache-key");
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
          const toFocus = targetRow.querySelector(
            wasKey ? ".cache-key" : ".cache-value"
          );
          if (toFocus) {
            toFocus.focus();
            toFocus.setSelectionRange(
              toFocus.value.length,
              toFocus.value.length
            );
          }
        }
      }
    });

    // Click event delegation for delete buttons
    container.addEventListener("click", (e) => {
      if (!e.target.classList.contains("delete-cache-btn")) return;
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
        // Save state after deletion
        FlowState.saveToStorage();
        // Update global cache toggle count
        this.updateGlobalCacheToggle();
      }
    });
  }

  /**
   * Make an element draggable from anywhere on its surface.
   * Used for panels that should be draggable except on interactive content.
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
      badge.textContent = formatNodeType(node.type).charAt(0);

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
    const prevNode = this.currentNode;
    const node = FlowState.goBack();
    if (node) {
      this.goToNode(node, prevNode, false);
    }
  }

  /**
   * Time travel to a specific point in history without truncating
   * @param {number} index - The history index to travel to
   */
  timeTravel(index) {
    const prevNode = this.currentNode;
    const node = FlowState.timeTravel(index);
    if (node) {
      this.goToNode(node, prevNode, false);
    }
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

  /**
   * Get the edge buttons for the current node (works in both normal and always-expand modes)
   */
  getCurrentEdgeButtons() {
    if (this.settings.alwaysExpandNodes && this.currentNode) {
      // In always-expand mode, find buttons in the current node's expanded overlay
      const overlay = document.getElementById(
        `expanded-overlay-${this.currentNode.id}`
      );
      if (overlay) {
        return overlay.querySelectorAll(".overlay-actions .edge-btn");
      }
      return [];
    } else {
      // In normal mode, use the main overlay
      return document.querySelectorAll("#overlay-actions .edge-btn");
    }
  }

  selectNextEdge() {
    const buttons = this.getCurrentEdgeButtons();
    if (buttons.length === 0) return;

    this.selectedEdgeIndex = Math.min(
      this.selectedEdgeIndex + 1,
      buttons.length - 1
    );
    this.highlightEdgeButton(buttons);
  }

  selectPrevEdge() {
    const buttons = this.getCurrentEdgeButtons();
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
    const buttons = this.getCurrentEdgeButtons();
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

    // Build a combined view of global cache + all node caches
    let html = "";

    // First, render global-only entries (not tied to any node)
    const globalEntries = Object.entries(this.globalCache);
    if (globalEntries.length > 0) {
      html += '<div class="cache-section"><div class="cache-section-header">Global</div>';
      globalEntries.forEach(([key, value]) => {
        html += this.renderGlobalCacheRow(key, value, null);
      });
      html += '</div>';
    }

    // Add empty row for new global entries
    html += `
      <div class="cache-row empty-row global-entry" data-node-id="">
        <textarea class="cache-key" placeholder="Add global key..." data-field="key" data-original-key=""></textarea>
        <textarea class="cache-value" placeholder="Value" data-field="value" data-key=""></textarea>
        <button class="delete-cache-btn" style="visibility:hidden">×</button>
      </div>
    `;

    // Then, render entries from each node's cache
    this.nodeCache.forEach((cache, nodeId) => {
      const entries = Object.entries(cache);
      if (entries.length === 0) return;

      const node = this.nodes[nodeId];
      const nodeLabel = node ? node.label : nodeId;
      const isCurrent = this.currentNode?.id === nodeId;

      html += `<div class="cache-section node-cache-section ${isCurrent ? 'current-node' : ''}">`;
      html += `<div class="cache-section-header">
        <span class="node-cache-label" title="${escapeHtml(nodeLabel)}">${escapeHtml(truncateLabel(nodeLabel, 25))}</span>
        <button class="jump-to-node-btn" data-node-id="${escapeHtml(nodeId)}" title="Jump to node">→</button>
      </div>`;

      entries.forEach(([key, value]) => {
        html += this.renderGlobalCacheRow(key, value, nodeId);
      });
      html += '</div>';
    });

    if (globalEntries.length === 0 && this.nodeCache.size === 0) {
      html = '<div class="empty-cache">No data stored yet</div>' + html.slice(html.indexOf('<div class="cache-row empty-row'));
    }

    container.innerHTML = html;

    // Setup event delegation for the global cache panel
    this.setupGlobalCacheEditorDelegation(container);

    // Update toggle button to show count
    this.updateGlobalCacheToggle();
  }

  /**
   * Render a single row in the global cache panel
   */
  renderGlobalCacheRow(key, value, nodeId) {
    const nodeIdAttr = nodeId ? `data-node-id="${escapeHtml(nodeId)}"` : 'data-node-id=""';
    const nodeClass = nodeId ? 'node-entry' : 'global-entry';
    return `
      <div class="cache-row ${nodeClass}" ${nodeIdAttr}>
        <textarea class="cache-key" placeholder="Key" data-field="key" data-original-key="${escapeHtml(key)}">${escapeHtml(key)}</textarea>
        <textarea class="cache-value" placeholder="Value" data-field="value" data-key="${escapeHtml(key)}">${escapeHtml(value)}</textarea>
        <button class="delete-cache-btn" data-key="${escapeHtml(key)}">×</button>
      </div>
    `;
  }

  /**
   * Sets up event delegation for the global cache panel
   * Handles both global entries and node cache entries
   */
  setupGlobalCacheEditorDelegation(container) {
    // Skip if already set up
    if (container.dataset.delegationSetup === "true") return;
    container.dataset.delegationSetup = "true";

    // Input event delegation - only commit changes on blur
    container.addEventListener("blur", (e) => {
      if (!e.target.classList.contains("cache-key") && 
          !e.target.classList.contains("cache-value")) return;

      const row = e.target.closest(".cache-row");
      const nodeId = row.dataset.nodeId;
      const isGlobalEntry = nodeId === "";

      const keyInput = row.querySelector(".cache-key");
      const valInput = row.querySelector(".cache-value");
      const originalKey = keyInput.dataset.originalKey;
      const currentKey = keyInput.value.trim();
      const currentValue = valInput.value;

      // Get the appropriate cache
      let cache;
      if (isGlobalEntry) {
        cache = this.globalCache;
      } else {
        cache = this.nodeCache.get(nodeId) || {};
      }

      let needsRerender = false;

      if (originalKey) {
        // Modification of existing entry
        if (currentKey !== originalKey) {
          // Key changed
          delete cache[originalKey];
          if (currentKey) {
            cache[currentKey] = currentValue;
          }
          needsRerender = true;
        } else if (currentKey) {
          // Just value changed
          cache[currentKey] = currentValue;
        }
      } else {
        // New entry creation
        if (currentKey) {
          cache[currentKey] = currentValue;
          needsRerender = true;
        }
      }

      // Update the cache
      if (!isGlobalEntry) {
        this.nodeCache.set(nodeId, cache);
        // Also update the node overlay if it's the current node
        if (this.currentNode?.id === nodeId) {
          this.renderOverlayData();
        }
      }

      // Save state
      FlowState.saveToStorage();

      if (needsRerender) {
        this.renderGlobalCache();
      }
    }, true); // Use capture phase for blur

    // Click event delegation for delete buttons and jump buttons
    container.addEventListener("click", (e) => {
      // Handle delete button
      if (e.target.classList.contains("delete-cache-btn")) {
        e.stopPropagation();
        const row = e.target.closest(".cache-row");
        const nodeId = row.dataset.nodeId;
        const isGlobalEntry = nodeId === "";
        const key = e.target.dataset.key;

        if (!key) return;

        let cache;
        if (isGlobalEntry) {
          cache = this.globalCache;
        } else {
          cache = this.nodeCache.get(nodeId) || {};
        }

        delete cache[key];

        if (!isGlobalEntry) {
          this.nodeCache.set(nodeId, cache);
          // Also update the node overlay if it's the current node
          if (this.currentNode?.id === nodeId) {
            this.renderOverlayData();
          }
        }

        FlowState.saveToStorage();
        this.renderGlobalCache();
        return;
      }

      // Handle jump-to-node button
      if (e.target.classList.contains("jump-to-node-btn")) {
        e.stopPropagation();
        const nodeId = e.target.dataset.nodeId;
        if (nodeId && this.nodes[nodeId]) {
          this.navigateToNode(nodeId);
        }
        return;
      }
    });
  }

  updateGlobalCacheToggle() {
    const toggle = document.getElementById("global-cache-toggle");
    if (!toggle) return;

    // Count all entries: global cache + all node caches
    let count = Object.keys(this.globalCache).length;
    this.nodeCache.forEach((cache) => {
      count += Object.keys(cache).length;
    });

    const countBadge =
      count > 0 ? ` <span class="cache-count">(${count})</span>` : "";
    toggle.innerHTML = `Global Data${countBadge}`;
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
      historyIndex: this.historyIndex,
      visitedNodes: Array.from(this.visitedNodes),
      globalCache: this.globalCache,
      nodeCache: Object.fromEntries(this.nodeCache),
      // Include the original flow data for complete export
      flowData: this.flowData,
    };

    const json = JSON.stringify(state, null, 2);
    const blob = new Blob([json], { type: "application/json" });
    const url = URL.createObjectURL(blob);

    const a = document.createElement("a");
    a.href = url;
    a.download = `flowplay-export-${
      this.flowData?.name || "flow"
    }-${Date.now()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  // =========================================
  // OPEN FILE
  // =========================================
  openFile() {
    // Create a hidden file input
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".json";
    input.style.display = "none";

    input.addEventListener("change", async (e) => {
      const file = e.target.files[0];
      if (!file) return;

      try {
        this.showLoading(true);
        const text = await file.text();
        const data = JSON.parse(text);

        // Check if this is an exported session state (has flowData property)
        // or a raw flow JSON file
        if (data.flowData) {
          // This is an exported session - restore full state
          await this.loadFromExport(data);
        } else if (data.nodes && data.edges) {
          // This is a raw flow JSON file
          await this.loadNewFlow(data);
        } else {
          throw new Error("Invalid file format: must be a flow JSON or exported session");
        }

        this.showLoading(false);
      } catch (error) {
        console.error("Failed to load file:", error);
        alert("Failed to load file: " + error.message);
        this.showLoading(false);
      }

      // Clean up
      document.body.removeChild(input);
    });

    document.body.appendChild(input);
    input.click();
  }

  /**
   * Load a new flow from raw flow JSON data
   */
  async loadNewFlow(flowData) {
    // Reset all state
    FlowState.reset();

    // Initialize with new flow data
    FlowState.init(flowData);

    // Update title
    document.getElementById("flowchart-name").textContent = flowData.name;

    // Re-render the flowchart
    this.g.selectAll("*").remove();
    this.renderFlowchart();

    // Update mini-map
    this.renderMiniMap();

    // Setup expanded overlays if needed
    if (this.settings.alwaysExpandNodes) {
      this.setupExpandedOverlays();
    }

    // Start the flow
    this.start();
  }

  /**
   * Load from an exported session state (includes flow data and session state)
   */
  async loadFromExport(exportData) {
    // Load the flow data first
    await this.loadNewFlow(exportData.flowData);

    // Restore session state
    FlowState.history = exportData.history || [];
    FlowState.historyIndex = exportData.historyIndex ?? -1;
    FlowState.visitedNodes = new Set(exportData.visitedNodes || []);
    FlowState.globalCache = exportData.globalCache || {};
    FlowState.nodeCache = new Map(Object.entries(exportData.nodeCache || {}));

    // Restore visited visual state
    this.visitedNodes.forEach((nodeId) => {
      d3.select(`#node-${nodeId}`).classed("visited", true);
    });

    // Navigate to the current node from the export
    if (exportData.currentNode && this.nodes[exportData.currentNode]) {
      FlowState.currentNode = this.nodes[exportData.currentNode];
      this.goToNode(this.currentNode, null, false);
    }

    // Update global cache UI
    this.renderGlobalCache();
    this.updateGlobalCacheToggle();
  }

  // =========================================
  // SETTINGS PANEL
  // =========================================
  setupSettingsPanel() {
    const settingsBtn = document.getElementById("settings-btn");
    if (!settingsBtn) return;

    // Settings button opens command palette
    settingsBtn.addEventListener("click", () => {
      CommandPalette.open("commands");
    });
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

    // Always expand nodes - show overlays for all nodes
    document.body.classList.toggle(
      "always-expand-nodes",
      this.settings.alwaysExpandNodes
    );

    // Setup or tear down expanded overlays
    if (this.nodes && Object.keys(this.nodes).length > 0) {
      this.setupExpandedOverlays();
    }
  }

  setSetting(key, value) {
    if (this.settings.hasOwnProperty(key)) {
      this.settings[key] = value;
      SettingsManager.save(this.settings);
      this.applySettings();
    }
  }
}

// Initialize on load
document.addEventListener("DOMContentLoaded", () => {
  const app = new FlowPlay();
  app.init();
});
