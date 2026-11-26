# Go-live checklist

Work through this top to bottom. The last step is a script that checks your server's settings
and tells you what is still wrong, so you do not have to trust your own memory.

```bash
cd backend
python -m app.deploy_check          # reads the same .env / environment the server will use
python -m app.deploy_check --smtp   # also tries logging in to the mail server
```

It judges against **production** standards whatever `ENVIRONMENT` says, so on a development
machine it will (correctly) report failures. It exits with code 1 if anything FAILs.

---

## 0. Decisions to make first

| Decision | Recommendation |
|---|---|
| Where the **API** runs | Any host that runs Python 3.12 and keeps a process alive (a VPS, Render, Railway, Azure App Service...). The frontend host (GoDaddy shared hosting) cannot run it. |
| **Database** | PostgreSQL (or MySQL). SQLite is a single file: fine for a demo, not for production. |
| Where **uploaded images** live | A persistent disk or volume. See section 2 (Uploads). |
| **Domain layout** | Site on `neuintern.in`, API on `api.neuintern.in`. Same parent domain keeps cookies simple (section 7). |
| **Email** | An SMTP mailbox on your own domain (Zoho, Google Workspace, etc.). |
| **Backups** | Decide now who backs up the database and the uploads folder, and how often (section 9). |

## 1. Rotate every credential that was ever committed

The old `.env.example` in git **history** contained real secrets (Razorpay test keys, the SMTP
password, the database password). Cleaning the file does not remove them from history, so
treat them as public:

- [ ] New SMTP password (and confirm the old one no longer works)
- [ ] New database password / a new database user
- [ ] New Razorpay keys (you need the **live** keys for production anyway, section 4)
- [ ] A fresh `JWT_SECRET` (never reuse the dev one)
- [ ] Never commit a real `.env` again (`backend/.env` and `frontend/.env` are git-ignored; check `git status` before every commit)

## 2. Backend setup

```bash
python3.12 -m venv venv && source venv/bin/activate     # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env     # then fill it in (table below)
```

### Environment variables

