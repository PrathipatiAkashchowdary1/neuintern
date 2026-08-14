# NeuIntern — 4-Week Internship Programs (Frontend, Phase 1)

A production-ready React + Vite frontend for NeuIntern, an internship platform offering
focused 4-week programs. This is Phase 1 (frontend only) — the architecture is designed
so a backend (Node.js, FastAPI, Laravel, or PHP) can be plugged in later without touching
components.

## Tech Stack

React 19 (Vite) · React Router DOM · Tailwind CSS · Framer Motion · React Helmet Async ·
React Hook Form · Axios · Swiper.js · React Icons · AOS

## Getting Started

```bash
npm install
npm run dev       # start local dev server
npm run build     # production build → dist/
npm run preview   # preview the production build locally
```

## Project Structure

```
src/
  api/          Service layer (programs, contact, certificate, auth) — mock data now,
                swap for real HTTP calls in Phase 2 without changing any component.
  components/   Reusable UI: layout (Navbar/Footer), common (Loader, FAQ, CTA, etc.),
                home/ and programs/ specific pieces.
  data/         Mock content: 16 programs, testimonials, FAQs.
  hooks/        useScrollToTop, useCountUp.
  layouts/      MainLayout (Navbar + Outlet + Footer + BackToTop).
  pages/        Route-level pages, including pages/legal/ for policy pages.
  routes/       AppRoutes.jsx — lazy-loaded route definitions.
  seo/          Seo.jsx (Helmet wrapper) + schema.js (JSON-LD builders).
  utils/        Small helpers (cn.js classnames combinator).
```

## Backend Integration (Phase 2)

1. Set `VITE_API_BASE_URL` in a `.env` file (see `.env.example`).
2. In `src/api/*.js`, replace the mock `delay()`/resolved-promise bodies with real
   `apiClient` calls (the axios instance in `src/api/axios.js` already attaches an
   `Authorization` header from `localStorage` if a token is present).
3. No component changes are required — pages already treat these functions as promises.

## Deploying to GoDaddy Shared Hosting

1. Run `npm run build`. This generates a `dist/` folder with relative asset paths
   (`base: './'` in `vite.config.js`), so it works from any subdirectory.
2. Upload the **contents** of `dist/` (not the folder itself) to your hosting root,
   typically `public_html/`, or a subfolder if NeuIntern lives at a path like
   `yourdomain.com/neuintern`.
3. Confirm `.htaccess` (already included in `dist/`) is present at the same level as
   `index.html`. It handles:
   - SPA fallback routing so refreshing `/programs/react-development` doesn't 404
   - Gzip compression and long-lived caching for static assets
   - Basic security headers
4. If GoDaddy hides dotfiles in its file manager, enable "show hidden files" or upload
   `.htaccess` via FTP/SFTP to make sure it transfers.
5. Point your domain's DNS to the hosting account per GoDaddy's standard instructions,
   then visit the site — no server-side config beyond `.htaccess` is required for
   Phase 1.

## SEO

- `public/sitemap.xml` lists all static pages and all 16 program detail pages.
- `public/robots.txt` references the sitemap.
- Every route sets title, meta description, canonical URL, Open Graph/Twitter tags, and
  JSON-LD (Organization, Website, Breadcrumb, Course) via `src/seo/Seo.jsx`.
- Update `SITE_URL` in `src/seo/Seo.jsx` and the sitemap once the real domain is live.

## Notes

- Program images currently come from Unsplash placeholders — replace with real
  photography before launch.
- The "Apply Now" buttons on program pages link to a placeholder Google Form URL;
  update `href="https://forms.gle/"` in `src/pages/ProgramDetails.jsx`.
- Certificate verification, dashboards, login, and other Phase 2 features have
  placeholder service functions in `src/api/` ready to be wired up.
