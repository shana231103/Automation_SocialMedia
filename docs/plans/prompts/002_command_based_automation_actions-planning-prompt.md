<!-- File path: docs/plans/prompts/002_command_based_automation_actions-planning-prompt.md -->

# Prompt – Generate Implementation Plan from Idea

## Role

You are acting as a Senior Software Architect, Product Engineer, and Technical Planner inside the current IDE workspace.

You have full access to the project workspace.

---

## Source Idea

ở đây gọ hàm run_login cho chức năng login sau này tôi muốn làm chức năng post bài thì phải thêm function post bài, như vậy clas này sẽ phìn lên, tôi muốn mỗi tính năng là 1 class riêng biệt, chỉ cần register vào 1 class chính để sử dụng, gọi tính năng nào thì phân bổ class đó để chạy

---

## Objective

Generate a production-ready implementation planning document from the source idea.

Do not write source code.

Do not create the Technical Blueprint yet.

Save the generated planning document to:

```text
docs/plans/002_command_based_automation_actions.md
```

---

## Workspace Awareness

Before writing the plan:

1. Inspect the current workspace.
2. Detect:

   * primary language
   * frameworks
   * architecture style
   * folder structure
   * existing related modules
   * dependency management
   * testing framework
   * naming conventions
3. Reuse existing project conventions.
4. Prefer extending existing modules over creating duplicates.
5. If something is unclear, make a safe assumption and document it.

---

## Required Planning Document Structure

The planning document must include:

### 1. Overview

* Feature name
* Purpose
* Problem being solved
* Expected outcome

### 2. Current State Analysis

* Existing related files/modules
* Current behavior
* Technical gaps
* Constraints

### 3. Scope

* In scope
* Out of scope
* Assumptions

### 4. Proposed Solution

Describe the intended approach at a high level.

Do not write implementation code.

### 5. Architecture Impact

Explain:

* affected layers
* affected modules
* interfaces required
* data flow changes
* dependency boundaries

### 6. File Plan

List files likely to be:

* created
* modified
* reused

For each file, describe why it is needed.

### 7. Implementation Phases

Break the work into small steps.

Each phase should include:

* goal
* files involved
* expected result
* validation method

### 8. Testing Plan

Include:

* unit tests
* integration tests
* regression tests
* manual verification

### 9. Risks & Mitigation

List technical risks and mitigation.

### 10. Acceptance Criteria

Checklist for completion.

---

## Output Rules

The generated planning document must:

* be Markdown
* be saved under `docs/plans/`
* start with:

```html
<!-- File path: docs/plans/002_command_based_automation_actions.md -->
```

* not include source code
* not create blueprint
* not modify implementation files
