````md
# High-Level Architecture + Delivery Plan — Authentication Snippet Discovery System

## 1. Objective

Build a scalable web application that accepts any public website URL, safely loads the page, detects authentication-related markup, and returns the most relevant HTML snippet containing the login or authentication component.

The solution should demonstrate:

- website scraping and markup analysis
- authentication component discovery
- dynamic user input through a UI
- structured, explainable output
- good engineering standards for scalability, performance, and maintainability

---

## 2. What the System Should Do

### Functional Requirements
- Accept any public website URL from the UI
- Scrape or render the page
- Detect login or authentication-related markup
- Return the most relevant HTML snippet containing:
  - password input
  - username/email input
  - auth-related form/container
- Return a clear `not found` response if no authentication component exists

### Non-Functional Requirements
- Handle JavaScript-heavy pages
- Be safe against misuse of arbitrary URLs
- Be modular and easy to extend
- Fail gracefully on unsupported or protected targets
- Be structured for future growth and multi-site scaling

---

## 3. Recommended Architecture

```text
[ Web UI ]
    ↓
[ Backend API ]
    ↓
[ URL Validation + Safety Layer ]
    ↓
[ Scan Orchestrator ]
    ↓
[ Browser Fetch / Render Layer ]
    ↓
[ DOM Extraction + Parsing Layer ]
    ↓
[ Authentication Detection Engine ]
    ↓
[ Snippet Extraction + Confidence Scoring ]
    ↓
[ Response Formatter ]
    ↓
[ UI Result View ]
````

---

## 4. Core Design Decision

This should be built as a **small web product**, not a one-off script.

### Recommended Stack

* **Frontend:** React + TypeScript
* **Backend:** FastAPI
* **Browser Rendering:** Playwright
* **DOM Parsing:** BeautifulSoup or lxml
* **Optional Async Scale Later:** Redis + background workers

### Why this stack

* React gives a clean UI for dynamic input
* FastAPI gives typed request/response contracts
* Playwright handles modern JS-rendered auth pages
* BeautifulSoup/lxml keeps extraction logic simple and testable
* This stack is easy to explain, demo, and defend in review

---

## 5. Core Components

## 5.1 Web UI Layer

### Responsibilities

* Accept dynamic website URL input
* Trigger scans
* Display result state:

  * found
  * not found
  * protected / inaccessible
  * timeout / error
* Show:

  * confidence
  * detection signals
  * HTML snippet

### Design Principle

Keep frontend thin. No scraping logic in the browser client.

---

## 5.2 Backend API Layer

### Responsibilities

* Expose a scan endpoint, for example:

  * `POST /api/scan`
* Validate incoming request payload
* Call scan orchestration flow
* Return structured JSON result

### Design Principle

Backend owns all network access, extraction, safety, and scoring logic.

---

## 5.3 URL Validation + Safety Layer

### Responsibilities

* Validate syntax
* Allow only `http` and `https`
* Block localhost / private / loopback / reserved IPs
* Enforce timeout and content limits
* Prevent the service from being used as a generic network scanner

### Design Principle

Arbitrary URL input is a security-sensitive boundary and must be treated carefully.

---

## 5.4 Scan Orchestrator

### Responsibilities

* Coordinate the scan lifecycle
* Decide execution path
* Standardize scan stages
* Manage retries / fallbacks if needed

### Typical Flow

1. Validate URL
2. Load page through browser renderer
3. Extract rendered DOM
4. Run auth detection
5. Extract best snippet
6. Format result

### Design Principle

The orchestrator should manage workflow, not implement parsing or browser logic directly.

---

## 5.5 Browser Fetch / Render Layer

### Responsibilities

* Open target page
* Render JavaScript
* Wait for DOM to stabilize
* Return final page HTML for analysis

### Why

Many real login forms are not present in raw initial HTML and only appear after client-side rendering.

### Recommended Tool

* Playwright
* Headless Chromium
* one isolated browser context per scan request

### Performance Practices

* block images, fonts, media
* apply strict timeouts
* close page/context immediately after scan
* keep browser lifecycle controlled

---

## 5.6 DOM Extraction + Parsing Layer

### Responsibilities

* Parse rendered HTML
* Normalize markup
* Traverse parent-child DOM structure
* Identify meaningful containers

### Candidate Containers

* `form`
* `div`
* `section`
* `article`
* modal body
* auth-related wrappers

### Design Principle

Keep DOM parsing independent from browser automation.

---

## 5.7 Authentication Detection Engine

### Responsibilities

* Detect likely authentication sections
* Score candidate containers
* Distinguish login/auth forms from unrelated forms

### Detection Signals

* `input[type="password"]`
* username/email inputs nearby
* `<form>` presence
* labels like `email`, `username`, `password`
* placeholders like `enter your password`
* buttons like `login`, `log in`, `sign in`, `continue`
* nearby auth text like `sign in to your account`

### Design Principle

Use scoring heuristics instead of only regex or one-tag matching.

### Why

This is more robust across real sites and looks more senior than simple static pattern matching.

---

## 5.8 Snippet Extraction + Confidence Scoring

### Responsibilities

* Find the smallest useful enclosing HTML block
* Extract only the most relevant markup
* Assign a confidence score
* Return explainable detection signals

### Output Shape

* input URL
* found / not found
* confidence
* source
* detection signals
* HTML snippet
* message

### Design Principle

Return the best meaningful auth container, not the entire page HTML.

---

## 5.9 Response Formatter

### Responsibilities

* Normalize success and failure responses
* Keep API contract stable
* Hide internal implementation details

### Recommended States

* `found`
* `not_found`
* `protected_or_blocked`
* `invalid_input`
* `timeout`
* `scan_error`

---

## 6. Recommended Code Structure

```text
auth-snippet-finder/
  backend/
    app/
      api/
        routes.py
        schemas.py
      core/
        config.py
        logging.py
      security/
        url_validation.py
        network_safety.py
      services/
        scan_orchestrator.py
        browser_service.py
        dom_service.py
        auth_detector.py
        snippet_extractor.py
        formatter.py
      tests/
        unit/
        integration/
  frontend/
    src/
      components/
      pages/
      services/
      types/
  README.md
