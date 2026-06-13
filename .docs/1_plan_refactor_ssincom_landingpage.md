# Refactor S&S Incom Landing Page To FastAPI + Railway Deployment

## Summary
- Split the current single-file landing page into `frontend/index.html`, `frontend/styles.css`, and `frontend/app.js`.
- Add a FastAPI backend that serves the frontend and provides contact-form APIs.
- Load contact form product/application options from PostgreSQL table `quotation.pdgroup`.
- Save submitted contact requests to `quotation.contact_customer`.
- Send notification email to `contact@ssincom.com` and `mailtossincom@gmail.com` after a successful database insert.
- Deploy as a single Railway service using Railway Variables for database and SMTP configuration.

## Key Changes
- Frontend:
  - Move embedded CSS from `<style>` into `frontend/styles.css`.
  - Move embedded JavaScript from `<script>` into `frontend/app.js`.
  - Replace inline contact form submit behavior with `fetch()` to `POST /api/contact`.
  - Populate the product/application select from `GET /api/pdgroups`.
  - Preserve the current landing page layout, language toggle, and product tab behavior.

- Backend:
  - Create a FastAPI app under `backend/`.
  - Add `GET /api/pdgroups` to return `pdgroup_id` and `pdgroup_name`.
  - Add `POST /api/contact` to validate input, optionally validate `pdgroup_id`, insert the contact record, and trigger SMTP email.
  - If the database insert succeeds but email sending fails, return success to the user and log the email error.

- Config and deployment:
  - Use `DATABASE_URL` from Railway Variables in production.
  - Use SMTP Railway Variables for email settings.
  - Commit `.env.example`, not `.env`; `.env` is only for local development.
  - Start Railway with `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`.
  - Set `CONTACT_MAIL_RECIPIENTS=contact@ssincom.com,mailtossincom@gmail.com` on Railway.

## Validation Rules
- `person_name` and `tel` are required.
- `pdgroup_id` is optional.
- If `pdgroup_id` is provided, it must exist in `quotation.pdgroup`.
- Secrets must not be hardcoded in source code.

## Test Plan
- Verify the frontend is served by FastAPI at `/`.
- Verify `GET /api/pdgroups` returns database-backed options.
- Submit a valid contact form and confirm a row is inserted into `quotation.contact_customer`.
- Confirm the notification email is sent to both configured recipients.
- Simulate SMTP failure after database insert and confirm the frontend still shows success while the backend logs the error.
- Run Python syntax checks and JavaScript syntax checks.
- On Railway, verify `/api/health`, `/api/pdgroups`, contact form submission, inserted database row, and delivered notification email using the real Railway Variables.

## Assumptions
- The app will be deployed as one FastAPI service that serves both frontend static files and API routes.
- `DATABASE_URL` will be supplied through Railway Variables in production.
- SMTP credentials will be supplied through Railway Variables in production.
- `.env` will be ignored by git and `.env.example` will document required keys.