Set these in `backend/.env` (or the host's environment). `✔` = must be set for production.

| Variable | | What it is |
|---|---|---|
| `ENVIRONMENT` | ✔ | `production`. Turns on the start-up safety checks and Secure cookies. |
| `JWT_SECRET` | ✔ | 32+ random characters: `python -c "import secrets; print(secrets.token_urlsafe(48))"`. Changing it later logs everyone out **and breaks the unsubscribe links in emails already sent**. |
| `DATABASE_URL` | ✔ | e.g. `postgresql://user:pass@host:5432/neuintern` |
| `CORS_ORIGIN` | ✔ | Your site's exact origin(s), comma-separated: `https://neuintern.in`. Never `*`. |
| `FRONTEND_URL` | ✔ | `https://neuintern.in`. Used for links inside emails. |
| `API_PUBLIC_URL` | ✔ | `https://api.neuintern.in`. Used for uploaded-image links and the one-click unsubscribe header. |
| `ADMIN_PASSWORD` | ✔ | Password for the first admin account (`info@neuintern.in`), created at first start. Without it, no admin exists in production. |
| `RAZORPAY_KEY_ID` / `RAZORPAY_KEY_SECRET` | ✔ | **Live** keys (`rzp_live_...`). |
| `RAZORPAY_WEBHOOK_SECRET` | ✔ | The secret you choose in the Razorpay webhook (section 4). |
| `SMTP_HOST` `SMTP_PORT` `SMTP_USER` `SMTP_PASSWORD` | ✔ | Without these, emails are only printed to the server log and nobody receives them. |
| `SMTP_FROM` | | Default `NeuIntern <contact@neuintern.in>`. |
| `CONTACT_NOTIFY_EMAIL` | | Where contact-form messages are sent. |
| `UPLOAD_DIR` | | Where admin-uploaded images are stored. Use an **absolute path on a persistent disk** (section 2, Uploads). |
| `COOKIE_SAMESITE` | | `lax` (default). Set `none` only if the site and API are on **different** domains. |
| `COOKIE_DOMAIN` | | Leave empty, or `.neuintern.in` to share the cookie across subdomains. |
| `SCHEDULER_ENABLED` | | `true` (default). Runs certificate unlocks, email retries and reminders. Safe with several workers. |
| `REMINDERS_ENABLED` | | `false` (default). Turn on after the dry run in section 10. |
| `RATE_LIMIT_ENABLED` | | Leave on. Production refuses to start with it off. |
| `JWT_EXPIRES_MINUTES` | | Session length, default 10080 (7 days). |
| `MAX_UPLOAD_MB` | | Image size limit, default 3. |
| `COOKIE_SECURE` | | Leave unset. Production refuses to start if it is false. |

### Database

- **New, empty database:** `alembic upgrade head`
- **A database that already has the tables** (created before migrations existed):
  1. **Back it up first.**
  2. Make sure its schema matches the models (compare with a fresh `alembic upgrade head` on a scratch copy).
  3. `alembic stamp 0001` to mark it as already at the baseline, then `alembic upgrade head`.
- Every later release: back up, then `alembic upgrade head` **before** restarting the app. The app no longer creates tables itself.

### Running the server

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2 --proxy-headers
```

- Put **nginx or Caddy in front with HTTPS** and proxy to it. `--proxy-headers` makes rate limits
  and the sessions list see each visitor's real IP instead of the proxy's.
- Run it under a process manager (systemd, Docker restart policy) so it restarts after a crash.
- Several workers are safe: background jobs take a database lock so each runs once, and
  certificate unlocking is atomic.

### Uploads

Admin-uploaded program images are written to `UPLOAD_DIR` and served at `/uploads`. If that
folder is inside the application directory, many hosts **wipe it on every redeploy** and the
images disappear. Point `UPLOAD_DIR` at a persistent volume, and include it in your backups.
(If you would rather use S3/R2, that is not built yet: it is a small, separate piece of work.)

## 3. Frontend build and hosting

- [ ] Create `frontend/.env.production` containing `VITE_API_BASE_URL=https://api.neuintern.in/api`
      (it is git-ignored, so create it on the machine that builds). A production build **refuses to run**
      if that address is missing, `localhost`, or not `https://`, so you cannot ship a site that calls the wrong API.
      For local development, copy `frontend/.env.example` to `frontend/.env` (also git-ignored).
- [ ] The API must be on a **subdomain of your own domain** (for example `api.neuintern.in`, a DNS record at GoDaddy
      pointing at wherever the API runs). On an unrelated address the login cookie is treated as third-party and
      login breaks in Safari and increasingly in Chrome.
- [ ] `cd frontend && npm ci && npm run build`
- [ ] Upload the contents of `frontend/dist/` to the web root (GoDaddy `public_html`). The
      `.htaccess` from `public/` is included in `dist/` and handles SPA routing and the www → non-www redirect.
- [ ] `public/sitemap.xml` is hand-written: add any programs you create in the admin portal.

## 4. Razorpay

- [ ] KYC complete and **live** keys generated.
- [ ] Dashboard → Settings → Webhooks → Add: URL `https://api.neuintern.in/api/payments/webhook`,
      events **`payment.captured`** and **`order.paid`**, and a secret you choose (put the same value in `RAZORPAY_WEBHOOK_SECRET`).
- [ ] Do one real payment of the actual fee end to end (section 8), then refund it from the Razorpay dashboard.

Why the webhook matters: if a student pays and closes the tab before our site confirms it, only
the webhook tells us the money arrived.

## 5. Email

- [ ] SMTP settings filled in; `python -m app.deploy_check --smtp` shows a successful login.
- [ ] DNS for your sending domain has **SPF, DKIM and DMARC** records (your mail provider shows the exact values). Without them, receipts and certificates often land in spam.
- [ ] Submit the contact form on the live site: the message shows under Admin → Messages and the two emails show **Sent** under Admin → Emails.

## 6. Admin account and settings

- [ ] Log in as the admin with `ADMIN_PASSWORD`; confirm the default `Admin@123` no longer works.
- [ ] Admin → Invoice: company name, address, **GSTIN**, GST rate and wording are correct. Use *Preview PDF*.
- [ ] Admin → Courses: every program's fee, image, category and active status are right.

## 7. Domains and cookies

- Site and API on subdomains of one domain: nothing to change (default `SameSite=lax`).
- Different domains (for example the API on `*.azurewebsites.net`): set `COOKIE_SAMESITE=none`
  (cookies are Secure in production, which `none` requires). The checker warns about this.
- `CORS_ORIGIN` must match the address bar of the live site exactly (scheme + host, no trailing slash).

## 8. Verify before announcing (about 20 minutes)

Run the checker first: `python -m app.deploy_check --smtp` → fix every FAIL, read every WARN.

Then on the **live** site:

- [ ] `https://api.neuintern.in/api/health` answers `{"success": true ...}`
- [ ] Register a new account with a real email: the verification code arrives by email
- [ ] Enroll in a program: the offer letter email arrives with a PDF
- [ ] Submit the task, pay the real fee: Razorpay checkout opens, payment succeeds, the dashboard moves to "waiting", the invoice email arrives, and the amount and company details on the PDF are right
- [ ] Admin → Payments shows it; Admin → Emails shows everything **Sent**
- [ ] Log out and back in; log in on a phone and use *Your devices* → *Log out* on one of them
- [ ] Forgot password works end to end
- [ ] The unsubscribe link in a reminder email opens the page and works (after section 10)
- [ ] Certificates unlock only after the 28-day course ends: test this on a staging copy by moving an enrollment's date back, not on live data

## 9. Backups and watching it run

- [ ] **Database backup** on a schedule (for PostgreSQL, a nightly `pg_dump`), stored off the server, with one restore tried.
- [ ] **Uploads folder** backed up too.
- [ ] Something pings `/api/health` and alerts you when it stops answering.
- [ ] Check **Admin → Emails** now and then: *Failed* means an invoice, certificate or offer letter did not reach someone. Fix the cause (usually SMTP) and press *Retry now*.
- [ ] Re-run `python -m app.deploy_check` after every deploy.

## 10. Turn on reminder emails (optional)

They nudge students who enrolled but have not paid. They are off by default so a deploy never emails people by surprise.

1. Run `POST /api/admin/reminders/send?dryRun=true` (as an admin) to see how many students would be emailed.
2. If the number looks right, set `REMINDERS_ENABLED=true` and restart. Each reminder includes an unsubscribe link.

## 11. Rolling back

- Keep the previous release's files, and **back up the database before every upgrade**.
- Code-only problem: redeploy the previous release (migrations are additive, so older code keeps working with a newer schema in the common case).
- Schema problem: `alembic downgrade -1` steps back one migration, but dropped columns lose their data, so restoring the backup is the safer rollback.

## 12. Known limits (so nothing surprises you)

- Login codes (OTP) emails are sent from memory, not the durable email queue; if the server restarts at that moment, the user just asks for another code.
- Sessions from before the device-session feature have no server record and live until they expire (7 days at most); *Log out of all devices* and a password reset still cut them off.
- Invoices split GST as CGST + SGST only (no IGST for out-of-state customers).
- `sitemap.xml` is static; uploaded images live on the API server's disk (section 2).
- Free-tier hosts that sleep or wipe their disk are not suitable for the database or uploads.
