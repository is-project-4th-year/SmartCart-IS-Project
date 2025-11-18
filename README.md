# SmartCart

SmartCart is a Flask-based retail analytics assistant that lets merchants upload transaction CSVs, explore AI‑assisted insights, configure spending thresholds, and keep customers informed with OTP‑secured flows. The project is designed for local analysis and **is not deployed to a public environment**.

## Features
- OTP-protected authentication with first-time store setup and profile management
- Dashboard that surfaces KPIs, customer segments, and association-rule driven recommendations
- CSV upload pipeline with validation, context filtering, and historical tracking per user
- Budget threshold configurator to flag low/medium/high spend alerts
- Email service helper with console fallback for development testing
- Modular analytics engine, configurable currency display, and Flask CLI helpers

## Tech Stack
- Python 3.9+
- Flask, Flask-Login, Flask-WTF, SQLAlchemy
- SQLite (development), PostgreSQL compatible in production
- Pandas, NumPy, scikit-learn, mlxtend for analytics
- Bootstrap-based templates served from `app/templates`

## Getting Started (Local Only)
1. **Clone**: `git clone https://github.com/is-project-4th-year/SmartCart-IS-Project.git`
2. **Create virtualenv**:
   ```bash
   cd SmartCart-IS-Project
   python3 -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```
3. **Install dependencies**: `pip install --upgrade pip && pip install -r requirements.txt`
4. **Create uploads folder** (if it does not exist): `mkdir -p uploads`

## Environment Variables
Copy `.env.example` (or create `.env`) and set at least:
```
FLASK_ENV=development
SECRET_KEY=replace-me
DEV_DATABASE_URL=sqlite:///smartcart_dev.db
EMAIL_USER=your-email@example.com
EMAIL_PASSWORD=app-password-or-token
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_ALLOW_CONSOLE=true
GOOGLE_CLIENT_ID=optional-oauth-client
GOOGLE_CLIENT_SECRET=optional-oauth-secret
```
For local testing you can leave OAuth fields blank and rely on console-based OTP emails by keeping `EMAIL_ALLOW_CONSOLE=true`.

## Database Tasks
Run these commands after activating the virtual environment:
```bash
flask --app run.py init-db   # create tables in smartcart_dev.db
# Optional cleanup
flask --app run.py drop-db
```
`instance/smartcart_dev.db` stores the SQLite data. Delete it if you need a clean start.

## Running the App Locally
```bash
flask --app run.py run --debug    # listens on http://127.0.0.1:5001
# or
python run.py
```
Because there is no deployment target, the app must be accessed from your local machine or a LAN tunnel you control.

## Uploading Data
- Accepted format: `.csv`
- Use the “Upload Dataset” form in the dashboard after logging in.
- Files are stored per user under `uploads/` with metadata recorded in the database for analytics replay.

## OTP & Email Notes
- OTP codes are generated per login attempt and stored in the database.
- When `EMAIL_ALLOW_CONSOLE=true`, OTPs are printed to the terminal to simplify development.
- For real SMTP delivery, supply valid `EMAIL_USER`, `EMAIL_PASSWORD`, and related SMTP settings.

## Troubleshooting
- **Push fails / permissions**: ensure your Git credentials are configured; this repository is meant for private local work.
- **Migrations not running**: rerun `flask --app run.py init-db` after deleting `instance/smartcart_dev.db`.
- **Large CSV uploads**: default max file size is 100 MB; adjust `MAX_CONTENT_LENGTH` in `config.py` if needed.

---
This README intentionally focuses on local execution because SmartCart is not deployed to any shared infrastructure. Reach out to the maintainers before publishing data or credentials.
