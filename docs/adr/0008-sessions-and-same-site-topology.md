---
status: proposed
date: 2026-10-01
decision-makers: Arka
consulted: R3, R4, R7
blueprint-sections: "§6.3, §6.4, §13, §15, §16"
---

# ADR-0008: Opaque server-side sessions, argon2id via pwdlib, and a same-site domain topology

## Context and Problem Statement

v2.0.0 specifies "short-lived access token + rotating refresh token in httpOnly cookies", web on Vercel and API
on EC2 behind Caddy. Two issues:

1. **JWT access + refresh rotation is the complex option** for a single first-party web app talking to a single
   API that already hits Postgres on every request. It adds token-family tracking, reuse detection, clock-skew
   handling and still needs a server-side denylist for logout/role change. Opaque sessions give instant
   revocation (role change, logout, compromised account) with one indexed lookup.
2. **Cookies across sites.** `*.vercel.app` and an EC2 hostname are *different sites*. Browsers increasingly block
   third-party cookies, and `SameSite=None` cookies need extra CSRF care. If web and API share a registrable
   domain (`app.<domain>` and `api.<domain>`), cookies are **same-site** and `SameSite=Lax` works.
3. FastAPI's current security tutorial uses **`pwdlib[argon2]`** and **PyJWT**; `passlib` is unmaintained.

## Decision Drivers

* ASVS L1 with the least custom crypto/protocol code.
* Revocation must be immediate (RBAC changes are audited, §13).
* Works in all major browsers without third-party cookies.

## Considered Options

1. JWT access + rotating refresh (v2.0.0).
2. **Opaque session id (256-bit random) in `__Host-`-style httpOnly Secure SameSite=Lax cookie; server stores
   `sha256(session_id)` in `sessions` table with expiry, idle timeout, user agent hash; CSRF = double-submit
   token + `Origin` check on mutations.**
3. Managed auth (Clerk/Auth0) or Better Auth in Next.js with JWKS verification in FastAPI.

## Decision Outcome

Chosen option: **2**, plus topology:

* Buy a cheap domain (e.g., a `.my.id` or `.dev`); web at `app.<domain>` (Vercel custom domain), API at
  `api.<domain>` (Caddy TLS). Cookie `Domain` unset (host-only on `api.<domain>`), `SameSite=Lax`, `Secure`,
  `HttpOnly`, `Path=/`. CORS allowlist = `https://app.<domain>` with credentials.
* Passwords: `pwdlib` `PasswordHash.recommended()` (argon2id); rehash-on-login when parameters change.
* Sessions: absolute lifetime 7 days, idle timeout 12 h, rotate id on login and on privilege change,
  revoke all sessions on password change.
* PyJWT is **not** needed. (If a future MCP server/API client needs tokens, add scoped API keys — ADR then.)

### Consequences

* Good: less code, instant revocation, easy to test, easy to explain.
* Good: preview deployments on `*.vercel.app` use a **demo API** with seeded sandbox users only (no real
  cookies cross sites) — documented in RUNBOOK.
* Bad: one DB read per authenticated request (indexed, < 1 ms). Acceptable.
* Bad: ~US$1–15/year for a domain. Acceptable; also improves the portfolio link.

### Confirmation

* CP-25 tests: login sets cookie with the exact attributes; logout invalidates server row; role change kills
  existing sessions; mutation without CSRF token → 403 problem+json; session fixation test (id rotates on login).
* CP-31 security checklist item "cookies same-site, no tokens in JS-readable storage" checked in browser devtools.

## More Information

* https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/ (pwdlib + PyJWT in current tutorial)
* https://github.com/fastapi/fastapi/discussions/11773 (passlib unmaintained)
* OWASP Session Management Cheat Sheet; OWASP CSRF Prevention Cheat Sheet
