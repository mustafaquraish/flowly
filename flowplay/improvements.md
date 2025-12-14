# FlowPlay UX Improvements

## User-Requested Improvements (4)

1. ✅ **Draggable incoming panels from anywhere** - Make incoming cache panels draggable from any non-interactive area (not just drag handle), excluding text content
2. ✅ **History panel behavior** - Show 4 items instead of 5; clicking history should "time travel" back (truncating future), and forking creates new path
3. ✅ **Edge clicking for current node** - Clicking edges connected to current node should navigate to the other connected node
4. ✅ **Arrow positioning fix** - Arrows must ALWAYS connect to node edges, not overlap with node shapes (works for all node types including expanded)

## Additional Improvements (15+)

5. ✅ **Mini-map navigation** - Add a small overview map in corner showing all nodes, current position, and allowing click-to-navigate
6. ✅ **Search/filter nodes** - Add search box (Ctrl+K) to quickly find and jump to nodes by name
7. ✅ **Breadcrumb path display** - Show abbreviated path from start node to current with clickable segments
8. ✅ **Node preview on hover** - When hovering over a node (not current), show a tooltip preview of its description
9. ✅ **Progress indicator** - Show how far through the flow you are (x/y nodes visited with progress bar)
10. ✅ **Zoom level indicator** - Display current zoom percentage, click to reset to 100%
11. ✅ **Auto-save state to localStorage** - Persist current node, history, cache data between sessions
12. ✅ **Export flow state** - Button to export current session state (visited nodes, cache values) as JSON
13. ✅ **Edge labels always visible** - Edge labels show full text on hover via tooltip
14. ⬜ **Improved focus management** - After navigation, automatically focus the first interactive element
15. ✅ **Double-click to expand/collapse** - Double-click on node in overview to zoom and navigate
16. ⬜ **Touch/swipe support** - Add swipe gestures for mobile: swipe left/right to navigate edges, pinch to zoom
17. ✅ **Animated edge flow** - Outgoing edges show animated dashed "pulse" along the path direction (CSS)
18. ⬜ **Node connection count badges** - Show small badges on nodes indicating in/out edge counts
19. ⬜ **Quick actions menu** - Right-click context menu on nodes for quick actions (go to, copy name, etc.)
20. ✅ **Loading indicator** - Show spinner while flowchart data is loading
21. ✅ **Auto-hide controls** - Controls fade after 5 seconds of inactivity

## Batch 2 - User-Requested Improvements (Dec 14)

22. ✅ **Wider edge click area** - Invisible wider hit area for edges (20px stroke) for easier clicking
23. ✅ **Edge hover shows connected node** - Hovering over edges from current node shows preview of the connected node
24. ✅ **Global settings menu** - Settings panel to toggle features (mini-map, incoming panels, progress, etc.)
25. ✅ **Text selection in incoming panels** - Cache table text is now selectable without triggering drag
26. ✅ **History preserves future** - Time-traveling back keeps future history visible; only truncates on different path
27. ✅ **Re-zoom on current node** - Clicking current node while zoomed out re-zooms to it

## Batch 3 - User-Requested Improvements (Dec 14)

28. ✅ **Back button in history panel** - Moved back button from overlay to history panel for better visibility
29. ✅ **History shows max 4 items** - History panel shows 4 visible items with +N buttons for both past and future
30. ✅ **First edge auto-selected** - When navigating to a node, first edge is automatically selected so Enter works immediately
31. ✅ **Combined edge tooltip** - Edge label and node preview combined into single tooltip on hover
32. ✅ **All edges show preview** - Any edge (not just current node's edges) shows target node preview on hover
33. ✅ **Expanded node arrow positioning** - Arrow endpoints recalculated based on expanded overlay size, not collapsed node

## Batch 2 - Additional Improvements (10)

34. ⬜ **Keyboard focus trap in overlay** - Tab key cycles through interactive elements within overlay
35. ⬜ **Highlight path to current node** - Option to highlight all edges from start to current node
36. ⬜ **Node statistics panel** - Show stats about visited nodes, cache entries, path length
37. ⬜ **Undo/Redo navigation** - Ctrl+Z to go back, Ctrl+Shift+Z to go forward in history
38. ⬜ **Copy node info to clipboard** - Button to copy node title/description/cache as text
39. ⬜ **Fullscreen mode** - Toggle fullscreen for distraction-free navigation
40. ⬜ **Keyboard-only navigation mode** - Full keyboard control without mouse needed
41. ⬜ **Theme toggle** - Switch between dark/light mode
42. ⬜ **Zoom to fit selection** - When multiple nodes selected, fit them all in view
43. ⬜ **Edge label search** - Include edge labels in search results

## Summary

- **29 improvements completed** ✅
- **10 improvements pending** ⬜

### Completed Features:
- Mini-map with click navigation
- Node search with Ctrl+K shortcut
- Breadcrumb navigation in overlay
- Node preview tooltips on hover
- Progress indicator (visited/total)
- Zoom level display with reset
- LocalStorage state persistence
- Export session state button
- Edge label tooltips
- Double-click navigation
- Loading spinner
- Auto-hiding controls
- Improved history with time-travel
- Edge clicking for navigation
- Arrow positioning fixes
- Draggable panels
- Wider edge click areas
- Edge hover shows connected node preview
- Global settings panel
- Text selection in cache panels
- History preserves future items
- Re-zoom on current node click
- Back button in history panel
- History 4-item limit with +N
- First edge auto-selected
- Combined tooltip for edges
- All edges show node preview
- Expanded node arrow recalculation

### Keyboard Shortcuts:
- `Ctrl+K` - Search nodes
- `1-9` - Select edge option
- `↑↓` - Navigate edges
- `Enter` - Activate selected
- `B` - Go back
- `Esc` - Close overlay
- `R` - Restart
- `F` - Fit to view
- `+/-` - Zoom
- `?` - Toggle help
