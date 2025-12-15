# FlowPlay Export Format

This document describes the JSON format used when exporting session state from FlowPlay.

## Overview

FlowPlay supports two types of JSON files:

1. **Raw Flow Files** - The basic flow definition with nodes and edges
2. **Exported Session Files** - Complete session state including the flow data and user progress

When you use the "Export Session State" button (⬇) or the `exportState` command, FlowPlay exports a complete session file that includes both the flow definition and your current session state.

## File Structure

### Raw Flow File

A raw flow file contains just the flow definition:

```json
{
  "name": "Flow Name",
  "metadata": {},
  "nodes": [...],
  "edges": [...],
  "graph": {
    "incomingEdges": {...},
    "outgoingEdges": {...}
  }
}
```

### Exported Session File

An exported session file includes the full flow data plus session state:

```json
{
  "flowName": "Flow Name",
  "exportDate": "2024-01-15T10:30:00.000Z",
  "currentNode": "node-uuid-here",
  "history": ["node-1-uuid", "node-2-uuid", ...],
  "historyIndex": 5,
  "visitedNodes": ["node-1-uuid", "node-2-uuid", ...],
  "globalCache": {
    "key1": "value1",
    "key2": "value2"
  },
  "nodeCache": {
    "node-uuid-1": {
      "local_key": "local_value"
    },
    "node-uuid-2": {
      "another_key": "another_value"
    }
  },
  "flowData": {
    "name": "Flow Name",
    "metadata": {},
    "nodes": [...],
    "edges": [...],
    "graph": {...}
  }
}
```

## Field Descriptions

### Session State Fields

| Field | Type | Description |
|-------|------|-------------|
| `flowName` | string | Name of the flow (copied from flow data) |
| `exportDate` | string | ISO 8601 timestamp of when the export was created |
| `currentNode` | string | UUID of the currently active node |
| `history` | array | Ordered list of node UUIDs representing navigation history |
| `historyIndex` | number | Current position in the history array (for back/forward navigation) |
| `visitedNodes` | array | List of node UUIDs that have been visited |
| `globalCache` | object | Key-value pairs stored in the global data store |
| `nodeCache` | object | Map of node UUIDs to their local key-value caches |
| `flowData` | object | The complete flow definition (see below) |

### Flow Data Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Display name of the flow |
| `metadata` | object | Optional metadata for the flow |
| `nodes` | array | Array of node definitions |
| `edges` | array | Array of edge definitions |
| `graph` | object | Pre-computed graph structure for navigation |

### Node Definition

```json
{
  "id": "uuid-string",
  "type": "StartNode|ProcessNode|DecisionNode|EndNode",
  "label": "Display Label",
  "metadata": {
    "description": "Markdown description text"
  }
}
```

### Edge Definition

```json
{
  "id": "uuid-string",
  "source": "source-node-uuid",
  "target": "target-node-uuid",
  "label": "Optional edge label"
}
```

### Graph Structure

```json
{
  "incomingEdges": {
    "node-uuid": ["edge-uuid-1", "edge-uuid-2"]
  },
  "outgoingEdges": {
    "node-uuid": ["edge-uuid-3", "edge-uuid-4"]
  }
}
```

## Loading Files

FlowPlay can load both file types:

- **Raw Flow Files**: Starts a fresh session with the new flow
- **Exported Session Files**: Restores the complete session state including your position, history, and all cached data

Use `⌘O` (Cmd+O) or the "Open flow file" button (📂) to load a file. FlowPlay automatically detects the file type based on its structure.

## Use Cases

### Sharing Progress

Export your session to share your current progress with others. They can import the file to see exactly where you were in the flow and access any notes/data you've stored.

### Backup

Regularly export your session to create backups of your progress and cached data.

### Offline Access

Export a session with the embedded flow data to have a self-contained file that can be loaded without needing the original flow file.

## Browser Storage

FlowPlay also automatically saves session state to browser localStorage for persistence across page refreshes. The export feature provides a way to create portable backups that aren't tied to browser storage.
