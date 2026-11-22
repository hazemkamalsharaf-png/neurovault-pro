# Tasks: Import File Feature

## Phase 1: Add Import Button + Text Extraction (gui.py only)

- [x] Task 1: Add "Import File" button below search bar in `VaultFrame.__init__()` and create `_import_file()` handler stub that checks for optional deps, opens file dialog, and calls `_extract_text()`
- [x] Task 2: Implement `_extract_text(file_path)` method on `VaultFrame` supporting `.txt`, `.md`, `.pdf`, `.docx` with lazy imports and error handling

### Checkpoint: Phase 1 ✅
- [x] Button appears in The Vault view next to search bar
- [x] File dialog opens filtering for .txt, .md, .pdf, .docx
- [x] Text extracted correctly from all 4 formats
- [x] Graceful error messages if file is empty or deps missing

## Phase 2: Save as Snippet + Refresh Vault

- [x] Task 3: Wire `_import_file()` to call `db.save_snippet()`, show status confirmation, and refresh the Vault list immediately after import completes

### Checkpoint: Phase 2 ✅
- [x] Imported files appear in The Vault snippet list immediately
- [x] Detail panel shows correct title (filename sans extension), language (extension), and content
- [x] All existing features still work (search, delete, double-click detail, navigation)
- [x] App runs without syntax errors (`py_compile` passes for all 5 files)
