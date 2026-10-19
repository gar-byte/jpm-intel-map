# jpm-intel-map

JPM Companies, LLC — jpm-intel-map Prototype

This repository contains a minimal prototype of a worldwide real-time intelligence map. The prototype ingests public real-time signals (USGS earthquakes and a news RSS), extracts minimal event fields, stores them in Postgres+PostGIS, and exposes a REST API and WebSocket for a simple map frontend.

Quickstart (requires Docker & docker-compose)

1. Clone the repo
   git clone https://github.com/gar-byte/jpm-intel-map.git
   cd jpm-intel-map

2. Start services
   docker-compose up --build

3. Open the frontend
   Visit http://localhost:8000 in your browser. The map will show recent events and receive live updates.

Notes
- Attribution: JPM Companies, LLC — jpm-intel-map Prototype
- Map tiles use OpenStreetMap (no API keys required)
- No secrets are committed. To change the database URL, set DATABASE_URL in the docker-compose environment or a .env file.

Architecture
- single backend (FastAPI) that serves static frontend files, provides REST + WebSocket endpoints, and runs background ingest workers.
- Postgres+PostGIS for spatial storage (the prototype uses a plain Postgres image; for full PostGIS features swap to postgis/postgis image if needed).

Files of interest
- backend/app/main.py — FastAPI app, endpoints, WS, startup tasks
- backend/app/ingest.py — simple ingest workers for USGS and an example RSS
- backend/app/models.py — DB helper functions
- backend/Dockerfile, docker-compose.yml — run everything locally

License
MIT — JPM Companies, LLC
