# ADR 0002: Server-Side Authentication, Role-Based Authorization, and Approval-Gated Plan Activation

## Status
Accepted

## Context
A security and governance audit of ProjectOps revealed several critical architectural gaps:
1. Every project endpoint was completely unauthenticated and accessible to any client.
2. The frontend "login" generated random UUIDs in client `localStorage` that the backend never validated.
3. Audit attribution fields (`decided_by`, `updated_by`, `created_by`, and `?triggered_by=`) were client-supplied strings in request bodies and queries, permitting trivial actor forgery.
4. Calling `POST /api/v1/projects/{id}/plans` activated the provided plan immediately with client-selected version numbers, violating the core principle that active plan mutations require human governance and approval.

## Decisions

### 1. Maintain Pure Domain Isolation
In strict accordance with ADR 0001 and `AGENTS.md`, authentication, password hashing, token validation, and RBAC logic live entirely outside `backend/app/domain` within `backend/app/auth`, schemas, and API dependencies. The domain engine remains 100% pure Python with zero auth or database imports.

### 2. Password Hashing & Token Architecture
- **Password Hashing**: Implemented via Argon2id (`argon2-cffi`), resisting GPU brute-force attacks. During login, a constant-time dummy hash verification is executed for unknown emails to prevent timing-based email enumeration.
- **Tokens**: Signed JSON Web Tokens (JWT) using HMAC-SHA256 (`HS256`). Claims include `sub` (user UUID), `exp` (default 60 minutes), and `iat`.
- **Fast-Fail Configuration**: `auth_secret_key` has no hardcoded default and fails fast with a descriptive configuration error if unconfigured in production or development outside tests.

### 3. Server-Derived Identity & Forgery Defense
- **Actor Attribution**: All governance actions derive the actor string directly from the authenticated JWT claims:
  - `decided_by = user.id`
  - `updated_by = user.id`
  - `created_by = user.id`
  - `recorded_by = user.id`
  - `triggered_by = f"user:{user.id}"` for manual agent loop execution.
- **Rejection of Client-Supplied Identity**: Request schemas (`PlanCreateRequest`, `TaskStatusUpdateRequest`, `ReplanApprovalRequest`, `ReplanRejectionRequest`, `DecisionCreateRequest`, `ProgressEventCreateRequest`) are configured with Pydantic's `extra="forbid"`. Clients sending legacy actor fields receive `422 Unprocessable Entity` rather than being silently ignored.

### 4. Zero-Leakage 404 vs 403 Policy
- To prevent external attackers or unauthorized users from probing whether a specific project ID exists:
  - If a user has no membership in a project, requests to any `/projects/{project_id}/*` route return `HTTP 404 Not Found` (never 403).
  - If a user is a member of the project but lacks the `owner` role required for owner-only mutations (such as initial plan activation or replan approvals), the system returns `HTTP 403 Forbidden`.

### 5. Approval-Gated Plan Activation
- `POST /api/v1/projects/{id}/plans` now creates an immutable snapshot with `is_active=False`. The server determines the version monotonically (`max_existing + 1`), rejecting client-supplied version numbers.
- A new endpoint `POST /api/v1/projects/{id}/plans/{version}/activate` (Owner only) governs initial plan activation. It requires a mandatory, non-empty rationale string.
- If a project already has an active plan, calling `/activate` returns `HTTP 409 Conflict`. All subsequent plan changes must proceed through the deterministic simulation and proposal approval workflow (`/replan/propose` $\to$ `/replan/approve`).
- Plan activation executes within a single atomic transaction: setting `is_active=True`, logging an append-only `PLAN_ACTIVATED` decision record, logging a progress history event, recording an `AgentRun` entry, and backfilling task execution states.

### 6. Client Token Storage Trade-off
- Access tokens are stored in application memory with `sessionStorage` fallback for page reloads.
- `localStorage` is purged and forbidden for token storage to reduce persistent XSS exposure.
- *Security Trade-off*: While `sessionStorage` remains accessible to running JavaScript (vulnerable to XSS), it is isolated to the browser tab session and cleared upon tab close. HttpOnly SameSite cookie sessions represent a future hardening phase.

### 7. GitHub Webhook Signature Exemption
- The GitHub webhook endpoint (`POST /projects/{id}/github/webhook`) is explicitly exempt from user JWT authentication. It authenticates exclusively via `X-Hub-Signature-256` HMAC-SHA256 against `GITHUB_WEBHOOK_SECRET`.

## Consequences

- **Positive**:
  - Eliminates unauthenticated access across all project endpoints.
  - Immutably binds all governance, execution state transitions, and audit records to cryptographically verified user identities.
  - Guarantees that plans cannot be activated silently without recorded owner rationale or formal proposal approval.
  - Prevents external project existence enumeration via strict 404 access gates.
- **Negative / Trade-offs**:
  - Legacy unowned projects (created before Phase F) have no owner memberships and remain inaccessible until claimed or backfilled.
  - Absence of refresh tokens in this phase requires users to re-authenticate when the 60-minute JWT expires.
  - Onboarding wizards remain decoupled from live backend APIs until Phase G (`TODO(phase-g)`).
