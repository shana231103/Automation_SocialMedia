---
name: environment-health
description: Read-only inspection of the local AI Coding environment. Detects OS, Git, Python, Node.js, Docker, SQLite, Tree-sitter, Qdrant, embedding providers, Ollama, QMD, Project Memory, and required AI Skills. Never modifies anything. Returns a detailed Environment Health Report with actionable recommendations.
---

# Skill: Environment Health

## Purpose

Perform a **complete, read-only inspection** of the local development environment and return a detailed **Environment Health Report**.

This Skill is the **diagnostic entry point** of the Environment Management Platform.

Run this Skill to:
- Understand the current state of the environment before starting any workflow.
- Diagnose issues reported by other Skills.
- Verify readiness after a machine setup or configuration change.

This Skill inspects only. It **never modifies, installs, or configures** anything.

To resolve detected issues, run **`environment-bootstrap`** instead.

---

## Role

You are acting as a **Principal AI Platform Engineer** and **Environment Diagnostics Specialist**.

You have full **read-only** access to:
- Local system tools and binaries
- Environment variables
- Project configuration files
- Git repository state
- Running processes and services
- Network endpoints (health checks only)

---

## Capability Boundary

**This Skill MUST NEVER:**
- Install any software or packages
- Modify any configuration file
- Create any file or directory
- Execute builds, tests, or Git operations
- Start or stop any service
- Perform planning, blueprint, or implementation work

**This Skill MAY:**
- Run read-only detection commands (`--version`, `which`, `where`, `curl`, `git status`, etc.)
- Read local files (config files, skill directories, memory files)
- Query local service health endpoints (HTTP GET only)
- Print findings and recommendations

---

## Workflow

### Step 1 — Detect Operating System

```bash
# macOS
uname -s && sw_vers -productVersion

# Linux
uname -s && cat /etc/os-release | grep PRETTY_NAME

# Windows (PowerShell)
[System.Environment]::OSVersion.VersionString
```

Detect and record:
- `os_type`: macOS | Linux | Windows
- `os_version`: version string
- `architecture`: x86_64 | arm64 | aarch64
- `preferred_package_manager`: brew | apt | dnf | yum | pacman | winget | choco | unknown

---

### Step 2 — Inspect Required Tools

---

#### 2.1 Git

```bash
git --version
git config --global user.name
git config --global user.email
git config --global core.editor
```

| Check | Pass Condition |
|-------|---------------|
| Installed | Binary found |
| Version | ≥ 2.30 |
| user.name | Non-empty |
| user.email | Non-empty |

Health levels:
- `PASS` — installed, version OK, name and email configured
- `WARNING` — installed, version OK, name or email missing
- `FAIL` — not installed

---

#### 2.2 Python

```bash
python --version   2>/dev/null || echo "not found"
python3 --version  2>/dev/null || echo "not found"
pip --version      2>/dev/null || echo "not found"
pip3 --version     2>/dev/null || echo "not found"
which python3 2>/dev/null || where python3 2>/dev/null
```

| Check | Pass Condition |
|-------|---------------|
| python or python3 | Binary found |
| Version | ≥ 3.9 |
| pip available | pip or pip3 found |

---

#### 2.3 Node.js

```bash
node --version  2>/dev/null || echo "not found"
npm --version   2>/dev/null || echo "not found"
npx --version   2>/dev/null || echo "not found"
which node      2>/dev/null || where node 2>/dev/null
```

| Check | Pass Condition |
|-------|---------------|
| node | Binary found |
| Version | ≥ 18.0 |
| npm | Available |
| npx | Available |

---

#### 2.4 SQLite

```bash
sqlite3 --version  2>/dev/null || echo "not found"
which sqlite3      2>/dev/null || where sqlite3 2>/dev/null
```

| Check | Pass Condition |
|-------|---------------|
| sqlite3 | Binary found |
| Version | ≥ 3.35 |

---

#### 2.5 Tree-sitter

