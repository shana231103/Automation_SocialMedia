# Symbol Index

| Symbol | Type | Module | File | Description |
|--------|------|--------|------|-------------|
| `Account` | Class | `backend_domain` | [models.py](file:///c:/Users/Kyle/windows/Projects/Automation_SocialMedia/backend/app/domain/models.py) | Represents social network account credentials and status. |
| `LoginHistory` | Class | `backend_domain` | [models.py](file:///c:/Users/Kyle/windows/Projects/Automation_SocialMedia/backend/app/domain/models.py) | Audit log capturing results and execution streams of login checks. |
| `Platform` | Enum | `backend_domain` | [models.py](file:///c:/Users/Kyle/windows/Projects/Automation_SocialMedia/backend/app/domain/models.py) | Valid platforms (Facebook, YouTube, TikTok, Twitter). |
| `LoginStatus` | Enum | `backend_domain` | [models.py](file:///c:/Users/Kyle/windows/Projects/Automation_SocialMedia/backend/app/domain/models.py) | Verification states (logged in, logged out, checkpoint, dead). |
| `AccountRepository` | Class | `backend_domain` | [repositories.py](file:///c:/Users/Kyle/windows/Projects/Automation_SocialMedia/backend/app/domain/repositories.py) | Interface boundary for social account CRUD storage. |
| `LoginHistoryRepository` | Class | `backend_domain` | [repositories.py](file:///c:/Users/Kyle/windows/Projects/Automation_SocialMedia/backend/app/domain/repositories.py) | Interface boundary for history audit logs. |
| `BrowserContextManager` | Class | `backend_application` | [interfaces.py](file:///c:/Users/Kyle/windows/Projects/Automation_SocialMedia/backend/app/application/interfaces.py) | Context manager abstraction for browser process lifecycle. |
| `AutomationService` | Class | `backend_application` | [interfaces.py](file:///c:/Users/Kyle/windows/Projects/Automation_SocialMedia/backend/app/application/interfaces.py) | Port specifying login automation triggers. |
| `SQLAlchemyAccountRepository` | Class | `backend_infrastructure` | [repositories.py](file:///c:/Users/Kyle/windows/Projects/Automation_SocialMedia/backend/app/infrastructure/database/repositories.py) | Concrete PostgreSQL CRUD mapping engine. |
| `SQLAlchemyLoginHistoryRepository` | Class | `backend_infrastructure` | [repositories.py](file:///c:/Users/Kyle/windows/Projects/Automation_SocialMedia/backend/app/infrastructure/database/repositories.py) | Concrete history audit mapping engine. |
| `GemLoginBrowser` | Class | `backend_infrastructure` | [gemlogin_browser.py](file:///c:/Users/Kyle/windows/Projects/Automation_SocialMedia/backend/app/infrastructure/automation/gemlogin_browser.py) | Context manager executing and attaching to GemLogin Antidetect Browser profiles. |
| `LocalBrowser` | Class | `backend_infrastructure` | [local_browser.py](file:///c:/Users/Kyle/windows/Projects/Automation_SocialMedia/backend/app/infrastructure/automation/local_browser.py) | Context manager running standard local Chrome instances. |
| `PlaywrightBrowser` | Class | `backend_infrastructure` | [playwright_browser.py](file:///c:/Users/Kyle/windows/Projects/Automation_SocialMedia/backend/app/infrastructure/automation/playwright_browser.py) | Context manager wrapping Playwright connection to local or GemLogin instances. |
| `DrissionPageService` | Class | `backend_infrastructure` | [drission_page.py](file:///c:/Users/Kyle/windows/Projects/Automation_SocialMedia/backend/app/infrastructure/automation/drission_page.py) | Automation runner implementing DrissionPage. |
| `PlaywrightService` | Class | `backend_infrastructure` | [playwright_service.py](file:///c:/Users/Kyle/windows/Projects/Automation_SocialMedia/backend/app/infrastructure/automation/playwright_service.py) | Automation runner implementing Playwright. |
