# Symbol formatting implementation plan

**Goal:** Add subscript/superscript controls with a live preview at the top of the existing symbol picker.

**Architecture:** Keep QLineEdit label storage and existing symbol insertion signals. Store scripts as escaped sub/sup markup for Plotly and Qt previews; convert scripts to mathtext for Matplotlib rendering and exports.

**Tech stack:** PySide6, Plotly, Matplotlib, unittest.

1. Add failing tests for formatting selected text, inserting scripts at the cursor, live preview placement, escaping, cancellation, and existing symbol insertion.
2. Extend `graphs/symbol_picker.py` with a top preview, script text entry, mutually exclusive subscript/superscript controls and Insert. Preserve the target's selection while the popup has focus. Keep symbols underneath.
3. Add `utils/label_formatting.py` for safe preview markup and Matplotlib conversion. Cover plain labels, combined scripts and special characters.
4. Apply conversion at Matplotlib label rendering boundaries in heatmap exports, Multi Property exports and animation. Plotly keeps the stored markup.
5. Run symbol-picker, label-editor and export tests. Inspect an offscreen screenshot and confirm the preview is at the top. Log formatting and conversion using `debug_print`.

Completed: all five steps. Verified 65 focused tests across picker interactions, label editors, actual PNG rendering, export layouts and animation. Inspected the popup screenshot with its preview at the top. Review confirmed full and partial script reformatting and insertion inside an existing script remain exportable.

Follow-up: added Backspace, Normal and Clear; explicit light backgrounds and dark text for all control states; markup-aware editing with undo and UTF-16 cursor positions. Verified 77 focused tests and visually checked the real app stylesheet under a dark palette. Review confirmed edited plain-label entities render consistently in exports.

Notation correction: replaced exposed HTML in label fields with `_xx`, `^p` and grouped expressions such as `_{x y}`. A shared parser retains legacy-label compatibility and source positions for editing. Plotly chart serialization and Matplotlib rendering translate notation for display. Verified 114 focused checks, including real PNG/animation exports and Custom Graph titles. Review confirmed angle-bracket labels and selections containing notation markers are handled correctly.

2026-10-28 mixed-entry correction: formatting buttons now act on selected entry text before the parent-label selection. Pending entries preserve independently formatted spans and explicit `^xx_yy` notation. Initial and post-insertion mode is Normal. Cancel/reopen clears mixed-entry state. Verified 119 focused tests and the visible-popup sequence producing `σ^xx_yy`; review confirmed cancellation does not leak composition state.

2026-10-28 full-label live synchronization supersedes the insertion-buffer workflow above: the popup now loads the entire existing label and mirrors text, cursor and selection with the original QLineEdit. Symbols, formatting, keyboard edits, Backspace and Clear use the same editor; Done/Enter/outside closing keeps live edits. Typing notifications are debounced, while button actions notify immediately. Blank edits remain mirrored without triggering auto-title refill until the user replaces the text or closes the popup. Verified 108 focused checks including actual Custom Graph title clearing/replacement, source and dialog undo/redo, signal-loop protection, notation, exports and animation. Visually checked the popup and both synchronization directions. Read-only review found no remaining issues.