```bash
tree-sitter --version  2>/dev/null || echo "not found"
tree-sitter dump-languages 2>/dev/null | head -20
```

| Check | Pass Condition |
|-------|---------------|
| CLI installed | Binary found |
| Version | ≥ 0.20 |
| Language parsers | At least one detected |

---

### Step 3 — Inspect Docker & Container Infrastructure

```bash
docker --version           2>/dev/null || echo "not found"
docker compose version     2>/dev/null || echo "not found"
docker info 2>/dev/null | grep -E "Server Version|Operating System|Containers:"
docker ps 2>/dev/null | head -5
```

| Check | Pass Condition |
|-------|---------------|
| Docker installed | Binary found |
| Docker version | Any |
| Docker Compose | Available |
| Daemon running | `docker info` succeeds |

Health levels:
- `PASS` — installed and daemon running
- `WARNING` — installed but daemon not running
- `INFO` — not installed (optional component)

---

### Step 4 — Inspect Qdrant Vector Database

```bash
# Check if container is running
docker ps --filter name=qdrant --format "{{.Names}} {{.Status}}" 2>/dev/null

# Health endpoint
curl -s --max-time 3 http://localhost:6333/healthz 2>/dev/null

# Version
curl -s --max-time 3 http://localhost:6333/ 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('version','unknown'))" 2>/dev/null

# Collections list
curl -s --max-time 3 http://localhost:6333/collections 2>/dev/null
```

Detect and record:
- Running: yes/no
- Version: string
- HTTP reachable: yes/no
- Collections: list
- Configured collection (from `memory.config.json`): exists / missing / unknown

| State | Description |
|-------|-------------|
| `PASS` | Running, reachable, configured collection exists |
| `WARNING` | Running, reachable, configured collection missing |
| `WARNING` | Not running but Docker is available |
| `INFO` | Not installed (optional) |

---

### Step 5 — Inspect Embedding Providers

Check all known providers:

**Ollama (local)**
```bash
ollama --version  2>/dev/null
curl -s --max-time 3 http://localhost:11434/api/tags 2>/dev/null
```

Extract: installed (yes/no), running (yes/no), models list, embedding models detected.

**OpenAI**
```bash
echo "${OPENAI_API_KEY:0:8}..."   # show only prefix for security
```

**Anthropic**
```bash
echo "${ANTHROPIC_API_KEY:0:8}..."
```

**Google Gemini**
```bash
echo "${GEMINI_API_KEY:0:8}..."
```

**Sentence Transformers / Local**
```bash
python3 -c "import sentence_transformers; print(sentence_transformers.__version__)" 2>/dev/null
python3 -c "from sentence_transformers import SentenceTransformer; print('available')" 2>/dev/null
```

**Nomic Embed**
```bash
python3 -c "import nomic; print(nomic.__version__)" 2>/dev/null
```

Display each provider:
- Status: `AVAILABLE` | `NOT CONFIGURED` | `NOT INSTALLED`
- Configuration: key set (prefix shown) | not set
- Models: list if applicable

---

### Step 6 — Inspect Ollama

```bash
ollama --version   2>/dev/null
curl -s --max-time 3 http://localhost:11434/ 2>/dev/null
curl -s --max-time 3 http://localhost:11434/api/tags 2>/dev/null | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    models = [m['name'] for m in d.get('models', [])]
    print('\n'.join(models))
except:
    print('error parsing response')
" 2>/dev/null
```

Record:
- Installed: yes/no
- Service running: yes/no
- Models available: list
- Embedding models: filter for `embed`, `nomic`, `bge`, `e5` in name

---

### Step 7 — Inspect QMD

```bash
qmd --version   2>/dev/null || echo "not found"
which qmd       2>/dev/null || where qmd 2>/dev/null
```

Check for index file:
```bash
ls .agents/memory/qmd.index 2>/dev/null || echo "index not found"
ls .agents/memory/*.qmd 2>/dev/null || echo "no qmd files"
```

