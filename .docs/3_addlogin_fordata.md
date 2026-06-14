# Add Login Gate For Dashboard

## Current state

Landing page `/frontend/` is public and already contains a direct `Dashboard` link to `/frontend/dashboard_sand.html`.
The dashboard HTML and dashboard proxy APIs were also public, so hiding the link alone would not protect direct access to the data.

The billing app example uses a simple session login:

- `GET /login` renders a username/password form.
- `POST /login` checks `APP_USER` and `APP_PASS`.
- A successful login stores `request.session["user"] = {"name": username}`.
- Protected pages check `request.session.get("user")`.

## Fix approach

- Add Starlette `SessionMiddleware` to the landing page backend.
- Add environment-based credentials and session secret:
  - `APP_USER`
  - `APP_PASS`
  - `SESSION_SECRET`
- Add auth routes:
  - `GET /login`
  - `POST /login`
  - `GET /logout`
  - `GET /api/auth/me`
- Keep `/frontend/` public.
- Hide the landing page `Dashboard` button by default and show it only when `/api/auth/me` returns `authenticated: true`.
- Add a visible `Login` button for anonymous users and a `Logout` button for authenticated users.
- Protect direct dashboard access by adding an exact backend route for `/frontend/dashboard_sand.html` before the static file mount.
- Protect dashboard data by checking the same session in:
  - `/api/dashboard/saletax_summary`
  - `/api/dashboard/saletax_list`
- Keep existing dashboard API URLs unchanged; only session access is added.

## Expected behavior

- Anonymous visitors can still open `/frontend/`.
- Anonymous visitors see `Login` but do not see `Dashboard`.
- Opening `/frontend/dashboard_sand.html` directly without login redirects to `/login?next=/frontend/dashboard_sand.html`.
- Logging in with valid credentials redirects to the requested `next` path.
- Authenticated users see `Dashboard` and can load dashboard data.
- Logging out clears the session and hides `Dashboard` again.
- Dashboard API calls without session return `401`.

## Files changed

- `backend/main.py`
  - Session middleware, auth routes, dashboard page guard, dashboard API guards.
- `backend/config.py`
  - `APP_USER`, `APP_PASS`, `SESSION_SECRET` settings.
- `frontend/login.html`
  - Login form based on the billing app pattern.
- `frontend/index.html`
  - Dashboard/Login/Logout navbar controls.
- `frontend/app.js`
  - Auth status check and navbar state update.
- `frontend/styles.css`
  - Login/logout button styling and hidden-state support.
- `.env.example`
  - Auth environment variable examples.
- `requirements.txt`
  - Session/form parsing dependencies.

## Verification

1. Run Python syntax check:
   `python -m py_compile backend/main.py backend/config.py`
2. Run JavaScript syntax checks for:
   - `frontend/app.js`
   - inline JavaScript in `frontend/login.html`
   - inline JavaScript in `frontend/dashboard_sand.html`
3. Open `/frontend/` without login and confirm `Dashboard` is hidden.
4. Open `/frontend/dashboard_sand.html` without login and confirm redirect to `/login?next=/frontend/dashboard_sand.html`.
5. Login with `APP_USER` and `APP_PASS`; confirm redirect to `next`.
6. Confirm authenticated `/frontend/` shows `Dashboard`.
7. Confirm dashboard data loads normally after login.
8. Confirm dashboard API calls without session return `401`.
9. Confirm logout clears the session and hides `Dashboard`.

## Assumptions

- This is a lightweight internal dashboard gate, not a full user-management system.
- Credentials are managed through environment variables, not a database table.
- The dashboard data is internal enough to protect both the page and proxy APIs.
- Session lifetime follows the billing app example: 2 hours.
