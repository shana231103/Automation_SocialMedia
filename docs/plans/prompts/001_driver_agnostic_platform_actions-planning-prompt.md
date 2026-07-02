<!-- File path: docs/plans/prompts/001_driver_agnostic_platform_actions-planning-prompt.md -->

# Prompt – Generate Implementation Plan from Idea

## Role

You are acting as a Senior Software Architect, Product Engineer, and Technical Planner inside the current IDE workspace.

You have full access to the project workspace.

---

## Source Idea

Các lớp (classes) trong module `backend/app/infrastructure/automation` chưa thực sự hiệu quả. Mỗi lần cần thêm một driver điều khiển trình duyệt khác (như Playwright, DrissionPage, hay Puppeteer) thì nhà phát triển lại phải viết lại toàn bộ kịch bản tương tác đăng nhập (các actions) trong `platforms_drissionpage` và `platform_playwright`. 

Mục tiêu là tái cấu trúc (refactor) lại phần code này sao cho khi thêm một service điều khiển mới (ví dụ: `playwright_service.py`, `drission_page.py`, hay một puppeteer service trong tương lai):
1. Không phải viết lại các action tương tác nền tảng (nhập dữ liệu, click, kiểm tra trạng thái đăng nhập, xác thực 2FA/checkpoint) cho từng nền tảng (Facebook, YouTube, TikTok, Twitter).
2. Không cần phải phân chia các thư mục kịch bản tương tác theo driver như hiện tại (`platforms_drissionpage` và `platforms_playwright` riêng biệt). Thay vào đó, cần định nghĩa một cơ chế tương tác trừu tượng (ví dụ: Page Object Pattern, Action Commands, hoặc Adapter cho Browser Page API) để các kịch bản nền tảng có thể tái sử dụng chung một tập hợp lệnh điều khiển bất kể driver bên dưới là gì.

---

## Objective

Generate a production-ready implementation planning document from the source idea.

Do not write source code.

Do not create the Technical Blueprint yet.

Save the generated planning document to:

```text
docs/plans/001_driver_agnostic_platform_actions.md
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
   * existing related modules (specifically [backend/app/infrastructure/automation/](file:///c:/Users/Kyle/windows/Projects/Automation_SocialMedia/backend/app/infrastructure/automation))
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
* Ví dụ: Định nghĩa một Interface `BasePageWrapper` chung với các phương thức như `navigate(url)`, `type_text(selector, text)`, `click_element(selector)`, `get_element_html(selector)`, `current_url()`, v.v.
* Các driver (DrissionPage, Playwright, Puppeteer) sẽ cài đặt (implement) interface `BasePageWrapper` này.
* Các kịch bản đăng nhập mạng xã hội (Facebook, YouTube, v.v.) sẽ chỉ nhận vào một đối tượng `BasePageWrapper` và gọi các phương thức trừu tượng này, loại bỏ sự phụ thuộc trực tiếp vào các phần tử của riêng DrissionPage (`page.ele`) hay Playwright.

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
<!-- File path: docs/plans/001_driver_agnostic_platform_actions.md -->
```

* not include source code
* not create blueprint
* not modify implementation files