Record:
- Installed: yes/no
- Version: string
- Index file: exists / missing

---

### Step 8 — Inspect Project Configuration

#### 8.1 Project Structure

```bash
ls -la .agents/              2>/dev/null
ls -la .agents/skills/       2>/dev/null
ls -la .agents/memory/       2>/dev/null
cat .agents/memory.config.json 2>/dev/null
```

#### 8.2 Memory Configuration Validation

If `.agents/memory.config.json` exists, validate:

| Field | Validation Rule |
|-------|----------------|
| `project_id` | Non-empty, no spaces |
| `memory_root` | Path resolvable |
| `vector_provider` | One of: `qdrant`, `chroma`, `none` |
| `vector_collection` | Non-empty if provider ≠ `none` |
| `embedding_model` | Any string or absent |

Report any missing or invalid fields as `WARNING`.

#### 8.3 Project Memory State

Check files in `memory_root`:

| File | Check |
|------|-------|
| `project-summary.md` | Exists → memory bootstrapped |
| `memory-state.json` | Exists → read `last_updated_at`, calculate staleness |
| `indexes/module-index.json` | Exists → indexes generated |
| `rag/keyword-index.md` | Exists → RAG ready |
| `embeddings/embedding-manifest.json` | Exists → embedding manifest ready |

Determine memory state:

| State | Condition |
|-------|-----------|
| `FRESH` | `project-summary.md` exists, updated ≤ 7 days ago |
| `STALE` | `project-summary.md` exists, updated > 7 days ago |
| `INCOMPLETE` | Some files missing, some present |
| `NOT GENERATED` | `project-summary.md` missing, config exists |
| `NOT INITIALIZED` | `memory.config.json` missing |

---

### Step 9 — Inspect Required AI Skills

Search for Skills in known locations (in order):
1. `.agents/skills/`
2. `~/.gemini/config/skills/`
3. Any path found in IDE skill configuration

For each required Skill, verify:
- Directory exists: `[skill-name]/`
- `SKILL.md` file present
- YAML frontmatter `name` field matches expected name

Required Skills:

| Skill | Required |
|-------|---------|
| `software-development-workflow` | ✅ |
| `idea-to-planning-prompt` | ✅ |
| `planning-prompt-to-plan` | ✅ |
| `plan-to-blueprint` | ✅ |
| `blueprint-to-implementation` | ✅ |
| `implementation-to-release` | ✅ |
| `project-memory-bootstrap` | ✅ |
| `project-memory-update` | ✅ |
| `project-rag-search` | ✅ |
| `environment-health` | ✅ |
| `environment-bootstrap` | ✅ |

---

### Step 10 — Inspect Git Repository State

```bash
git status --short      2>/dev/null
git branch --show-current 2>/dev/null
git log --oneline -5   2>/dev/null
git remote -v          2>/dev/null
```

Report:
- On branch: name
- Uncommitted changes: count of modified files
- Unpushed commits: count
- Remote configured: yes/no

---

### Step 11 — Generate Environment Health Report

