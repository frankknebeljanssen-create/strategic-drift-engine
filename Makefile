# Bequeme Kommandos rund um Docker Compose. Variablen ueber .env.
# MODE steuert den Klassifikator: mock (Standard) oder claude.
MODE ?= mock

.PHONY: up down db ingest analyze psql logs build

# Startet DB und Backend im Hintergrund.
up:
	docker compose up -d --build

down:
	docker compose down

build:
	docker compose build

# Wartet, bis Postgres bereit ist (Migration laeuft beim ersten Init automatisch).
db:
	docker compose up -d db

# Normalisiert synthetic_data in die Datenbank.
ingest:
	docker compose run --rm backend python -m scripts.ingest

# Fuehrt die vier Agenten aus und schreibt den Frontend-Dump.
# (scripts/analyze.py folgt zusammen mit den Agenten.)
analyze:
	docker compose run --rm backend python -m scripts.analyze --mode $(MODE) --dump docs/drift_data.json

# Interaktive psql-Shell in der DB.
psql:
	docker compose exec db psql -U $${POSTGRES_USER:-drift} -d $${POSTGRES_DB:-drift}

logs:
	docker compose logs -f backend
