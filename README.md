# AIChatRobot

## Project Overview
AIChatRobot is a Flask-based multimodal AI assistant and membership billing platform. It combines models from OpenAI, DeepSeek, and Google Gemini to provide text chat, image generation, text-to-speech, subtitle extraction, and related workflows. Alipay and bank card top-ups are supported alongside attachment management, email notifications, and usage accounting. SQLite tracks account activity, Redis handles caching and throttling, and Cloudflare R2 stores attachments and subtitle files.

## Feature Highlights
- **Multi-model chat**: Integrates OpenAI Chat Completions and DeepSeek with optional streaming responses, context caching, and token accounting (`app/OpenAI.py`).
- **Multimedia tools**: Offers DALL·E image generation, Gemini TTS, Whisper subtitle transcription, and detailed usage logging (`app/GeminiAPI.py`, `app/subtitle_extractor.py`).
- **Attachment pipeline**: `AttachmentProcessor` extracts text, uploads files to Cloudflare R2, and supports OCR for PDF, DOCX, Excel, and image formats (`app/attachment_processor.py`, `app/r2_storage.py`).
- **Account system**: Registration, login, password reset, and account activation with Cloudflare Turnstile protection and email notifications (`app/api/userAPI.py`, `app/SendMail.py`).
- **Top-up and billing**: Integrates Alipay Face-to-Face Pay and Creem card acquiring (with Redis caching) while recording every transaction (`app/alifacepay/app.py`, `app/CreemPay.py`, `app/payUtils.py`).
- **Risk control and throttling**: Flask-Limiter provides per-IP and per-user rate limits; Redis caches balances and attachment contents.
- **Template site**: `templates/` includes chat, image, TTS, subtitle, and pricing pages available through routes such as `chat`, `image`, `tts`, `subtitle`, and `pricing`.

## Tech Stack
- Python 3.11/3.12 (`restartService.sh` assumes a pyenv-based 3.12 environment)
- Flask, Flask-RESTX, Flask-Cors, Flask-Limiter, Flask-JWT-Extended
- Redis for caching and rate-limiting state
- SQLite accessed via `app/DB/SqlLiteUtil.py`
- OpenAI, Google Gemini, DeepSeek, Creem API, and Alipay Face-to-Face Pay
- Cloudflare R2 (S3 compatible) for storing attachments and subtitles
- Optional tooling: ffmpeg, pytesseract, PyPDF2, python-docx, openpyxl, and other media utilities

## Project Structure
```
├── app.py                  # Flask application entrypoint
├── app/
│   ├── __init__.py         # create_app, logging, limiter, service wiring
│   ├── OpenAI.py           # OpenAI/DeepSeek chat, image, streaming handlers
│   ├── GeminiAPI.py        # Gemini TTS and media processing
│   ├── subtitle_extractor.py  # Whisper subtitles plus R2 upload helpers
│   ├── attachment_processor.py # Attachment validation, OCR, storage
│   ├── r2_storage.py       # Cloudflare R2 wrapper
│   ├── CreemPay.py         # Card payment workflow
│   ├── alifacepay/         # Alipay Face-to-Face Pay integration
│   ├── views/              # Page routes (chat/image/tts/subtitle/...)
│   ├── api/                # REST APIs for chat, attachments, users
│   ├── DB/SqlLiteUtil.py   # SQLite DAO utility
│   ├── templates/          # Jinja2 templates
│   └── static/             # Static assets
├── requirements.txt        # Dependency list (UTF-16 LE encoded)
├── sqlscript/              # Database initialization scripts
└── restartService.sh       # Gunicorn restart script
```

## Before You Start
- **Python**: Use Python 3.11 or later (production script runs `pyenv shell myenv3.12`).
- **System dependencies**: Install `ffmpeg`, `tesseract-ocr`, `libreoffice`, and other tools as required for subtitle and document processing.
- **Database**: SQLite is used by default; configure `DB_PATH` for the actual file location (for example `./app/DB/OpenAI.db`).
- **Redis**: Expects `localhost:6379` by default to support caching and rate limiting.
- **Cloudflare R2**: Requires account ID, access key, secret, and bucket.
- **External APIs**: Prepare credentials for OpenAI, DeepSeek, Google (Gemini + Cloud TTS + Generative Language), Creem, Alipay Face-to-Face Pay, and SMTP.

## Environment Variables
Create a `.env` file in the project root and populate the following values:

| Variable | Description |
| --- | --- |
| `OPENAI_API_KEY`, `DS_API_KEY` | API keys for OpenAI Chat Completions and DeepSeek. |
| `GOOGLE_API_KEY` | Google Gemini / Generative AI API key. |
| `DB_PATH` | SQLite file path, for example `./app/DB/OpenAI.db`. |
| `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB` | Redis connection settings. |
| `TURNSTILE_SITE_KEY`, `TURNSTILE_SECRET_KEY` | Cloudflare Turnstile credentials. |
| `PRODUCTION_APPID`, `PRODUCTION_KEY_PATH` | Alipay Face-to-Face Pay App ID and private key directory (`SANDBOX_*` for sandbox). |
| `CREEM_ENVIRONMENT` | `sandbox` or `production`. |
| `CREEM_SANDBOX_API_KEY`, etc. | Creem API keys and webhook secrets. |
| `CLOUDFLARE_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET_NAME` | Cloudflare R2 configuration. |
| `BASE_URL`, `DOMAIN` | Public endpoints used for payment callbacks and email links. |
| `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USERNAME`, `MAIL_PASSWORD` | SMTP settings used by `SendMail`. |
| `EMAIL_PASSWORD` | SMTP password consumed by `SendMail`. |