```
╔══════════════════════════════════════════════════════════╗
║              Environment Health Report                   ║
║              Generated: [ISO8601 timestamp]              ║
╚══════════════════════════════════════════════════════════╝

Operating System
  Type:             [macOS | Linux | Windows]
  Version:          [x.x.x]
  Architecture:     [x86_64 | arm64]
  Package Manager:  [brew | apt | winget | unknown]

══════════════════════════════════════════════════════════
REQUIRED TOOLS
══════════════════════════════════════════════════════════

Git                    [✅ PASS | ⚠ WARNING | ❌ FAIL]
  Version:   [x.y.z]
  Location:  [/usr/bin/git]
  user.name: [configured ✅ | ⚠ not set]
  user.email:[configured ✅ | ⚠ not set]

Python                 [✅ PASS | ❌ FAIL]
  Version:   [3.x.x]
  Binary:    [python3 | python]
  Location:  [/usr/bin/python3]
  pip:       [✅ available | ❌ missing]

Node.js                [✅ PASS | ❌ FAIL]
  Version:   [vXX.x.x]
  Location:  [/usr/local/bin/node]
  npm:       [✅ vX.x.x | ❌ missing]
  npx:       [✅ available | ❌ missing]

SQLite                 [✅ PASS | ❌ FAIL]
  Version:   [3.x.x]
  Location:  [/usr/bin/sqlite3]

Tree-sitter            [✅ PASS | ⚠ WARNING | ❌ FAIL]
  Version:   [x.x.x]
  Location:  [/usr/local/bin/tree-sitter]
  Languages: [N parsers available | ⚠ none detected]

══════════════════════════════════════════════════════════
OPTIONAL INFRASTRUCTURE
══════════════════════════════════════════════════════════

Docker                 [✅ RUNNING | ⚠ STOPPED | ℹ NOT INSTALLED]
  Docker:          [vX.X.X | not found]
  Compose:         [vX.X.X | not found]
  Daemon:          [running | stopped | N/A]

Qdrant                 [✅ PASS | ⚠ WARNING | ℹ NOT RUNNING]
  Endpoint:        [http://localhost:6333]
  Status:          [reachable | unreachable]
  Version:         [X.X.X | unknown]
  Collections:     [N found | none]
  Target collection: [exists ✅ | missing ⚠ | not configured]

Embedding Providers    [✅ AVAILABLE | ⚠ NONE DETECTED]
  Ollama:          [✅ running (N models) | ⚠ stopped | ℹ not installed]
  OpenAI:          [✅ key configured | ℹ not set]
  Anthropic:       [✅ key configured | ℹ not set]
  Gemini:          [✅ key configured | ℹ not set]
  Sentence-BERT:   [✅ installed vX.X | ℹ not installed]
  Nomic:           [✅ installed vX.X | ℹ not installed]

Ollama                 [✅ RUNNING | ⚠ STOPPED | ℹ NOT INSTALLED]
  Version:         [X.X.X | not found]
  Service:         [running | stopped | N/A]
  Models:          [N available]
  Embed models:    [list or "none detected"]

QMD                    [✅ INSTALLED | ℹ NOT INSTALLED]
  Version:         [X.X.X | not found]
  Index:           [exists ✅ | ⚠ missing]

══════════════════════════════════════════════════════════
PROJECT CONFIGURATION
══════════════════════════════════════════════════════════

.agents/ directory     [✅ exists | ❌ missing]
.agents/skills/        [✅ exists | ❌ missing]

Memory Configuration   [✅ VALID | ⚠ INVALID | ❌ MISSING]
  File:          .agents/memory.config.json
  project_id:    [value ✅ | ❌ missing]
  memory_root:   [value ✅ | ❌ missing]
  vector_provider: [qdrant | chroma | none | ❌ missing]
  vector_collection: [value ✅ | ⚠ missing | N/A]

Project Memory State   [✅ FRESH | ⚠ STALE | ⚠ INCOMPLETE | ❌ NOT GENERATED | ❌ NOT INITIALIZED]
  project-summary.md:    [✅ exists | ❌ missing]
  memory-state.json:     [✅ exists | ❌ missing]
  Last Updated:          [ISO8601 | N/A]
  Staleness:             [N days | N/A]
  Indexes:               [✅ generated | ⚠ missing]
  RAG:                   [✅ ready | ⚠ missing]
  Embeddings:            [✅ manifest ready | ⚠ missing]

══════════════════════════════════════════════════════════
AI CODING SKILLS
══════════════════════════════════════════════════════════

  software-development-workflow    [✅ FOUND | ❌ MISSING]
  idea-to-planning-prompt          [✅ FOUND | ❌ MISSING]
  planning-prompt-to-plan          [✅ FOUND | ❌ MISSING]
  plan-to-blueprint                [✅ FOUND | ❌ MISSING]
  blueprint-to-implementation      [✅ FOUND | ❌ MISSING]
  implementation-to-release        [✅ FOUND | ❌ MISSING]
  project-memory-bootstrap         [✅ FOUND | ❌ MISSING]
  project-memory-update            [✅ FOUND | ❌ MISSING]
  project-rag-search               [✅ FOUND | ❌ MISSING]
  environment-health               [✅ FOUND | ❌ MISSING]
  environment-bootstrap            [✅ FOUND | ❌ MISSING]

  Skills Found: [N / 11]
  Skills Location: [path]

══════════════════════════════════════════════════════════
GIT REPOSITORY STATE
══════════════════════════════════════════════════════════

  Branch:             [branch-name | not a git repo]
  Uncommitted Files:  [N files | clean]
  Remote:             [origin → url | not configured]
  Recent Commits:     [N | none]

══════════════════════════════════════════════════════════
OVERALL STATUS
══════════════════════════════════════════════════════════

  [✅ HEALTHY | ⚠ WARNING | ❌ CRITICAL]

══════════════════════════════════════════════════════════
ACTION PLAN
══════════════════════════════════════════════════════════

(Printed only when issues exist. Priority order.)

❌ CRITICAL — Must resolve before starting workflow:
  [component]: [specific action]

⚠ WARNING — Recommended to resolve:
  [component]: [specific action]

ℹ INFO — Optional improvements:
  [component]: [specific action]
```

