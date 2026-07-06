-- Initiales Schema der Strategic Drift Engine.
-- Sechs Tabellen plus pgvector. Gespiegelt in app/models.py.

CREATE EXTENSION IF NOT EXISTS vector;

-- Personen: Org-Graph (reports_to) und Stimme fuer die Zuordnung.
CREATE TABLE IF NOT EXISTS people (
    id          text PRIMARY KEY,
    name        text NOT NULL,
    role        text,
    team        text,
    reports_to  text REFERENCES people (id),
    voice       text,
    meta        jsonb NOT NULL DEFAULT '{}'::jsonb
);

-- Strategische Saeulen. embedding und soll_gewicht kommen vom Pillar Extractor.
CREATE TABLE IF NOT EXISTS pillars (
    id            serial PRIMARY KEY,
    key           text NOT NULL UNIQUE,
    title         text NOT NULL,
    grundsatz     text,
    kriterien     jsonb NOT NULL DEFAULT '[]'::jsonb,
    soll_gewicht  numeric(4, 3),
    embedding     vector(1024),
    created_at    timestamptz NOT NULL DEFAULT now()
);

-- Rohe Datenpunkte aus allen Kanaelen. external_id sichert Idempotenz beim Ingest.
CREATE TABLE IF NOT EXISTS sources (
    id           bigserial PRIMARY KEY,
    source_type  text NOT NULL,
    channel      text,
    external_id  text NOT NULL,
    author_id    text REFERENCES people (id),
    ts           timestamptz,
    text         text,
    embedding    vector(1024),
    meta         jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at   timestamptz NOT NULL DEFAULT now(),
    UNIQUE (source_type, external_id)
);

-- Zuordnung Datenpunkt -> Saeule (oder strategie-fern) vom Energy Mapper.
CREATE TABLE IF NOT EXISTS mappings (
    id              bigserial PRIMARY KEY,
    source_id       bigint NOT NULL REFERENCES sources (id) ON DELETE CASCADE,
    pillar_id       integer REFERENCES pillars (id),
    is_off_strategy boolean NOT NULL DEFAULT false,
    confidence      numeric(4, 3),
    rationale       text,
    run_id          text,
    created_at      timestamptz NOT NULL DEFAULT now()
);

-- Aggregierte Drift je Zeitfenster und Saeule vom Drift Tracker.
CREATE TABLE IF NOT EXISTS drift_aggregates (
    id            bigserial PRIMARY KEY,
    run_id        text,
    pillar_id     integer REFERENCES pillars (id),
    window_start  date,
    window_end    date,
    ist_anteil    numeric(6, 4),
    soll_anteil   numeric(6, 4),
    drift         numeric(6, 4),
    n_sources     integer,
    created_at    timestamptz NOT NULL DEFAULT now()
);

-- Ein Lauf der Analyse. Klammert Mappings und Aggregate ueber run_id.
CREATE TABLE IF NOT EXISTS runs (
    run_id        text PRIMARY KEY,
    started_at    timestamptz NOT NULL DEFAULT now(),
    finished_at   timestamptz,
    window_start  date,
    window_end    date,
    bucket_days   integer,
    n_sources     integer,
    n_pillars     integer,
    status        text,
    notes         text
);

-- Indizes fuer die haeufigen Zugriffe.
CREATE INDEX IF NOT EXISTS idx_sources_ts ON sources (ts);
CREATE INDEX IF NOT EXISTS idx_sources_type_channel ON sources (source_type, channel);
CREATE INDEX IF NOT EXISTS idx_mappings_source ON mappings (source_id);
CREATE INDEX IF NOT EXISTS idx_mappings_run ON mappings (run_id);
CREATE INDEX IF NOT EXISTS idx_drift_run ON drift_aggregates (run_id);

-- Approximativer Nearest-Neighbor-Index (Cosine) fuer semantische Suche.
CREATE INDEX IF NOT EXISTS idx_sources_embedding
    ON sources USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
