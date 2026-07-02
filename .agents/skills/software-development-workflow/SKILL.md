---
name: software-development-workflow
description: Pure Workflow Orchestrator for the AI Coding Platform. Inspects environment health, project memory state, and SDLC artifact state to determine the current phase and recommend the single correct next Skill. Read-only. Never modifies anything. Never executes engineering work.
---

# Skill: Software Development Workflow Orchestrator

## Purpose

This Skill is the **central coordinator** of the entire AI Coding Platform.

It acts as a **Project Manager**, not a Software Engineer.

Its only responsibility is to:
1. Inspect the current state of the environment, memory, and workflow artifacts.
2. Determine exactly where the project is in the pipeline.
3. Recommend the single correct next Skill to run.
4. Explain why.
5. Stop immediately.

It does NOT perform any engineering work.

---

## AI Coding Platform Layers

This Skill coordinates all five layers of the platform:

```
Layer 1 — Environment
  environment-health
  environment-bootstrap

Layer 2 — Knowledge
  project-memory-bootstrap
  project-memory-update
  project-rag-search

Layer 3 — Planning
  idea-to-planning-prompt
  planning-prompt-to-plan
  plan-to-blueprint

Layer 4 — Engineering
  blueprint-to-implementation

Layer 5 — Release
  implementation-to-release
```

---

## Capability Boundary

**This Skill owns ZERO project artifacts.**

**This Skill MUST NEVER:**
- Modify source code
- Generate implementation code
- Create planning documents
- Create technical blueprints
- Update documentation
- Update Project Memory
- Update Qdrant or vector databases
- Update SQLite or JSON indexes
- Update QMD indexes
- Perform Git commits or pushes
- Execute builds or tests
- Invoke another Skill automatically
- Simulate the behavior of another Skill

**This Skill MAY ONLY:**
- Inspect files and directories (read-only)
- Analyze workflow state
- Recommend the next Skill
- Explain the recommendation

---

## Execution Mode

**READ ONLY — Absolute.**

This Skill never writes to, creates, modifies, or deletes any file or directory under any circumstance.

---

## User Input Policy

Everything written after invoking this Skill is treated as **PROJECT CONTEXT**.

It is **NEVER** an implementation request.

**Example:**
```
/software-development-workflow
Implement local cache for cloud-only files.
```

The phrase `"Implement local cache..."` is project context only.

It must NEVER trigger implementation, planning, or any engineering work.

The Skill must only determine the current workflow phase and recommend the next Skill.

---

## Decision Tree

Execute these checks in strict order. **Stop at the first check that returns a recommendation.**

```
Step 1 — Environment Health Check
        ↓
Step 2 — Project Memory Check
        ↓
Step 3 — Workflow State Detection
        ↓
Step 4 — Generate Recommendation
        ↓
STOP
```

Never skip a step. Never continue past a recommendation.

---

## Step 1 — Environment Health Check

### 1.1 — Locate environment-health Skill

Check that `environment-health` exists in known skill locations:
- `.agents/skills/environment-health/SKILL.md`
- `~/.gemini/config/skills/environment-health/SKILL.md`
- Global shared skills directory

If `environment-health` is missing:
```
⚠ environment-health Skill not found.

Cannot verify environment health without this Skill.

Recommended Next Skill:
Manually verify: Git, Python, Node.js, SQLite, Tree-sitter are installed.
Then install the environment-health Skill and re-run this Skill.

Workflow Paused.
```
→ STOP.

### 1.2 — Inspect Environment State (read-only proxies)

Perform lightweight environment checks sufficient for orchestration decisions:

```bash
git --version              2>/dev/null || echo "MISSING"
python3 --version          2>/dev/null || echo "MISSING"
node --version             2>/dev/null || echo "MISSING"
sqlite3 --version          2>/dev/null || echo "MISSING"
tree-sitter --version      2>/dev/null || echo "MISSING"
```