---

### Step 12 — Overall Status & Recommendation

**Status Determination:**

| Status | Condition |
|--------|-----------|
| ✅ `HEALTHY` | All required tools pass. Memory fresh. All skills found. |
| ⚠ `WARNING` | Required tools pass. Optional components or memory stale. |
| ❌ `CRITICAL` | One or more required tools fail, OR skills missing. |

**Recommendations:**

- If `CRITICAL` → List each critical item. Recommend `environment-bootstrap`.
- If `WARNING` + memory stale → Recommend `project-memory-update`.
- If `WARNING` + optional components missing → List optional improvements. Proceed if user wants.
- If `HEALTHY` + memory fresh → Recommend `software-development-workflow`.
- If `HEALTHY` + memory not initialized → Recommend `project-memory-bootstrap`.

---

## Parameters

```yaml
workspace: auto
# Current project directory. Default: current working directory.

check_optional: true
# Include optional component inspection (Docker, Qdrant, Ollama, QMD)

check_git_state: true
# Include git status inspection

check_network: true
# Include health endpoint checks (Qdrant, Ollama HTTP)

network_timeout_seconds: 3
# Timeout for each HTTP health check

report_format: detailed
# Options: detailed | summary
```

---

## IDE Skill Hardening & Boundary Rules

### 1. Single Responsibility
Inspect and report on the environment. Once the Health Report is printed, STOP.

### 2. Strictly Read-Only
Never write, install, configure, or modify anything. Any write operation is a violation of this Skill's boundary.

### 3. Never Execute Next Phase
Do NOT invoke `environment-bootstrap` or any other Skill. Only recommend.

### 4. Safe Credential Handling
When displaying API keys, show only the first 8 characters followed by `...`. Never print full keys.

### 5. Non-blocking
If any inspection command fails or times out, record the failure and continue. Never crash on a single check failure.

---

## Completion Contract

```text
=== Environment Health — Completion Report ===

Current Phase: Environment Inspection
Status: Completed
Mode: Read-Only

Overall Status: [✅ HEALTHY | ⚠ WARNING | ❌ CRITICAL]

Required Tools:   [N / 5 passing]
Optional Tools:   [N / 5 available]
Skills Found:     [N / 11]
Memory State:     [FRESH | STALE | NOT GENERATED | NOT INITIALIZED]

Recommended Next Skill:
  [environment-bootstrap | project-memory-bootstrap | project-memory-update | software-development-workflow]

Workflow Paused.
```
