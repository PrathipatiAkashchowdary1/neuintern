# NeuIntern — React + FastAPI + Razorpay + Student/Admin Dashboards

```
frontend/   React + Vite site — public pages, auth, student dashboard, admin dashboard
backend/    FastAPI API — auth, enrollments, payments, admin
```

## What this includes

**Public site**: Home, About, Programs (search/filter), Program Details, Certificate
lookup, Reviews, Contact, legal pages — unchanged from earlier versions.

**Student flow** (all behind login):
1. **Register** — full name, email, phone, degree, branch, current year, password
2. **Log in** — email + password
3. **Enroll** in any program from its detail page (free)
4. **Offer letter** — available immediately after enrolling, printable
5. **Task submission** — GitHub repo link + LinkedIn profile link
6. **Certificate fee** — flat ₹150 via Razorpay, only unlocked after the task step
7. **Certificate** — printable, unlocked once payment is verified
8. **Dashboard** (`/dashboard`) — shows a step tracker through all of the above, plus the
   student's profile info and (if enrolled in more than one program) a switcher between them

**Admin flow**:
- Log in with the seeded admin account (see below) — you're routed to `/admin`
  automatically instead of the student dashboard
- **Analytics tab** — total students, total enrollments, total revenue, a completion
  funnel chart (enrolled → task submitted → paid → certified), and enrollments-by-program
- **Students & Payments tab** — every enrollment with the student's profile (degree,
  branch, year), task links, payment status/amount, and certificate status
- **Manage Programs tab** — edit any program's title/category/price/tagline/active status,
  or add a brand new program, all reflected live in the public catalog

## Default admin login

```
Email:    admin@neuintern.com
Password: Admin@123
```

**Change this password immediately in any real deployment** — it's seeded automatically
on first backend startup in `backend/app/db/seed.py`.

## 1. Run the backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
.\venv\Scripts\Activate.ps1 -> # when runing the powershell to create virtual env easy 
pip install -r requirements.txt
cp .env.example .env
```

Edit `backend/.env` — at minimum set `JWT_SECRET`, and add Razorpay test keys from the
[Razorpay Dashboard](https://dashboard.razorpay.com/app/keys) (Test Mode on) to actually
process the ₹150 certificate payment:

```
JWT_SECRET=some-long-random-string
CORS_ORIGIN=http://localhost:5173
RAZORPAY_KEY_ID=rzp_test_xxxxxxxxxxxx
RAZORPAY_KEY_SECRET=xxxxxxxxxxxxxxxxxxxx
```

```bash
uvicorn app.main:app --reload --port 8000
```

A `neuintern.db` SQLite file is created and seeded (programs, sample certificates, the
admin account) automatically on first run. Docs: `http://localhost:8000/docs`.

## 2. Run the frontend

```bash
cd frontend
npm install
cp .env.example .env
```

Edit `frontend/.env`:
```
VITE_API_BASE_URL=http://localhost:8000/api
```

```bash
npm run dev
```

Visit `http://localhost:5173`.

## 3. Try the full student journey

1. Go to `/register`, create an account.
2. Open any program's detail page → **Enroll Now** (free, no payment yet).
3. You'll land on `/dashboard` — your offer letter is already there, printable.
4. Submit your GitHub + LinkedIn links in the Task Completion card.
5. **Pay ₹150** — Razorpay Checkout opens. In test mode, use Razorpay's published
   [test card/UPI details](https://razorpay.com/docs/payments/payments/test-card-upi-details/)
   (e.g. card `4111 1111 1111 1111`, any future expiry/CVV) — nothing is actually charged.
6. On success, your certificate appears immediately, also printable.
7. Log out, log back in as `admin@neuintern.com` — you'll land on `/admin` and see this
   student's enrollment, task links, and paid ₹150 in both the table and the analytics.

## 4. What's already verified

Before packaging, the entire flow was tested from this environment end-to-end:
- Register → login → enroll → offer letter → task submission → payment blocked before
  task (confirmed 400) → payment (verified via a real HMAC-SHA256 signature check,
  same algorithm Razorpay uses) → certificate unlock → certificate visible to the
  student → same enrollment visible to admin with correct profile/payment/task data →
  admin analytics numbers match
- Admin-only routes correctly reject a student token (403)
- Program CRUD: created, edited, and deactivated a program as admin; confirmed the
  public catalog reflected each change immediately
- Frontend production build succeeds; every route (`/`, `/login`, `/register`,
  `/dashboard`, `/admin`, program pages) returns clean 200s with both servers running
  together

Razorpay's actual `order.create()` call was confirmed to reach `api.razorpay.com`
correctly — it only fails in this sandbox because outbound internet is restricted here.
With real keys and normal internet access (any real deployment), it completes normally.

## 5. Design notes

The color palette was restyled toward a "vivid" violet → magenta → cyan direction,
inspired by the name and spirit of vividone.in. I wasn't able to extract that site's
exact hex values through my available tools (page-content fetching strips CSS), so this
is an interpretation, not a pixel-for-pixel match — send exact colors or a screenshot if
you want it dialed in closer.

## 6. Known gaps / next steps

- **Email notifications** aren't wired up (e.g. "your certificate is ready") — the
  contact form and payment flows work, but nothing sends actual email yet.
- **Offer letter / certificate "PDF"** currently uses the browser's native print-to-PDF
  (a styled, print-ready page) rather than a server-generated PDF file. Good enough for
  most uses; say the word if you want a true generated PDF attachment instead.
- **One enrollment per program per student** — re-enrolling in the same program returns
  the existing enrollment rather than creating a duplicate.
- See each folder's own README for stack details and deployment notes (GoDaddy shared
  hosting will not run either backend directly — see those READMEs for options).