Also check:
- `docker info 2>/dev/null` — daemon running?
- `curl -s --max-time 2 http://localhost:6333/healthz` — Qdrant reachable?
- `curl -s --max-time 2 http://localhost:11434/` — Ollama reachable?

Determine **Environment Status**:

| Status | Condition |
|--------|-----------|
| `HEALTHY` | All required tools found (Git, Python, Node, SQLite, Tree-sitter) |
| `WARNING` | Required tools found. Optional services (Docker, Qdrant) missing |
| `CRITICAL` | One or more required tools missing |

**If `CRITICAL`:**
```
❌ Environment Status: CRITICAL

One or more required tools are missing.
The AI Coding workflow cannot begin until the environment is ready.

Missing Tools:
  [list each missing required tool]

Recommended Next Skill:
environment-bootstrap

Reason:
environment-bootstrap will install missing tools and prepare the machine
for the AI Coding workflow.

Run environment-health first for a detailed diagnosis.

Workflow Paused.
```
→ STOP.

**If `WARNING`:**

Record the warning and continue to Step 2. Do NOT stop for optional component warnings.

---

## Step 2 — Project Memory Check

### 2.1 — Check Memory Configuration

Look for `.agents/memory.config.json`.

**If MISSING:**
```
❌ Memory Status: NOT INITIALIZED

Project Memory has not been configured for this project.
All downstream Skills require Project Memory to operate efficiently.

Recommended Next Skill:
project-memory-bootstrap

Reason:
project-memory-bootstrap will initialize the memory configuration and
generate the complete Project Memory knowledge base.

Run environment-bootstrap first if it has not been run yet.

Workflow Paused.
```
→ STOP.

**If exists:** Read and validate:
- `project_id` — non-empty
- `memory_root` — resolvable path
- `vector_provider` — valid value

If invalid fields:
```
⚠ Memory Status: CONFIGURATION INVALID

.agents/memory.config.json has invalid or missing fields:
  [list field: issue]

Recommended Next Skill:
environment-bootstrap

Reason:
environment-bootstrap can repair the memory configuration.

Workflow Paused.
```
→ STOP.

### 2.2 — Check Memory Existence

Check `<memory_root>/project-summary.md`.

**If MISSING:**
```
❌ Memory Status: NOT GENERATED

Memory configuration exists but Project Memory has not been generated.

Recommended Next Skill:
project-memory-bootstrap

Reason:
project-memory-bootstrap performs a full analysis of the project and
generates the complete memory knowledge base required by all Planning
and Implementation Skills.

Workflow Paused.
```
→ STOP.

### 2.3 — Check Memory Freshness

Read `<memory_root>/memory-state.json`.

Calculate staleness from `last_updated_at`.

| Staleness | Memory Status |
|-----------|--------------|
| ≤ 7 days | `FRESH` |
| 8 – 30 days | `STALE` |
| > 30 days | `VERY STALE` |
| `memory-state.json` missing | `UNKNOWN` |

**If `STALE` or `VERY STALE`:**
```
⚠ Memory Status: STALE ([N] days old)

Project Memory was last updated [N] days ago and may not reflect
recent code changes.

Recommended Next Skill:
project-memory-update

Reason:
Fresh memory is required before planning or implementation begins.
project-memory-update uses git diff to surgically update only
affected memory documents.

Workflow Paused.
```
→ STOP.

**If `FRESH` or `UNKNOWN`:** Continue to Step 3.

---

## Step 3 — Workflow State Detection

Inspect workspace artifacts to determine the current SDLC phase.

**Inspect in this order:**

### 3.1 — Check for active Planning Prompt

Look for files matching:
- `docs/plans/prompts/*.md` — any planning prompt file

**If NO planning prompt exists:**

→ Recommend `idea-to-planning-prompt`. (See output template below.)

---

### 3.2 — Check for Implementation Plan

Given a detected planning prompt (e.g., `docs/plans/prompts/NNN-*-planning-prompt.md`):

