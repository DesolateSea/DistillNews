# Security configuration after upstream sync

The security fixes from the saved fork commits were adapted to upstream's
`server/`, `service/`, `pipeline/`, and separate embedding architecture. The old
backend was not restored. Ollama now uses the existing OpenAI-compatible provider:
set `AGENT_PROVIDER=ollama`, `OLLAMA_BASE_URL` (without `/v1`), and `OLLAMA_MODEL`.
The upstream OpenAI/Foundry option remains available. Julep is no longer a dependency.

## Required setup

- Python 3.11+; API dependencies: `server/requirements.txt`.
- Set a fresh random `JWT_SECRET` containing at least 32 bytes. Startup rejects
  missing/short secrets. Rotate any credentials exposed by a prior compromise.
- Set `CORS_ORIGINS` to exact trusted frontend origins; wildcards are rejected.
- Browser requests use `/api`, proxied by Next.js to server-only `BACKEND_URL`.
  This value is needed **at build time** for standalone builds. Compose supplies
  `http://backend:8000`; direct local builds default to `http://127.0.0.1:8000`.
- Production requires HTTPS and `COOKIE_SECURE=true` (default). For local HTTP
  development only, set `COOKIE_SECURE=false` and use `http://localhost:3000`.
- Access sessions expire after `ACCESS_TOKEN_EXPIRE_MINUTES=60` by default.
- Configure your own matching `GOOGLE_CLIENT_ID` and
  `NEXT_PUBLIC_GOOGLE_CLIENT_ID`. Google login rejects email-only requests,
  unverified emails, expired tokens and tokens for another OAuth client.
- Set SMTP `EMAIL` / `PASS`. Failed delivery now returns 503; OTPs are never
  returned or logged. Each OTP session is atomically consumed on its first
  verification attempt, including an incorrect attempt. Request a new code
  after a failed attempt.

## Sessions and API protections

Existing users must log in again. Legacy localStorage bearer tokens are ignored
and removed by the frontend. Sessions use HttpOnly/Secure/SameSite=Strict cookies.
Mutations require an allowed Origin and a CSRF header bound to the signed session.
Logout increments the user's session version, invalidating all device sessions.
The readable CSRF cookie is only a UI hint, not authentication.

Chat permits guests with peer-based rate limits and isolated per-request histories;
signed-in users retain user-scoped histories and CSRF protections. Tracking requires
authentication. Chat accepts validated JSON messages
up to 4,000 characters. Reading durations must be finite, positive and at most
one hour. Pagination is bounded. `/store_article` is removed. File article IDs
cannot traverse paths. Registration passwords require 12 characters and at most
72 UTF-8 bytes; existing bcrypt hashes remain compatible.

MongoDB fixed-window limits cover authentication, OTP, chat and tracking across
workers. A TTL index expires buckets; unavailable storage fails closed. Unique
email index failures now fail startup: back up and resolve duplicate accounts
explicitly, never delete them automatically. Limits use the actual connection
peer, not spoofable forwarded headers. Behind Next.js, clients can share a peer
bucket; add per-client throttling at a trusted production reverse proxy.

Chat runs outside the event loop, allows two active jobs and one job per user per
worker, and returns a timeout after 60 seconds. Cancellation/timeout retains the
slot until the real worker finishes. Provider calls have finite timeouts and
output bounds. Histories expire after an hour and hold at most 1,000 users with
six entries each; raw chats are not logged. Limits/history continuity are
per-worker; use a single worker or a dedicated bounded job service if strict
global active-job limits are needed.

## Network, scraping and email

Compose no longer publishes the embedding port. MongoDB, Redis, MCP and the API
are bound to host loopback, while service-to-service communication uses Docker
DNS. The frontend remains public. Loopback publication does not isolate services
from other attached containers: use trusted Docker networks and host firewalls.
Do not expose Ollama or MCP publicly without additional authentication.

Scraping requires public HTTPS port 443, checks each redirect, and pins the TLS
connection to a validated public IP with original-host certificate validation.
Public proxies and compressed responses are disabled; HTML is limited to 2 MB.
OS DNS resolution may exceed the nominal fetch budget. Use network-level egress
restrictions and proxy read/connection deadlines as defense in depth.
MediaStack requires HTTPS without redirects. SMTP verifies certificates and
newsletter templates escape untrusted text and reject unsafe link schemes.
Importing the mail sender no longer sends a newsletter or logs credentials.

## Validation and deployment limits

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m pip check
python -m pip_audit
# frontend/
npm ci
npm run build
npx --no-install tsc --noEmit
npm run test:styles
npm audit
# server/email/
npm ci
node --test security.test.js
npm audit
```

These are source/dependency changes, not a live incident cleanup. No running
deployment was restarted. Preserve incident evidence, rotate exposed secrets,
inspect the host, and rebuild trusted images before deployment. Browser visual
smoke tests, real MongoDB/proxy integration, and the heavyweight embedding/pipeline
runtime audit still need staging. Tracking's upstream preference updates remain
read-modify-write and can lose simultaneous updates; they no longer accept
anonymous or unbounded input. Anonymous feed/search/weather endpoints still need
edge rate limiting. Dependencies should be audited again before every release.

Validation snapshot: 80 Python tests passed; clean npm installations, production
build with TypeScript validation, separate TypeScript and generated-CSS checks,
and mail regression tests passed. Frontend/mail npm audits and the installed
Python test/API environment audit reported zero known vulnerabilities. The
Python environment used Python 3.14; container Python versions have not been
integration-tested. This snapshot does not cover every optional pipeline model
dependency or a running deployment.