> Copy `.env.sample` if available; otherwise create the file manually.

## Installation and Deployment
```
# 1. Clone the repository
git clone <repo-url>
cd AIChatRobot

# 2. Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Convert dependency file encoding (requirements.txt is UTF-16 LE)
iconv -f utf-16le -t utf-8 requirements.txt > requirements-utf8.txt
pip install -r requirements-utf8.txt

# 4. Initialize the database
sqlite3 ./app/DB/OpenAI.db < sqlscript/user.sql
sqlite3 ./app/DB/OpenAI.db < sqlscript/history.sql
sqlite3 ./app/DB/OpenAI.db < sqlscript/price.sql
sqlite3 ./app/DB/OpenAI.db < sqlscript/Transaction.sql
sqlite3 ./app/DB/OpenAI.db < sqlscript/barcode.sql

# 5. Launch Redis (example)
redis-server

# 6. Run the development server
export FLASK_APP=app.py
flask run --host=0.0.0.0 --port=5000
```

For production you can reuse `restartService.sh`:
```
bash restartService.sh
```
The script activates the pyenv environment, shuts down existing Gunicorn processes, and starts four workers bound to 0.0.0.0:5000.

## Module Highlights
- **Application factory**: `app/__init__.py` creates the app, sets up logging (under `logs/`), rate limiting, CORS, JWT, payment services, and registers blueprints.
- **Chat and streaming**: `app/OpenAI.py` manages conversation history, calls OpenAI/DeepSeek APIs, and writes chat logs to `chatHistory`.
- **Multimodal services**: `app/imageGeneration.py`, `app/GeminiAPI.py`, and `app/subtitle_extractor.py` handle image generation, TTS, and subtitle extraction, including ffmpeg/Whisper calls and billing records.
- **Attachment workflow**: `app/attachment_processor.py` validates uploads, performs OCR/format parsing, uploads to R2, and caches extracted text in Redis.
- **Payment center**: `app/CreemPay.py`, `app/alifacepay/app.py`, and `app/views/orderCreation.py` coordinate top-ups, product caching in Redis, transaction storage, and QR code generation.
- **User services**: `app/api/userAPI.py` handles login, registration, email verification, Turnstile checks, and Redis caching; `app/SendMail.py` sends email notifications.
- **Subtitle service**: `app/views/subtitle.py` exposes upload, processing, and download endpoints that can write results back to R2.
- **Logging and throttling**: `CustomTimedRotatingFileHandler` writes to `logs/app.log.YYYYMMDD.log`, and Flask-Limiter applies IP and user-level limits.

## Routes and API Reference
- Pages: `/`, `/chat`, `/image`, `/tts`, `/subtitle`, `/pricing`, `/orderPreCreate`, `/payment_method`, and more.
- Core APIs:
  - `POST /api/v1/login`, `POST /register`, `GET /check-login`
  - `POST /api/v1/chat`, `POST /chatStream`
  - `POST /api/v1/image`
  - `POST /api/v1/upload_attachment`, `GET|DELETE /api/v1/get_attachment/<id>`
  - `POST /api/subtitle/upload`, `POST /api/subtitle/process`
  - `GET /query_order`, `GET /payment_success`

Blueprint registration lives in `app/__init__.py` for easy inspection.

## Database Scripts
The `sqlscript/` directory contains:
- `user.sql`: user and account balance tables
- `history.sql`: chat, image, TTS, and transcription history
- `price.sql`: default model pricing
- `Transaction.sql`: usage ledger
- `barcode.sql`: recharge QR codes plus Alipay/bank-card transactions
- `EmailFailure.sql`: records failed email deliveries

Extend or migrate to another database by updating `DB_PATH` and `SqlLiteUtil`.

## Logging and Operations
- Application logs: stored in `logs/` with daily rotation.
- Gunicorn logs: `/root/myai/gunicorn/*.log` (see `restartService.sh`).
- Redis cache keys: `useid:{userid}`, `conversation:{id}`, `attachment:{userid}:{id}`, `creem:product:{env}:{amount}`, and similar.
- Rate limits: see `app/api/allAPI.py` and `app/api/userAPI.py` for `@limiter.limit` settings.

## Troubleshooting
- **Dependency installation fails**: Convert `requirements.txt` to UTF-8 first; install missing system libraries like ffmpeg/tesseract/openjpeg as required.
- **Redis not running**: Login, attachments, and streaming chat rely on Redis; ensure the service is running and `.env` contains the correct host/port.
- **API returns 401/402**: Verify login state, account activation, and balance; negative balances block requests.
- **R2 errors**: Double-check environment variables and ensure the access key has read/write permissions.
- **Email delivery fails**: Inspect the `EmailFailure` table or application logs; confirm SMTP credentials and throttling limits.

## Development Tips
- Start Redis before running `flask run`, and prepare an SQLite database populated with test data.
- Enable DEBUG logging when testing multimedia or attachment features, and consider breakpoints in `app/attachment_processor.py`.
- When adding new models or payment channels, update `sqlscript/price.sql` and the billing logic in `UserUtils`.

## License
No explicit license is provided. All rights reserved unless you obtain permission from the author.
