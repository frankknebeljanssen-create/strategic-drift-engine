# Strategic Drift Engine, Projektkontext für Claude Code

Diese Datei ist der verbindliche Kontext für alle Claude-Code-Sessions in
diesem Repo. Lies sie zuerst und halte dich an die Konventionen.

## Was das ist

Ein Multi-Agenten-System, das die Lücke zwischen formulierter Strategie und
tatsächlichem Organisationsverhalten misst. Vier Agenten analysieren interne
Kommunikation (Slack, Mail, Meeting-Notizen, Kalender), ordnen sie den
strategischen Säulen zu und machen die Abweichung (Drift) über die Zeit
sichtbar. Jede Zahl bleibt bis zur Einzelquelle nachvollziehbar (Audit Trail).
Ausgabe: eine interaktive Heat-Map mit Drill-Down.

## Stack

Python 3.12, FastAPI, SQLAlchemy 2.0, Postgres 16 mit pgvector, LangGraph,
Anthropic API (Claude), Docker Compose. Frontend: eigenständiges HTML/CSS/JS
ohne Build-Schritt (Daten werden als JSON eingebettet).

## Repo-Struktur

```
strategic-drift-engine/
├── docker-compose.yml          # Postgres+pgvector und Backend
├── Makefile                    # up, db, ingest, analyze, psql
├── .env.example                # ANTHROPIC_API_KEY etc.
├── CLAUDE.md                   # diese Datei
├── README.md
├── synthetic_data/             # handgefertigt, LIEGT VOR, nicht neu generieren
│   ├── people.json
│   ├── strategy/techco_strategy_2026.md
│   ├── slack/{leadership,engineering,sales}.json
│   ├── mails/{ceo_mails,leadership_mails}.json
│   ├── meeting_notes/leadership_meetings.json
│   └── calendar/techco_calendar.json
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── migrations/001_init.sql
│   ├── app/
│   │   ├── config.py           # pydantic-settings aus .env
│   │   ├── db.py               # SQLAlchemy Engine + Session
│   │   ├── models.py           # ORM, gespiegelt zum SQL
│   │   ├── main.py             # FastAPI: /health /stats /people /pillars /heatmap /evidence
│   │   └── agents/
│   │       ├── llm.py          # Anthropic-Wrapper (lazy import) + JSON-Parsing
│   │       ├── pillar_extractor.py
│   │       ├── energy_mapper.py
│   │       ├── drift_tracker.py
│   │       ├── evidence_bridge.py
│   │       └── graph.py        # LangGraph-Orchestrierung
│   └── scripts/
│       ├── ingest.py           # normalisiert synthetic_data in die DB
│       └── analyze.py          # führt die vier Agenten aus, --mode, --from-files, --dump
└── docs/                       # per GitHub-Pages-Konvention (Pages-Root)
    ├── index.html              # self-contained Heat-Map + Drill-Down
    ├── drift_data.json         # Export von analyze --dump
    └── build_frontend.py       # baut index.html aus drift_data.json
```

## Datenmodell (6 Tabellen, siehe migrations/001_init.sql)

- **people**: id (PK, text), name, role, team, reports_to (FK people), voice, meta (jsonb)
- **pillars**: id (serial PK), key (unique), title, grundsatz, kriterien (jsonb),
  soll_gewicht (numeric 4,3), embedding (vector 1024), created_at
- **sources**: id (bigserial PK), source_type, channel, external_id,
  author_id (FK people), ts (timestamptz), text, embedding (vector 1024),
  meta (jsonb), created_at, unique(source_type, external_id)
- **mappings**: id (bigserial PK), source_id (FK sources cascade),
  pillar_id (FK pillars, nullable), is_off_strategy (bool), confidence (numeric 4,3),
  rationale, run_id, created_at
- **drift_aggregates**: id, run_id, pillar_id (FK), window_start (date),
  window_end (date), ist_anteil, soll_anteil, drift, n_sources, created_at
- **runs**: run_id (PK), started_at, finished_at, window_start, window_end,
  bucket_days, n_sources, n_pillars, status, notes

pgvector-Extension aktivieren, ivfflat-Index auf sources.embedding (cosine).

## Die vier Agenten

1. **Pillar Extractor**: liest das Strategiedokument, zerlegt es in Säulen mit
   key, title, grundsatz, kriterien und normalisierter soll_gewicht (Summe ~1.0).
2. **Energy Mapper**: ordnet jeden Datenpunkt einer Säule zu oder markiert ihn
   als strategie-fern, mit confidence und rationale. Claude-Aufrufe in Batches
   von 15 Datenpunkten.
3. **Drift Tracker**: teilt den Zeitraum in Fenster (Standard 15 Tage), berechnet
   je Fenster und Säule ist_anteil (Anteil an den zugeordneten Datenpunkten),
   soll_anteil und drift = ist - soll.
4. **Evidence Bridge**: hält für jede Zelle (Fenster × Säule) die Liste der
   beitragenden Quellen (Drill-Down), sortiert nach confidence.

Graph: `START → extract_pillars → map_energy → track_drift → bridge_evidence → END`

## Konventionen (verbindlich)

- **Zwei Modi überall**: `--mode claude` (echte Anthropic-API) und `--mode mock`
  (deterministischer Klassifikator: Kalender-Kategorie plus Keyword-Scoring,
  kostenlos, für Tests und Vorführung). Der Mock-Modus muss OHNE installiertes
  anthropic-Paket laufen, daher anthropic in llm.py erst innerhalb der
  client()-Funktion importieren (lazy).
- **analyze zwei Betriebsarten**: `--from-files` (in-memory gegen synthetic_data,
  ohne Datenbank) und DB-Modus (liest sources aus Postgres, schreibt Pillars,
  Mappings und Drift-Aggregate zurück). `--dump PATH` schreibt Heat-Map- und
  Evidence-JSON für das Frontend.
- **Persistenz außerhalb des Graphen**: der LangGraph-Graph arbeitet nur auf
  einem gemeinsamen State und bleibt frei von DB-Session-Handling. Die
  Persistenz macht der CLI-Runner (analyze.py) drumherum. So läuft der Graph
  auch rein in-memory.
- **Sprache**: Docstrings und Kommentare deutsch, Identifier englisch. Keine
  Umlaute in Python-Quelltext-Kommentaren nötig (ue/ae/oe ist ok im Code).
- **Keine Secrets im Code**: alles über pydantic-settings aus .env. .env in
  .gitignore.
- **synthetic_data/ liegt bereits vor** und ist handgefertigt (enthält eine
  eingebaute strategische Drift). NICHT neu generieren.
- **Mock-Klassifikator**: Kalender-Events werden über ihr Kategorie-Metadatum
  zugeordnet (customer_led → customer_led_growth, quality → quality_over_speed,
  enterprise/sales → enterprise_ready, speed_delivery/leadership/neutral →
  strategie-fern). Text-Kanäle über Keyword-Scoring je Säule, plus ein
  "quality_negative"-Signal (ship it, fix later, speed, momentum), das von der
  Quality-Säule abgezogen wird. Das reproduziert die eingebaute Drift.
