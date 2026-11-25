# NeuIntern Backend (FastAPI)

Python/FastAPI backend with student registration, JWT auth, the full enrollment →
offer letter → task submission → Razorpay payment → certificate journey, and an
admin API for analytics, student/payment records, and program management.

## Tech Stack

FastAPI · SQLAlchemy (SQLite by default) · python-jose (JWT) · bcrypt ·
Razorpay Python SDK · slowapi (rate limiting) · Pydantic v2

## Getting Started

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # edit JWT_SECRET, CORS_ORIGIN, Razorpay keys
alembic upgrade head            # create/upgrade the database schema
uvicorn app.main:app --reload --port 8000
```

- API: `http://localhost:8000`
- Interactive docs: `http://localhost:8000/docs`

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

Tests run against a throwaway SQLite database and never send real email or call
Razorpay, whatever your `.env` says (see `tests/conftest.py`). They cover the
payment flow (order, verify, webhook, idempotency) and certificate unlocking.

## Security & sessions

**Sessions.** Logging in sets an `httpOnly` cookie (`neuintern_session`) holding the JWT,
so page scripts can never read it. The login response still includes the token for
non-browser API clients (`Authorization: Bearer`). Cookie-authenticated requests that
change data must send an `X-Requested-With` header (the frontend does this) as a CSRF
guard. `POST /api/auth/logout` clears the cookie. Resetting a password logs out every
existing session.

**Brute-force protection.** 5 failed logins (or wrong reset/verification codes) for the
same email within 15 minutes lock that email for 15 minutes (HTTP 429 + `Retry-After`).
Counters live in the database, so they hold across workers. Unknown emails lock the same
way, so the lockout does not reveal which emails are registered. Passwords: 8+ characters,
at most 72 bytes.

**Production checklist.** With `ENVIRONMENT=production` the server refuses to start unless:

- `JWT_SECRET` is random and 32+ characters (`python -c "import secrets; print(secrets.token_urlsafe(48))"`)
- `CORS_ORIGIN` lists your site's exact origin(s), not `*`
- cookies are `Secure` (the default in production; don't set `COOKIE_SECURE=false`)
- the admin account does not still have the published default password

Also set `ADMIN_PASSWORD` before the first start (otherwise no admin is created in production).
If the site and API are on different domains, set `COOKIE_SAMESITE=none`; for subdomains
of one domain, `COOKIE_DOMAIN=.yourdomain.com` is enough. Behind a reverse proxy run
uvicorn with `--proxy-headers` so rate limits see each visitor's real IP, not the proxy's.
After upgrading, run `alembic upgrade head` (adds `login_throttle` and `users.token_valid_after`).
Users stay logged in only if they log in again once: sessions move from localStorage to the cookie.

submitted it but haven't paid. Pacing lives in `app/services/reminder_service.py`:
first reminder 2 days after enrolling (task) / 1 day after submitting (payment),
then every 3+ days, at most 3 per enrollment, and never for enrollments older
than 60 days. Paid students are never emailed.
## Background jobs & multiple workers

Two jobs run inside the server: the hourly certificate unlock and the daily reminder
emails. It is safe to run several workers (`uvicorn --workers 3`, gunicorn, etc.): each
tick takes a database lock (`job_locks` table), so only one worker does the work, and a
worker that crashes mid-job frees its lock after 30 minutes. Certificate unlocking is also
atomic, so the scheduler, an admin's "process due" click and a late payment can never send
the same certificate twice, and workers starting together no longer collide while seeding.

To run the jobs in just one process instead, start the others with `SCHEDULER_ENABLED=false`.
After upgrading, run `alembic upgrade head` (adds `job_locks`).

## Reminder emails

A daily job (10:30 UTC) emails students who enrolled but haven't paid the
certificate fee: one email if they never submitted the task, another if they

It is **off by default** (`REMINDERS_ENABLED=false`) so a deploy never emails
existing students by surprise. To roll it out:

1. `alembic upgrade head` (adds `reminder_count` / `last_reminder_at`).
2. Admin dry run: `POST /api/admin/reminders/send?dryRun=true` reports how many
   students would be emailed, without sending or recording anything.
3. Set `REMINDERS_ENABLED=true` (and `FRONTEND_URL` for the dashboard link).

`POST /api/admin/reminders/send` (no `dryRun`) runs the job on demand.

**Unsubscribe.** Every reminder ends with a per-student unsubscribe link
(`{FRONTEND_URL}/unsubscribe?token=...`). It opens a page that asks for one click,
then calls `POST /api/unsubscribe/{token}`, which sets `users.reminders_opt_out`
(stops reminders for all of that student's enrollments; `DELETE` on the same URL
undoes it). It is POST, not GET, so mail scanners that prefetch links can't
unsubscribe anyone. Tokens are HMACs of the user id under `JWT_SECRET`, so they
never expire, **but rotating `JWT_SECRET` invalidates links in old emails**.
Set `API_PUBLIC_URL` (e.g. `https://api.neuintern.in`) to also send the RFC 8058
`List-Unsubscribe` headers, which show the native Unsubscribe button in Gmail and
Apple Mail. Offer letters, receipts and certificates are not affected.

## Database migrations (Alembic)

The schema is managed by Alembic (`alembic/versions/`); the app no longer calls
`create_all()`. It reads `DATABASE_URL` from `.env`, same as the app.

```bash
alembic upgrade head                          # apply all migrations (new/empty DB)
alembic revision --autogenerate -m "add X"    # after editing app/db/models.py
alembic upgrade head                          # then apply it
alembic downgrade -1                          # roll back one step
```

Review every autogenerated file before applying it. Alembic can't detect renames
(it sees drop + add), so fix those by hand.

**Existing database that already has these tables** (e.g. production, created by
the old `create_all`): do NOT run `upgrade head` — it would try to re-create them.
Back up first, confirm the live schema matches `models.py`, then mark it as
already at the baseline:

```bash
alembic stamp 0001
```

From then on, deploy with `alembic upgrade head` before restarting the app.

Seed data (programs, sample certificates, default admin) is still inserted by the
app at startup if the tables are empty. The default SQLite file `neuintern.db` is seeded the same way:
the 16-program catalog, two sample certificates, and a default admin account
(`admin@neuintern.com` / `Admin@123` — **change this in production**).

## Project Structure

```
app/
  main.py              FastAPI app, CORS, error normalization, startup/seed
  core/                config, JWT + bcrypt security, shared rate limiter
  db/
    models.py           User, Program, Enrollment, Certificate, Contact, Newsletter
    seed.py              Seeds programs, sample certificates, default admin
  data/                 programs.json / testimonials.json (seed source only —
                         Program is DB-backed and admin-editable after seeding)
  schemas/               Pydantic request/response models
  routers/
    auth.py               register / login / me
    programs.py            public catalog (reads DB)
    enrollments.py          enroll, offer letter, task, payment, certificate
    admin.py                enrollment list, analytics, program CRUD
    contact.py, certificate.py, testimonials.py, payments.py (legacy generic checkout)
  services/              programs_service, enrollments_service, razorpay_client
  deps.py                get_current_user / require_admin dependencies
```

## Key API Endpoints

All responses follow `{ success, data?, message? }`.

**Auth**
- `POST /api/auth/register` — `{ fullName, email, phone, degree, branch, currentYear, password }`
- `POST /api/auth/login` — `{ email, password }` → `{ token, user }` (`user.role` is `student` or `admin`)
- `GET /api/auth/me` — requires `Authorization: Bearer <token>`

**Student enrollment journey** (all require a student's Bearer token)
- `POST /api/enrollments` — `{ programSlug }`, free, idempotent per student+program
- `GET /api/enrollments/me` — list the current student's enrollments
- `GET /api/enrollments/{id}/offer-letter`
- `POST /api/enrollments/{id}/task` — `{ githubLink, linkedinLink }`
- `POST /api/enrollments/{id}/payment/create-order` — flat ₹150, blocked until task is submitted
- `POST /api/enrollments/{id}/payment/verify` — verifies Razorpay's HMAC signature server-side, unlocks the certificate
- `GET /api/enrollments/{id}/certificate` — 403 until unlocked

**Admin** (require an admin Bearer token)
- `GET /api/admin/enrollments?search=&program_slug=&payment_status=`
- `GET /api/admin/analytics` — totals, revenue, completion funnel, per-program counts
- `GET/POST /api/admin/programs`, `PUT/DELETE /api/admin/programs/{slug}` (delete = soft deactivate)

**Public catalog & misc**: `/api/programs`, `/api/testimonials`, `/api/contact`,
`/api/certificate/verify`, `/api/health`.

## Environment Variables

| Variable              | Description                                         |
|------------------------|------------------------------------------------------|
| `PORT`                 | Uvicorn port (default 8000)                          |
| `JWT_SECRET`           | Secret used to sign auth tokens — change in production |
| `CORS_ORIGIN`          | Comma-separated allowed origins, or `*`               |
| `DATABASE_URL`         | SQLAlchemy URL (SQLite by default)                    |
| `RAZORPAY_KEY_ID`      | Razorpay key ID (test or live)                        |
| `RAZORPAY_KEY_SECRET`  | Razorpay key secret                                   |

## Deployment Notes

- GoDaddy shared hosting generally does not run Python ASGI apps — check for a
  Python App feature on your plan, or use Render/Railway/PythonAnywhere/a VPS.
- Production: `gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker`
- Swap SQLite for Postgres/MySQL via `DATABASE_URL` — no model changes needed
  beyond installing the driver.
- **Change the default admin password and JWT_SECRET before deploying anywhere real.**