Look for the corresponding plan:
- `docs/plans/NNN-*.md` (same phase prefix, no `-planning-prompt` suffix)

**If planning prompt EXISTS but implementation plan is MISSING:**

→ Recommend `planning-prompt-to-plan`.

---

### 3.3 — Check for Technical Blueprint

Given a detected implementation plan:

Look for the corresponding blueprint:
- `docs/plans/designs/NNN-*-design.md`

**If implementation plan EXISTS but blueprint is MISSING:**

→ Recommend `plan-to-blueprint`.

---

### 3.4 — Check for Implementation Completion

Given a detected blueprint:

Inspect git status to estimate implementation progress:
```bash
git status --short 2>/dev/null
git log --oneline -10 2>/dev/null
```

Heuristic signals for "implementation in progress or complete":
- Modified source files present in `git status`
- Recent commits referencing the phase name
- Blueprint file is older than modified source files

**If blueprint EXISTS and implementation appears INCOMPLETE:**

→ Recommend `blueprint-to-implementation`.

---

### 3.5 — Check Post-Implementation Memory Update

If implementation appears complete (recent commits exist):

Check `memory-state.json` `last_updated_at` against the most recent Git commit timestamp.

```bash
git log -1 --format="%ai" 2>/dev/null
```

**If implementation commits are newer than last memory update:**

```
⚠ Implementation was completed after the last memory update.

Project Memory is out of sync with the current codebase.

Recommended Next Skill:
project-memory-update

Reason:
Memory must be synchronized before release to ensure future planning
sessions have accurate context.

Workflow Paused.
```
→ STOP.

---

### 3.6 — Check for Pending Release

If memory is updated after implementation:

Check git status for uncommitted changes or unpushed commits:
```bash
git status --short 2>/dev/null
git log --branches --not --remotes --oneline 2>/dev/null
```

**If uncommitted changes or unpushed commits exist:**

→ Recommend `implementation-to-release`.

---

### 3.7 — Check Post-Release Memory Update

If no uncommitted changes and no unpushed commits:

Check if a release occurred (git tag or recent merge commit) after the last memory update.

**If release occurred after last memory update:**

```
⚠ A release was completed after the last memory update.

Recommended Next Skill:
project-memory-update

Reason:
Memory must be refreshed after release to reflect the released implementation
and capture release notes in the lessons layer.

Workflow Paused.
```
→ STOP.

---

### 3.8 — Workflow Complete

If all checks pass with no pending work:

```
✅ Workflow Complete

All phases appear to be complete for the current feature or release cycle.

Environment:    HEALTHY
Memory:         FRESH
Planning:       Complete
Blueprint:      Complete
Implementation: Complete
Memory Sync:    Complete
Release:        Complete

To start a new feature cycle:

Recommended Next Skill:
idea-to-planning-prompt

Workflow Paused.
```
→ STOP.

---

## Step 4 — Output Format

For every recommendation, use exactly this format:

