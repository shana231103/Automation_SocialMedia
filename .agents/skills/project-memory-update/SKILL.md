---
name: project-memory-update
description: Incrementally update Project Memory using Git diff and file change detection. Only regenerates affected memory layers. Never rebuilds the entire memory unless explicitly requested. Supports Markdown, JSON indexes, SQLite metadata, embedding manifest, and Qdrant synchronization plan updates.
---

# Skill: Project Memory Update

## Purpose

Perform an **incremental update** of Project Memory based on files changed since the last memory sync.

This Skill is the **maintenance engine** of the Project Memory Platform.

Use this Skill:
- After completing a feature, phase, or PR.
- Before planning a new feature to ensure memory is fresh.
- On a scheduled basis in automated workflows.
- Whenever `git status` shows significant changes.

For a first-time or full rebuild, use **`project-memory-bootstrap`** instead.

---

## Role

You are acting as a **Principal AI Platform Architect** and **Knowledge Base Synchronization Engineer**.

You have full **read-only** access to source code and full **write** access to `memory_root`.

Your responsibility is to **detect exactly what changed** in the project since the last memory update and **surgically update only the affected memory documents**.

---

## Capability Boundary

**This Skill owns ONLY:**
```
<memory_root>/        (default: .agents/memory/)
```

**This Skill MUST NEVER:**
- Modify source code
- Modify test files
- Modify build or CI files
- Modify project documentation outside `memory_root`
- Implement features
- Execute builds or tests
- Perform Git commits, pushes, or tags
- Populate vector databases directly (only generate sync plans)

---

## Configuration

On startup, read `.agents/memory.config.json`.

**If the file does NOT exist**, print:

```
Project Memory is not initialized.

Run project-memory-bootstrap first to create the initial memory.
```

Then STOP.

**If `memory_root` does not exist or `project-summary.md` is missing**, print:

```
Project Memory has not been bootstrapped.

Run project-memory-bootstrap to generate the initial memory before running updates.
```

Then STOP.

---

## Workflow

### Step 1 — Load Configuration & State

1. Read `.agents/memory.config.json`.
2. Read `memory_root/memory-state.json` if it exists (tracks last update timestamp and git hash).
3. Determine the last known Git commit hash from `memory-state.json` or prompt the user.
4. Record update start timestamp.

**`memory-state.json` schema:**
```json
{
  "last_updated_at": "ISO8601",
  "last_git_hash": "abc123",
  "memory_version": "1.0.0",
  "layers_generated": ["summary", "architecture", "modules", "services", "repositories", "apis", "entities", "lessons", "indexes", "rag", "embeddings"]
}
```

---

### Step 2 — Change Detection

Use all available signals to detect what changed.

**Signal 1 — Git (preferred when available)**

```bash
# Files changed since last memory update
git diff --name-only <last_git_hash> HEAD

# Uncommitted/unstaged changes
git status --short

# Recent commits for context
git log --oneline -20

# Current HEAD hash
git rev-parse HEAD
```

**Signal 2 — File system fallback (when Git is unavailable)**

Compare file modification timestamps in the project against the `last_updated_at` timestamp in `memory-state.json`.

**Signal 3 — Explicit user input**

If the user specifies files or modules in parameters, treat those as the changed set regardless of Git state.

---

### Step 3 — Change Classification

Classify each changed file into a change type and map it to affected memory layers:

| Change Type | Memory Layers to Update |
|-------------|------------------------|
| New file added | Relevant module, service, repo, entity, or API memory + JSON indexes + RAG indexes |
| File modified | Same as above |
| File deleted | Remove or update all memory references to that file |
| New module directory | Generate new module memory file + update module-index |
| Interface changed | Update service memory + symbol index + dependency graph |
| API route changed | Update api memory + api-index.json |
| Entity/DTO changed | Update entity memory + entity-index.json + embedding manifest |
| Migration added | Update repository memory + migration-notes.md |
| Config changed | Update project-summary.md |
| Makefile changed | Update project-summary.md (build commands) |

---

### Step 4 — File-to-Memory Mapping

Use `indexes/file-map.json` to locate which memory documents own each changed file.

If `file-map.json` is missing or stale:
1. Re-analyze the changed files directly.
2. Determine ownership from folder structure and naming.
3. Update `file-map.json` after regenerating affected memory.

**Mapping rules:**

| File Pattern | Memory Target |
|-------------|--------------|
| `*/usecase/*.go` | `modules/[module].md`, `services/[service].md` |
| `*/repository/*.go` | `repositories/[repo].md` |
| `*/handler/*.go` or `*/router/*.go` | `apis/[group].md` |
| `*/entity/*.go` or `*/domain/*.go` | `entities/[group].md` |
| `*/service/*.go` | `services/[service].md` |
| `go.mod`, `package.json`, `pyproject.toml` | `project-summary.md` |
| `Makefile`, `justfile` | `project-summary.md` |
| `docs/architecture/` | `architecture/[area].md` |
| `migrations/` | `repositories/*.md`, `lessons/migration-notes.md` |
| `.env.example`, `config/` | `project-summary.md` |

---

### Step 5 — Incremental Memory Regeneration

Regenerate **only** the memory documents mapped to changed files.

**Regeneration rules:**

