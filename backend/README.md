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
uvicorn app.main:app --reload --port 8000
```

- API: `http://localhost:8000`
- Interactive docs: `http://localhost:8000/docs`

A `neuintern.db` SQLite file is created and seeded automatically on first run:
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