```
╔══════════════════════════════════════════════════════════╗
║         Software Development Workflow Orchestrator       ║
║         [ISO8601 timestamp]                              ║
╚══════════════════════════════════════════════════════════╝

Workflow Status

──────────────────────────────────────────────────────────
Environment Status
──────────────────────────────────────────────────────────
  Status:     [✅ HEALTHY | ⚠ WARNING | ❌ CRITICAL]
  Git:        [✅ vX.X | ❌ MISSING]
  Python:     [✅ 3.X | ❌ MISSING]
  Node.js:    [✅ vXX | ❌ MISSING]
  SQLite:     [✅ 3.X | ❌ MISSING]
  Tree-sitter:[✅ vX.X | ❌ MISSING]
  Docker:     [✅ running | ⚠ stopped | ℹ not installed]
  Qdrant:     [✅ running | ℹ not running]

──────────────────────────────────────────────────────────
Memory Status
──────────────────────────────────────────────────────────
  Status:       [✅ FRESH | ⚠ STALE | ❌ NOT GENERATED | ❌ NOT INITIALIZED]
  Config:       [✅ valid | ⚠ invalid | ❌ missing]
  Last Updated: [ISO8601 | N/A]
  Staleness:    [N days | N/A]

──────────────────────────────────────────────────────────
Workflow State
──────────────────────────────────────────────────────────
  Current Phase:  [Phase name]
  Planning Prompt:[✅ exists: path | ❌ missing]
  Plan:           [✅ exists: path | ❌ missing]
  Blueprint:      [✅ exists: path | ❌ missing]
  Implementation: [✅ detected | ⚠ in progress | ❌ pending]
  Memory Sync:    [✅ up to date | ⚠ outdated]
  Release:        [✅ released | ⚠ pending | ❌ not started]

──────────────────────────────────────────────────────────
Completed Phases
──────────────────────────────────────────────────────────
  [✅ Phase 1 — Idea to Planning Prompt]
  [✅ Phase 2 — Planning Prompt to Plan]
  [⏳ Phase 3 — Plan to Blueprint  ← CURRENT]
  [⬜ Phase 4 — Blueprint to Implementation]
  [⬜ Phase 5 — Implementation to Release]

──────────────────────────────────────────────────────────
Recommended Next Skill
──────────────────────────────────────────────────────────
  Skill:    [skill-name]

  Reason:
  [Clear explanation of why this Skill is recommended based on
   the inspection findings above. Be specific about what was
   detected and what the Skill will do.]

  Required Input:
  [What the user or the Skill needs as input]

  Expected Output:
  [What artifact the Skill will produce]

  Next Checkpoint:
  [What to inspect after this Skill completes, to determine the
   next recommended Skill]

══════════════════════════════════════════════════════════
Workflow Paused.
Waiting for user to invoke: [skill-name]
══════════════════════════════════════════════════════════
```

---

## Resume Support

When invoked again after a phase completes, re-run the full Decision Tree from Step 1.

Never restart the workflow from Phase 1 if later phases are already complete.

The Decision Tree naturally handles resume by detecting which artifacts already exist and skipping completed phases.

---

## Ownership

- **Owned artifacts**: None.
- **Generated artifacts**: None.
- **Modified artifacts**: None.

The only output of this Skill is the orchestration report printed to the chat interface.

---

## Parameters

```yaml
workspace: auto
# Current project directory

check_environment: true
# Include environment health check in Step 1

check_memory: true
# Include memory state check in Step 2

check_workflow: true
# Include SDLC artifact state detection in Step 3

network_timeout_seconds: 2
# Timeout for optional service health checks (Qdrant, Ollama)

phase_hint: auto
# Optional: user-specified phase name to narrow detection
# If auto, detect automatically from workspace artifacts
```

---

## IDE Skill Hardening & Boundary Rules

### 1. Single Responsibility
This Skill has exactly ONE responsibility: determine the current workflow state and recommend the next Skill. Once the report is printed, STOP.

### 2. Absolute Read-Only
Any write operation — to any file, in any directory — is a direct violation of this Skill's purpose. There are no exceptions.

### 3. Never Execute Next Phase
This Skill must NOT automatically invoke any other Skill, generate any artifact, or simulate any other Skill's behavior.

### 4. User Input Is Context
Everything written after invocation is project context used to identify the current feature being developed. It is never a command to generate code, plans, or blueprints.

### 5. Deterministic
Given the same workspace state, this Skill must always produce the same recommendation. No randomness, no guessing.

### 6. Resume by Default
Never restart a completed phase. Always detect and resume from the furthest completed state.

---

## Completion Contract

```text
╔══════════════════════════════════════════════════════════╗
║         Software Development Workflow Orchestrator       ║
╚══════════════════════════════════════════════════════════╝

Phase:   Workflow Orchestration
Status:  Completed

[Full status report as per Output Format above]

Recommended Next Skill: [skill-name]

Workflow Paused.
Waiting for user to invoke the recommended Skill.
```