```

### Design Standard

Each module should have one clear responsibility:

* `browser_service` → page loading and rendering
* `dom_service` → parsed DOM access
* `auth_detector` → auth candidate scoring
* `snippet_extractor` → final snippet extraction
* `formatter` → response shape
* `scan_orchestrator` → execution flow

This makes the system easier to test, extend, and maintain.

---

## 7. Scalability Considerations

## 7.1 Stateless API Layer

API instances should remain stateless so they can scale horizontally.

### Why

This enables multiple containers or instances behind a load balancer.

---

## 7.2 Browser Resource Control

Headless browsers are expensive in CPU and memory.

### Best Practices

* use bounded concurrency
* isolate each request using browser contexts
* avoid launching a full browser per request if not necessary
* apply strict per-request timeout budgets

### Why

This prevents resource exhaustion under concurrent scans.

---

## 7.3 Async Job Model for Growth

For small demos, synchronous request-response is fine.

For larger scale:

* accept request
* enqueue scan
* worker performs scan
* UI polls for result

### Recommended Future Stack

* Redis
* Celery / RQ / Dramatiq

### Why

This decouples user traffic from expensive browser execution.

---

## 7.4 Caching

Short-TTL caching can improve repeat scans of the same public URL.

### Cache Candidates

* normalized rendered DOM
* detection result
* final snippet response

### Caution

Keep TTL short because login pages may change.

---

## 8. Performance Considerations

### Reduce Rendering Cost

* block unnecessary asset types
* stop after DOM is usable
* avoid deep interaction if not needed

### Reduce Analysis Cost

* analyze likely auth containers first
* cap traversal depth
* score only useful candidate nodes

### Apply Strict Time Budgets

* connection timeout
* page load timeout
* DOM extraction timeout
* total scan timeout

### Principle

Fast, predictable scans are better than slow, fragile ones.

---

## 9. Reliability and Failure Handling

## Expected Failure Modes

* invalid URL
* DNS failure
* site timeout
* malformed HTML
* no auth section present
* blocked or protected website
* partial rendering / unstable page

## Recommended Behavior

Return structured and honest responses instead of masking failures.

### Example Outcome Types

* `found`
* `not_found`
* `protected_or_blocked`
* `timeout`
* `invalid_input`
* `scan_error`

### Principle

Graceful failure handling is part of production quality.

---

## 10. Security Considerations

This service accepts arbitrary URLs, so security must be first-class.

### Required Safeguards

* allow only public `http/https` URLs
* reject private/internal addresses
* restrict redirects
* enforce timeouts and size limits
* do not submit forms
* do not enter credentials
* do not bypass website protections
* sanitize logs and error messages

### Principle

The system is a read-only markup inspection tool.

---

## 11. Observability

## Logging

Use structured logs with:

* request ID
* URL
* scan duration
* result state
* confidence
* failure reason

## Metrics

Track:

* request count
* success rate
* not found rate
* timeout rate
* protected rate
* average scan latency
* browser resource usage

## Why

Good observability makes the system operable and debuggable at scale.

---

## 12. Testing Strategy

## Unit Tests

Test:

* URL validation
* detection scoring
* snippet extraction
* formatter behavior

## Integration Tests

Test:

* HTML fixtures with login forms
* signup-only forms
* no-auth pages
* malformed markup

## End-to-End Tests

Test:

* UI to backend request flow
* success state
* failure state
* result rendering

### Principle

Heuristic systems need fixture-based regression testing.

---

## 13. Delivery Plan

This is the high-level plan for implementing the solution in a clean, senior-level way.

## Phase 1 — Foundation

Set up the project structure and base services.

### Tasks

* initialize frontend and backend projects
* define typed request/response models
* implement URL validation and safety checks
* set up base logging and config

### Outcome

A stable skeleton with clean project boundaries.

---

## Phase 2 — Browser-Based Page Acquisition

Add reliable page loading for both static and JS-heavy websites.

### Tasks

* integrate Playwright
* implement page rendering service
* configure timeouts
* block unnecessary assets for speed
* return rendered HTML

### Outcome

Reliable page acquisition for real-world modern websites.

---

## Phase 3 — Authentication Detection Engine

Implement the logic that finds auth-related sections.

### Tasks

* parse rendered DOM
* identify candidate containers
* detect password, username/email, auth forms, and buttons
* score candidates using multiple signals

### Outcome

A robust detector that works beyond simple string matching.

---

## Phase 4 — Snippet Extraction and Structured Output

Return the smallest meaningful auth-related block in a clean format.

### Tasks

* extract nearest relevant parent container
* clamp snippet size
* build structured response
* include confidence and explanation signals

### Outcome

Useful and explainable output for both UI and API consumers.

---

## Phase 5 — UI Integration

Add dynamic user input and result visualization.

### Tasks

* build URL input screen
* call backend scan endpoint
* render result states
* display snippet and metadata

### Outcome

A complete user-facing application satisfying the assignment requirement.

---

## Phase 6 — Hardening and Quality

Polish the system to production-style standards.

### Tasks

* add tests
* improve error handling
* add structured logs
* add protected / blocked response state
* add README with architecture and tradeoffs

### Outcome

A professional, review-ready submission.

---

## 15. Final Recommendation

The strongest version of this assignment is:

* **React UI**
* **FastAPI backend**
* **Playwright for rendered DOM**
* **BeautifulSoup/lxml for parsing**
* **heuristic auth detection**
* **safe arbitrary URL handling**
* **structured, explainable output**
* **modular codebase**
* **clear failure states**
* **tests and observability**

