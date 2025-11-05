# Repository Guidelines

## Project Structure & Module Organization
- `app.py` boots Flask by calling `app.create_app`; use it for local entry points.
- Application code lives under `app/`: `api/` for REST endpoints, `views/` for page blueprints, payment clients in `CreemPay.py` and `alifacepay/`, media helpers in `OpenAI.py`, `GeminiAPI.py`, `attachment_processor.py`, and SQLite utilities in `DB/SqlLiteUtil.py`.
- Assets sit in `app/templates/` and `app/static/`; upload staging (`uploads/`, `subtitles/`, `audio_debug/`) and schema primers (`sqlscript/`) support media and billing flows.
- Place new pytest modules in `tests/` and mirror blueprint-specific fixtures next to the feature under test.

## Build, Test, and Development Commands
- `py -3.12 -m venv .myenv` then `. .\Scripts\activate` creates the expected Windows virtualenv.
- `Get-Content requirements.txt | Out-File -Encoding utf8 requirements-utf8.txt` prevents encoding errors; follow with `pip install -r requirements-utf8.txt`.
- `flask --app app:create_app run --debug` (or `python app.py`) starts the dev server with all blueprints registered.
- `sqlite3 OpenAI.db < sqlscript\user.sql` seeds the schema before payment or attachment flows.

## Coding Style & Naming Conventions
- Follow PEP 8 with 4-space indentation, `snake_case` functions, `PascalCase` classes, and upper-case config constants.
- Add type hints for new public helpers in `app/*.py`, keep blueprints thin, and route heavy logic to utilities.
- Prefer configured loggers from `app/__init__.py`; avoid `print`.

## Testing Guidelines
- Use `pytest` with `flask.testing.FlaskClient`; run `pytest` before submitting.
- Name tests after their feature (`test_openai_streaming.py`, `test_attachment_uploads.py`) and cover failure paths.
- Document any manual smoke checks (e.g., `curl http://127.0.0.1:5000/api/chat`) in your PR description.

## Commit & Pull Request Guidelines
- Write imperative commit subjects mirroring history (`Add rate limit guard`, `Update README for Redis path`) and keep scope focused.
- PRs should summarize code changes, note schema/config updates, link issues, and include UI screenshots when relevant.
- Surface new environment variables in `.env.example` and explain rollout steps.

## Security & Configuration Tips
- Store secrets only in `.env`; never commit production keys.
- Align rate-limiter and billing changes across `app/api/allAPI.py` and `UserUtils.py`.
- Scrub sensitive payloads from `logs/` before sharing diagnostics outside the team.
