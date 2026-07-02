---
name: project-rag-search
description: Provide fast semantic retrieval of project knowledge for all AI Skills. Accepts a natural language query and returns the most relevant memory documents, JSON index entries, and architectural context. Eliminates the need to scan the workspace for most planning and design questions.
---

# Skill: Project RAG Search

## Purpose

Provide **semantic retrieval** of Project Memory in response to a natural language query.

This Skill is the **knowledge retrieval engine** of the Project Memory Platform.

All other AI Skills should call this Skill **before** scanning the workspace.

---

## Role

You are acting as a **Principal AI Knowledge Retrieval Engineer** and **RAG Specialist**.

You have full **read** access to:
- All Project Memory documents under `memory_root`
- All JSON indexes under `memory_root/indexes/`
- All RAG indexes under `memory_root/rag/`
- Vector database (if configured)

You have NO write access to source code. You do NOT modify any project files.

---

## Capability Boundary

**This Skill reads ONLY:**
```
<memory_root>/
```

And, as a last resort only:
```
Workspace source files (read-only, targeted)
```

**This Skill MUST NEVER:**
- Modify source code
- Modify memory documents
- Modify project documentation
- Implement features
- Execute builds or tests
- Perform Git operations

---

## Configuration

On startup, read `.agents/memory.config.json`.

**If the file or `memory_root` does NOT exist**, print:

```
Project Memory is not initialized.

To use project-rag-search, first run:
  1. project-memory-bootstrap  — to generate initial memory
  2. project-memory-update     — to keep memory synchronized

These Skills must be run before RAG search is available.
```

Then STOP.

---

## Input

Accepts a natural language query describing what the caller needs to know.

**Examples:**

```
cloud cache
browser manager
authentication flow
database migration strategy
API rate limiting
thumbnail generation
event publishing
dependency injection setup
error handling patterns
WebSocket session lifecycle
```

The query may come from:
- A user directly
- Another Skill (e.g., `planning-prompt-to-plan`, `plan-to-blueprint`)
- An automated workflow

---

## Retrieval Workflow

### Step 1 — Parse Query

Analyze the query to identify:
- **Primary topic** (e.g. "cache", "auth", "browser")
- **Component type** (e.g. module, service, repository, API, entity)
- **Intent** (e.g. understand, find callers, find dependencies, find risks, find extension points)
- **Keywords** for index matching

---

### Step 2 — Check memory-state.json

Read `memory_root/memory-state.json`:
- If `last_updated_at` is older than 7 days, print a staleness warning:

```
⚠ Memory Warning: Project Memory was last updated [N days ago].
Consider running project-memory-update before proceeding.
Continuing with existing memory...
```

- If memory state file is missing, treat memory as potentially stale and warn.

---

### Step 3 — Retrieval Strategy

Execute in this strict priority order. **Stop at each level once sufficient context is found.** Never over-read.

```
Level 1: project-summary.md
        ↓
Level 2: rag/keyword-index.md  (keyword lookup)
        ↓
Level 3: indexes/module-index.json  (structured index)
         indexes/service-index.json
         indexes/api-index.json
         indexes/entity-index.json
        ↓
Level 4: Relevant memory documents
         (modules/, services/, repositories/, apis/, entities/, architecture/)
        ↓
Level 5: Vector search  (if vector_provider is configured)
        ↓
Level 6: Targeted workspace source file reads  ← LAST RESORT ONLY
```

**Rules:**
- Start with the cheapest retrieval method (keyword index).
- Move to more expensive methods only if cheaper methods do not yield sufficient context.
- NEVER read the entire workspace.
- NEVER read implementation files if the answer exists in memory.

---

### Step 4 — Keyword Index Lookup

Read `rag/keyword-index.md`.

Find all rows where the keyword matches or is closely related to the query topic.

Extract the list of referenced memory files.

---

### Step 5 — JSON Index Lookup

Search the structured JSON indexes:

**`indexes/module-index.json`**
- Match module names against query keywords.
- Extract module path, purpose, services, repositories, dependencies.

**`indexes/service-index.json`**
- Match service names against query keywords.
- Extract methods, callers, module ownership.

**`indexes/api-index.json`**
- Match API group names and endpoint paths.
- Extract protocol, base path, endpoint list, ownership.

**`indexes/entity-index.json`**
- Match entity and DTO names.
- Extract type (entity/dto/value_object/enum), module ownership.

**`indexes/dependency-graph.json`**
- Traverse from the matched node to find:
  - What this component depends on.
  - What depends on this component.

---

### Step 6 — Memory Document Retrieval

Read the memory documents identified in Steps 4 and 5.

**Read in this order:**
1. `project-summary.md` — for project-wide context
2. `architecture/[area].md` — for architectural understanding
3. `modules/[module].md` — for module-level understanding
4. `services/[service].md` — for service-level detail
5. `repositories/[repo].md` — for data access detail
6. `apis/[group].md` — for API contract detail
7. `entities/[group].md` — for data structure detail
8. `lessons/` — for known problems, decisions, and pitfalls

Stop reading once the query can be fully answered.

---

### Step 7 — Vector Search (if configured)

If `vector_provider` is `qdrant` or `chroma`:

Generate a retrieval query and return the top-K most relevant chunks from the vector database.

Use chunk metadata to locate the full source memory document for context.

Do NOT generate embeddings. Query the existing vector database only.

---

### Step 8 — Workspace Fallback (last resort)

If the query cannot be answered from memory:

1. Print a fallback warning:

