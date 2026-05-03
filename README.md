# Astrology GPT Django Starter

This is a Django-first MVP for the astrology website described in `How to do.docx`.

## What is included

- SQLite by default for local development
- PostgreSQL-ready settings through `DATABASE_URL`
- Apps for accounts, charts, chat, and payments
- Starter models for plans, profiles, saved charts, conversations, messages, and payment events
- Simple Django template pages with no React build step

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python manage.py migrate
python manage.py runserver
```

If Python's `venv` fails because of local `ensurepip` permissions, install Python 3.12 or 3.13 from python.org and create the venv with that version. Django and astrology packages are typically better tested on 3.12/3.13 than brand-new Python 3.14.

## SQLite now, PostgreSQL later

For the MVP, leave `DATABASE_URL` empty and Django will use `db.sqlite3`.

When you deploy or move to PostgreSQL:

```env
DATABASE_URL=postgres://USER:PASSWORD@HOST:5432/DBNAME
```

Then run:

```powershell
python manage.py migrate
```

The app models do not depend on SQLite-specific features, so the move should be straightforward.