1. **Markdown files** — Re-read affected source files and rewrite only the sections that changed. Preserve all sections that were not affected.
2. **JSON indexes** — Update only the affected entries. Validate the JSON remains parseable after update.
3. **RAG Markdown indexes** — Update only the rows or entries related to changed components.
4. **Embedding manifest** — Add new chunks for added sections. Update chunks for modified sections. Remove chunks for deleted files.
5. **Qdrant sync plan** — Generate a sync plan file listing which chunks to upsert and which to delete.
6. **SQLite schema** — No changes to schema unless explicitly requested. Update `memory-state.json` only.
7. **Lessons files** — APPEND new lessons discovered during the update. Never overwrite existing entries.

**Never:**
- Truncate or overwrite entire memory files when only a section changed.
- Delete lessons entries.
- Rebuild all JSON indexes when only one module changed.

---

### Step 6 — Qdrant Synchronization Plan

If `vector_provider` is `qdrant` or `chroma` in config, generate:

**`rag/vector-sync-plan.json`**

```json
{
  "generated_at": "ISO8601",
  "collection": "...",
  "upsert": [
    {
      "id": "chunk-id",
      "text": "Updated text content",
      "metadata": {
        "type": "module",
        "module": "cache",
        "tags": ["caching"]
      }
    }
  ],
  "delete": [
    { "id": "chunk-id-of-deleted-section" }
  ]
}
```

This plan is consumed by an external pipeline. This Skill does NOT upload to vector databases.

---

### Step 7 — Update memory-state.json

After all updates are complete:

```json
{
  "last_updated_at": "ISO8601 — current timestamp",
  "last_git_hash": "current HEAD hash",
  "memory_version": "1.0.0",
  "last_run_mode": "incremental",
  "files_changed": 12,
  "memory_docs_updated": 5,
  "layers_generated": ["modules", "services", "indexes", "rag", "embeddings"]
}
```

---

### Step 8 — Quality Validation

Before finishing, validate:

- [ ] Only affected memory documents were modified.
- [ ] No source code copied verbatim (summaries only).
- [ ] JSON indexes remain valid (parseable, no broken references).
- [ ] `file-map.json` updated to reflect any new or deleted files.
- [ ] Lessons files only appended (no existing entries overwritten).
- [ ] Embedding manifest updated (new chunks added, deleted chunks removed).
- [ ] `memory-state.json` updated with current timestamp and Git hash.
- [ ] If vector provider configured, `rag/vector-sync-plan.json` generated.

---

## Full Rebuild Mode

If the user explicitly requests a full rebuild:

```yaml
mode: full
```

Behavior:
- Clear all files in `memory_root` except `lessons/` (lessons are always preserved).
- Re-run the full analysis as if running `project-memory-bootstrap`.
- Regenerate all layers from scratch.
- Preserve all lessons entries.

---

## Parameters

```yaml
mode: auto
# Options:
#   auto       — detect changes and run incremental (default)
#   incremental — force incremental mode
#   full        — force full rebuild (clears memory except lessons)
#   lessons     — only update lessons/ files

workspace: auto

config_file: .agents/memory.config.json

target_files: []
# Optional: list specific files to update memory for
# Example: ["internal/cache/service.go", "internal/auth/handler.go"]

target_layers: all
# Options: all | summary | architecture | modules | services |
#          repositories | apis | entities | lessons | indexes | rag | embeddings

git_aware: true
# Use git diff to detect changes

since_commit: auto
# Git hash to diff from. Default: last hash in memory-state.json
```

---

## Workspace Strategy

```
memory-state.json (last known state)
        ↓
git diff / git status (change detection)
        ↓
file-map.json (ownership lookup)
        ↓
Affected source files only (targeted reads)
        ↓
Update only affected memory documents
```

Never read the entire workspace unless `mode: full`.

---

## IDE Skill Hardening & Boundary Rules

### 1. Single Responsibility
Incrementally update Project Memory based on detected file changes. Once the Completion Report is printed, STOP.

### 2. Never Execute Next Phase
Do NOT invoke another Skill, generate source code, commit to Git, or call external databases.

### 3. Surgical Updates Only
Never overwrite or truncate memory documents beyond the changed sections. Preserve all unchanged content.

### 4. Lessons Are Append-Only
Never delete or overwrite existing lessons entries. Only append.

### 5. Memory-Only Writes
Only write to `memory_root` and `memory-state.json`. All project source files are read-only.

---

## Completion Report

```text
=== Project Memory Update — Completion Report ===

Current Phase: Phase 0 — Project Memory Update
Status: Completed
Mode: [incremental | full]

## Change Detection
Method: [git diff | filesystem timestamp | user-specified]
Git Hash (from): [previous hash]
Git Hash (to):   [current HEAD]
Files Changed: [N]

## Files Changed (source)
(list changed source files detected)

## Memory Documents Updated
(list memory files updated with reason)

## JSON Indexes Updated
(list which index files were modified)

## Embedding Manifest
(N chunks added, N chunks updated, N chunks removed)

## Vector Sync Plan
(generated: rag/vector-sync-plan.json | not applicable)

## Lessons Updated
(list which lesson files were appended, with lesson titles)

## Memory State
memory-state.json updated — [timestamp]

## Memory Coverage (estimated)
[X]% of project components indexed

## Recommended Next Skill
project-rag-search    — query memory before planning new features
planning-prompt-to-plan — start planning using fresh memory

Workflow Paused.
```