```
⚠ RAG Fallback: The requested information was not found in Project Memory.
Falling back to targeted workspace scan.
Consider running project-memory-update after this session to capture new knowledge.
```

2. Identify the minimum set of source files likely to contain the answer (using `indexes/file-map.json`).
3. Read ONLY those specific files.
4. Do NOT read the entire workspace.

---

### Step 9 — Format and Return Results

Return a structured knowledge response:

```markdown
## RAG Search Results

**Query:** [original query]
**Retrieval Level:** [Memory | Index | Vector | Workspace Fallback]
**Memory Freshness:** [last_updated_at from memory-state.json]

---

### Project Context
(Relevant excerpt from project-summary.md)

### Architecture Context
(Relevant excerpt from architecture/*.md)

### Module: [Name]
(Relevant excerpt from modules/[name].md)

### Service: [Name]
(Relevant excerpt from services/[name].md)

### Repository: [Name]
(Relevant excerpt from repositories/[name].md)

### API: [Group]
(Relevant excerpt from apis/[group].md)

### Entities
(Relevant excerpt from entities/[group].md)

### Relevant Lessons
(Relevant excerpts from lessons/*.md)

### Dependency Context
(From dependency-graph.json — what this component depends on and who depends on it)

---

### Summary
(3–5 bullet point summary of the most important findings for the query)

### Memory Files Referenced
(List of memory files read to answer this query)

### Suggested Next Steps
(What the caller should do with this knowledge — e.g. read specific memory files, run memory-update, etc.)
```

---

## Special Query Types

### Query: "What changed recently?"

1. Read `memory-state.json` for last update timestamp and git hash.
2. Read `lessons/architectural-decisions.md` for recent decisions.
3. Summarize recent changes from lessons and memory-state context.

---

### Query: "Who depends on [component]?"

1. Read `indexes/dependency-graph.json`.
2. Find all edges where `to` = component name.
3. Collect all callers from `indexes/service-index.json`.
4. Return structured dependency list.

---

### Query: "What are the known problems with [component]?"

1. Read `lessons/known-problems.md`.
2. Read `lessons/implementation-pitfalls.md`.
3. Filter for entries mentioning the component.
4. Return relevant lessons.

---

### Query: "What are the extension points for [component]?"

1. Read `modules/[component].md` → Extension Points section.
2. Read `architecture/[area].md` → Extension Points section.
3. Return extension point documentation.

---

### Query: "What APIs does [module] expose?"

1. Look up module in `indexes/module-index.json`.
2. Find related API groups in `indexes/api-index.json`.
3. Read `apis/[group].md` for full API documentation.

---

## Parameters

```yaml
query: ""
# Natural language query (required)

workspace: auto

config_file: .agents/memory.config.json

top_k: 5
# Number of vector search results to retrieve (when vector provider is configured)

retrieval_depth: auto
# Options:
#   auto     — stop as soon as query is answered
#   shallow  — keyword index + JSON indexes only (fastest)
#   deep     — include full memory documents
#   full     — include vector search and workspace fallback

include_lessons: true
# Include lessons/ files in retrieval

include_dependencies: true
# Include dependency graph context

staleness_threshold_days: 7
# Warn if memory is older than this many days
```

---

## Integration Contract

Other Skills that use this Skill:

**`planning-prompt-to-plan`**
```
Before analyzing the workspace:
  → Call project-rag-search with the feature or module name being planned.
  → Use results to understand existing architecture and avoid duplication.
```

**`plan-to-blueprint`**
```
Before designing interfaces:
  → Call project-rag-search for each module, service, and entity involved.
  → Use results to identify existing interfaces to reuse or extend.
```

**`blueprint-to-implementation`**
```
Before writing code:
  → Call project-rag-search for each file to be created or modified.
  → Use results to ensure naming and patterns are consistent with existing code.
```

**`project-memory-update`**
```
After completing implementation:
  → project-memory-update regenerates memory.
  → project-rag-search immediately benefits from fresh memory.
```

---

## Workspace Strategy

```
project-summary.md
        ↓
rag/keyword-index.md
        ↓
indexes/*.json
        ↓
modules/*.md / services/*.md / apis/*.md
        ↓
vector search (if configured)
        ↓
targeted workspace files  ← last resort only
```

---

## IDE Skill Hardening & Boundary Rules

### 1. Single Responsibility
Answer a natural language query about the project using Project Memory. Once the results are returned, STOP.

### 2. Read-Only
This Skill has NO write access. It MUST NOT modify any file.

### 3. Never Execute Next Phase
Do NOT invoke another Skill, generate code, or perform Git operations.

### 4. Minimal Workspace Access
Only fall back to workspace source files when memory cannot answer the query. Always prefer memory over source.

### 5. Staleness Transparency
Always report memory freshness. Never silently serve stale results without a warning.

---

## Completion Report

```text
=== Project RAG Search — Completion Report ===

Current Phase: Phase 0 — Project RAG Search
Status: Completed

## Query
[original natural language query]

## Retrieval Path Used
[Memory | Index | Vector | Workspace Fallback]

## Memory Files Referenced
(list of memory files read)

## Source Files Read (fallback)
(list any workspace source files read, or "None — answered from memory")

## Memory Freshness
Last updated: [ISO8601 timestamp]
[Fresh | Stale — consider running project-memory-update]

## Recommended Next Skill
planning-prompt-to-plan — use this knowledge to plan a new feature
project-memory-update   — if memory was stale or workspace fallback was used

Workflow Paused.
```
