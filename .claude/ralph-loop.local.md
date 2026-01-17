---
active: true
iteration: 1
max_iterations: 30
completion_promise: "COMPLETE"
started_at: "2026-01-17T15:53:57Z"
---

# PRD: Hybrid Authentication System (Subdomain Architecture)

## Introduction
Implement a robust, production-ready FastAPI Server with a hybrid authentication system for Meowart.ai. This system supports a Hybrid model allowing users to log in via **Google OAuth** (for low friction) or **Email/Password** (traditional).

The architecture uses **Subdomain Separation**:
- **Frontend:** 'https://meowart.ai'
- **Backend:** 'https://api.meowart.ai' (FastAPI)

Crucially, the system handles **Automatic Registration & Merging**: if a user logs in with Google and that email already exists in the database (from a previous password registration), the accounts are silently merged, and the user is logged in.

## Goals
- Support standard Google OAuth 2.0 flow.
- Support traditional Email/Password registration and login.
- **Unified Identity:** One user record per email address, regardless of login method.
- **Cross-Subdomain Session:** Ensure login state persists between 'api.meowart.ai' and 'meowart.ai'.
- Secure password storage using hashing (e.g., bcrypt).

## User Stories

### US-001: Database Schema & Setup
**Description:** As a developer, I need the database ready to store users with support for both password and Google identities.

**Acceptance Criteria:**
- [ ] Create 'users' table with fields: 'id', 'email' (unique), 'password_hash' (nullable), 'google_id' (nullable, unique), 'avatar_url', 'created_at'.
- [ ] 'password_hash' is nullable (Google-only users won't have a password).
- [ ] 'google_id' is nullable (Password-only users won't have one).
- [ ] Database migration script created and executed successfully.

### US-002: Google Login (Redirect & Callback)
**Description:** As a user, I want to click Sign in with Google to log in without remembering a password.

**Acceptance Criteria:**
- [ ] **Endpoint:** 'GET /api/auth/google/login' redirects user to Google's consent screen.
- [ ] **Endpoint:** 'GET /api/auth/google/callback' handles the return from Google.
- [ ] **Logic (Auto-Merge):**
    - If Google email does **not** exist in DB -> Create new user -> Set Session.
    - If Google email **exists** in DB -> Update user record with 'google_id' -> Set Session.
- [ ] **Redirect:** After success, redirect browser to 'https://meowart.ai/'.
- [ ] **Cookie:** Session cookie must have 'domain=.meowart.ai' so frontend can read it.

### US-003: Email Registration
**Description:** As a user, I want to create an account using my email and a password if I don't use Google.

**Acceptance Criteria:**
- [ ] **Endpoint:** 'POST /api/auth/register' accepts JSON '{email, password}'.
- [ ] Validates email format.
- [ ] Checks if email already exists -> returns 400 error if true.
- [ ] Hashes password before storing in DB.
- [ ] Automatically logs user in (sets session) upon successful registration.

### US-004: Email Login
**Description:** As a user, I want to log in with my registered email and password.

**Acceptance Criteria:**
- [ ] **Endpoint:** 'POST /api/auth/login' accepts JSON '{email, password}'.
- [ ] Finds user by email -> verifies password hash.
- [ ] If valid -> Sets session cookie ('domain=.meowart.ai').
- [ ] If invalid -> Returns 401 error.

### US-005: Who Am I (Session Check)
**Description:** As the frontend application, I need to know the current user's state to update the UI.

**Acceptance Criteria:**
- [ ] **Endpoint:** 'GET /api/auth/me'.
- [ ] If cookie is valid -> Return user profile (id, email, avatar).
- [ ] If cookie is missing/invalid -> Return 401 Unauthorized or 'null'.
- [ ] **CORS Check:** Verify frontend ('meowart.ai') can successfully call this API endpoint on a different domain ('api.meowart.ai') with credentials.

### US-006: Logout
**Description:** As a user, I want to sign out securely.

**Acceptance Criteria:**
- [ ] **Endpoint:** 'POST /api/auth/logout'.
- [ ] Clears the session cookie (sets expiry to past).
- [ ] Redirects or returns success message.

## Functional Requirements

1.  **CORS Configuration:** Backend MUST allow 'https://meowart.ai' with 'allow_credentials=True'.
2.  **Cookie Configuration:**
    - 'key': session_id (or similar)
    - 'domain': **.meowart.ai** (Critical for subdomain separation)
    - 'httponly': True
    - 'samesite': lax
    - 'secure': True (Production only/HTTPS)
3.  **Google OAuth Config:**
    - 'redirect_uri' sent to Google MUST be 'https://api.meowart.ai/api/auth/google/callback'.
4.  **Error Handling:**
    - Duplicate email on register -> 400 Bad Request.
    - Invalid login -> 401 Unauthorized.

## Non-Goals
- **Email Verification:** No Click link to verify email flow for MVP.
- **Forgot Password:** Password reset flow is out of scope for this sprint.
- **Username Management:** Users will be identified by Email/Name from Google for now.

## Technical Considerations

### Subdomain Separation Challenges
Since Frontend ('meowart.ai') and Backend ('api.meowart.ai') are different origins:
1.  **HTTPS is Mandatory:** Both domains must have valid SSL certs for 'Secure' cookies to work properly in modern browsers.
2.  **Cookie Domain:** The backend middleware *must* explicitly set 'domain=.meowart.ai'. If this is missed, the frontend cannot detect the login state.

### Tech Stack
- **Framework:** FastAPI
- **Auth Library:** 'authlib' (for Google), 'passlib[bcrypt]' (for hashing).
- **Session:** 'SessionMiddleware' from 'starlette'.
- **Database:** SQLAlchemy (Async).

## Success Metrics
- 100% success rate for merging existing email accounts with Google login.
- Frontend can successfully retrieve user data via '/me' after a redirect from Google.

## Finally
Output <promise>COMPLETE</promise> when all phases done.
