# ANPR REST API

Python backend for the ANPR dashboard. Connects to MongoDB and serves detected plates and stats.

## Setup

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Optional: copy `.env.example` to `.env` and set `MONGODB_URI`, `ANPR_DB_NAME`, `ANPR_CAMERAS`, `ANPR_SITES`.

## Run

```bash
python app.py
```

- Dashboard: http://localhost:5000/
- API: http://localhost:5000/api/stats and http://localhost:5000/api/plates

## API

| Endpoint | Description |
|----------|-------------|
| `GET /api/stats` | Dashboard stats (total, today, week, cameras, sites) |
| `GET /api/plates?page=1&limit=25&sort=date-desc` | Paginated plates (sort: `date-desc`, `date-asc`, `plate`, `site`) |
| `GET /api/plates/<id>` | Single plate with base64 image |
| `GET /api/plates/<id>/image/img` | Plate image as JPEG (for `<img>` src) |

Database: **ANPR**, collection: **detected_plates**.
