<!-- File path: docs/plans/002_command_based_automation_actions.md -->

# Implementation Plan – Command-Based Automation Actions (Strategy/Command Pattern)

## 1. Overview
- **Feature Name**: Command-Based Browser Automation Actions (Registry & Strategy Pattern)
- **Business Objective**: Enable rapid deployment of new browser features (such as posting content, reading notifications, scraping followers) without causing file bloat or high regression risks in the core automation modules.
- **Technical Objective**: Refactor `PlaywrightAutomationService` and `DrissionPageAutomationService` by extracting the monolithic `run_login` logic into a polymorphic, extensible Action-based design. Each automation functionality becomes an independent class implementing a common `AutomationAction` interface. A main registry/dispatcher will orchestrate action execution by dispatching tasks to their respective classes.
- **Expected Outcome**: Class size of the service implementations is reduced to a minimal dispatcher wrapper. New browser features can be added by registering a new class without modifying existing services.

---

## 2. Memory Consultation Summary
- **Memory Confidence**: High (Memory bootstrapped on 2026-07-03T05:30:30+07:00 and updated).
- **Memory Documents Read**:
  - `project-summary.md` (Clean Architecture conventions, module dependencies, build/test commands)
  - `architecture/overview.md` (DDD flow diagrams)
  - `architecture/browser.md` (automation services, context managers, active providers)
- **RAG Query Used**: N/A (Consulted memory docs directly).
- **Additional Source Files Inspected**:
  - `backend/app/infrastructure/automation/playwright_service.py` (to inspect `run_login` signature and logging logic)
  - `backend/app/infrastructure/automation/drission_page.py` (to inspect `run_login` signature and logging logic)
  - `backend/app/infrastructure/automation/page_wrapper.py` (to verify the input interfaces available for actions)
- **Key Architectural Findings**:
  - Currently, both services duplicate the context entry setup (`with browser_manager as native_page: page = Wrapper(native_page)`), platform dispatch logic (`if platform == Platform.FACEBOOK: ...`), logging helpers (`def log(...)`), and final log formatting.
  - An Action-based abstraction would let the main services handle context management and logging setup generically, delegating only the actual page execution steps to the specific Action subclass.

---

## 3. Current Architecture
- **Current Modules**: `backend_infrastructure` governs the execution via `DrissionPageAutomationService` and `PlaywrightAutomationService`.
- **Current Responsibilities**:
  - `drission_page.py` & `playwright_service.py` construct `BrowserContextManager` and yield SSE logs. They directly call the platform-specific scripts (`login_facebook`, etc.) inside their hardcoded `run_login` methods.
- **Existing Limitations**:
  - **High Coupling**: If a new feature like `post_message` is added, both services must implement a matching `run_post()` method, leading to code bloat and high regression risk.
  - **Violates Open-Closed Principle (OCP)**: Adding features requires editing the service files.
- **Opportunities for Reuse**:
  - The browser context entry, screenshot error handling, and SSE logging loop are identical across all features and should remain inside the service layer as a generic dispatcher template.

---

## 4. Scope

### In Scope
- Defining the abstract `AutomationAction` base class/interface.
- Creating the `LoginAction` class containing the refactored login logic.
- Creating an `ActionRegistry` (or using a dynamic action-dispatcher) to map action names to their concrete action classes.
- Refactoring `PlaywrightAutomationService` and `DrissionPageAutomationService` to use the registry and run actions via a generic `run_action()` dispatcher interface.
- Ensuring the existing presentation layers calling `run_login` remain fully functional (preserving backward compatibility).
- Creating unit tests to verify the action registry and execution flow.

### Out of Scope
- Implementing concrete actions for posting messages or scraping profiles (this plan only implements the login action refactoring and registry architecture).
- Changing database tables or API route signatures.

### Assumptions
- Every automation action receives credentials and configuration parameters and outputs logs and a final status (such as `LoginStatus` or a generic `ActionStatus`).
- All actions interact with the browser solely via the `AutomationPage` wrapper.

---

## 5. Proposed Solution
We will implement the **Command/Strategy Pattern** combined with a Registry:

1. **`AutomationAction` (ABC)**:
   - Defines `execute(page: AutomationPage, params: dict, log_func) -> Any`.
2. **`LoginAction(AutomationAction)`**:
   - Encapsulates login execution (dispatching to platform-specific scripts like `login_facebook`).
3. **Registry in Services**:
   - The services hold a register of actions. When `run_login` is called (for backward compatibility) or a generic `run_action` is invoked, they fetch the registered action class, setup the browser context and log wrappers, and call `execute()`.

---

## 6. Architecture Impact
- **Affected Layers**: Infrastructure Layer (`backend_infrastructure`) only.
- **Affected Modules**: `backend/app/infrastructure/automation`.
- **Interfaces Required**: `AutomationAction` abstract class.
- **Data Flow Changes**: Instead of calling `run_login` directly, calls can go through a generic dispatcher method `run_action(action_name, params)`. For backward compatibility, `run_login` will remain and internally call the dispatcher.
- **Dependency Boundaries**: Keeps the action execution completely decoupled from the service lifecycle.

---

## 7. File Impact Analysis

### Create
- **`backend/app/infrastructure/automation/action_base.py`**:
  - Responsibility: Defines the abstract `AutomationAction` interface and any action-specific value structures.
  - Complexity: Low.
- **`backend/app/infrastructure/automation/actions/`** (New Directory):
  - `__init__.py`: Exports available actions.
  - `login_action.py`: Contains the `LoginAction` class wrapping the existing platform logins.
  - Complexity: Low (code migration).

### Modify
- **`backend/app/infrastructure/automation/drission_page.py`**:
  - Responsibility: Add action registration, change `run_login` to use the dispatcher.
  - Complexity: Medium.
- **`backend/app/infrastructure/automation/playwright_service.py`**:
  - Responsibility: Add action registration, change `run_login` to use the dispatcher.
  - Complexity: Medium.

---

## 8. Implementation Phases

### Phase 1: Core Action Abstraction & Login Action
- **Objective**: Create `AutomationAction` ABC and implement the concrete `LoginAction`.
- **Files**: `action_base.py`, `actions/__init__.py`, `actions/login_action.py`.
- **Validation**: Unit test verifying `LoginAction.execute` dispatches parameters correctly to platform functions.

### Phase 2: Service Refactoring & Registry Setup
- **Objective**: Add action registration to both automation services and dispatch execution dynamically.
- **Files**: `drission_page.py`, `playwright_service.py`.
- **Validation**: Run existing unit tests and integration test suites using `AUTOMATION_PROVIDER`.

---

## 9. Testing Strategy
- **Unit Testing**:
  - Verify action dispatching using mocks for `AutomationPage` and platform functions.
  - Test that calling an unregistered action returns a proper error message.
- **Integration Testing**:
  - Verify that the login flow remains fully functional end-to-end.

---

## 10. Risks
- **Risk 1: Parameter signature differences for future actions**
  - *Mitigation*: Use a unified `params: dict` payload or generic kwargs so that the executor method signature remains stable regardless of the action type.

---

## 11. Acceptance Criteria
- [ ] `AutomationAction` abstract class defined.
- [ ] `LoginAction` implemented and registered in both services.
- [ ] `run_login` refactored to delegate to `LoginAction` via the dispatcher.
- [ ] Unit and integration tests pass successfully.
