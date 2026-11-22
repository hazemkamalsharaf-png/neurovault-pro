# Implementation Plan: Import File Feature

## Overview

Add an "Import File" button to The Vault view that lets users upload local documents (.txt, .md, .pdf, .docx). Text is extracted and saved as a new snippet in the existing database, using the filename (without extension) as the title and file extension as the language/tag.

## Architecture Decisions

- **Lazy imports**: `pypdf` and `python-docx` are imported inside the import handler function so the app never crashes at startup if they're missing. A friendly error message is shown instead.
- **Language field reuse**: The existing `language` column in `snippets` stores the file extension (e.g., "pdf", "docx") — consistent with how it already works and doubles as a tag-like identifier.
- **Title from filename**: Extension stripped for cleaner display names. If extraction fails, user is notified without any crash or data loss.
- **Button placement**: Added below the search bar in The Vault header row, using an inline `CTkFrame` so it doesn't disrupt existing layout.

## Task List

### Phase 1: Add Import Button to VaultFrame (gui.py)
- [ ] Task 1: Add "Import File" button + `_import_file()` handler stub that checks for optional deps and calls file dialog
- [ ] Task 2: Implement text extraction logic (`_extract_text()`) supporting .txt, .md, .pdf, .docx

### Checkpoint: Phase 1
- [ ] Button appears in The Vault view
- [ ] File dialog opens and extracts text from all 4 formats
- [ ] Graceful error if file is empty or deps are missing

### Phase 2: Save Extracted Text as Snippet + Refresh
- [ ] Task 3: Wire extraction result to `db.save_snippet()` and refresh the Vault list

### Checkpoint: Phase 2
- [ ] Imported files appear in The Vault snippet list immediately after import
- [ ] Detail panel shows correct title, language (extension), and content
- [ ] All existing features still work (search, delete, double-click detail)

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| pypdf/python-docx missing at runtime | Medium | Lazy imports with try/except + user-friendly error message |
| Binary/corrupt files cause extraction to fail | Low | Wrap each format handler in try/except; show clean error |
| Large PDFs/docx slow the UI thread | Low | Use `.after()` for non-blocking refresh after import completes |

## Open Questions
- None — all requirements are clear from the spec.
