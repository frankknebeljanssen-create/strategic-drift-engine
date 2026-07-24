# Strategic Drift Engine

Ein Multi-Agenten-System, das die Luecke zwischen formulierter Strategie und
tatsaechlichem Organisationsverhalten sichtbar macht. Vier Agenten lesen
interne Kommunikation (Slack, Mail, Meeting-Notizen, Kalender), ordnen sie den
strategischen Saeulen zu und aggregieren die Abweichung ueber die Zeit. Jede
Zahl bleibt bis zur einzelnen Quelle nachvollziehbar. Ausgabe: eine
interaktive Heat-Map mit Drill-Down und ein Strategie-Steckbrief, der die
Grundlage der Auswertung offenlegt.

Der Stand ist ein einsatznaher Prototyp mit vollstaendiger Pipeline, echtem
Backend (FastAPI, Postgres mit pgvector) und einem self-contained Frontend
ohne Build-Kette.

## Architektur

```
  Strategiedokument                       Slack, Mail,
  (Steckbrief +                           Meeting-Notes,
   ausfuehrliche Version)                 Kalender
        |                                     |
        v                                     v
  Pillar Extractor  ------> Saeulen ----> Energy Mapper ----> Mappings
  (Agent 1)                (title,         (Agent 2)          (source_id,
                            grundsatz,     Batch-Prompt        pillar_key,
                            kriterien,     an Claude oder      confidence,
                            soll_gewicht)  Mock-Klassifikator) signals,
                                                               contribution)
                                                                    |
                                                                    v
                                                              Drift Tracker
                                                              (Agent 3)
                                                              Fenster von
                                                              15 Tagen,
                                                              ist_anteil,
                                                              soll_anteil,
                                                              drift = ist-soll
                                                                    |
                                                                    v
                                                              Evidence Bridge
                                                              (Agent 4)
                                                              Register
                                                              wi:pillar_key
                                                              -> Belege,
                                                              sortiert nach
                                                              confidence
                                                                    |
                                                                    v
                                                              JSON-Dump und
                                                              Heat-Map-Frontend
```

Die Orchestrierung laeuft ueber LangGraph als StateGraph. Der Graph bleibt
frei von DB-Handling; Persistenz macht der CLI-Runner `scripts/analyze.py`
darum herum. So laeuft dieselbe Kette in-memory (ohne DB) oder gegen
Postgres.

Zwei Modi:

- **mock**: deterministischer Klassifikator, Kalender-Kategorie plus
  Keyword-Scoring plus quality_negative-Signal. Kostenlos, laeuft ohne
  installiertes `anthropic`-Paket, reproduziert die in den synthetischen
  Daten eingebaute Drift.
- **claude**: Claude klassifiziert die Datenpunkte in Batches von 15,
  Antwort je Batch ein JSON-Array. Braucht `ANTHROPIC_API_KEY`.

## Repo-Struktur

```
strategic-drift-engine/
|-- docker-compose.yml           # Postgres+pgvector und Backend
|-- Makefile                     # up, db, ingest, analyze, psql
|-- .env.example                 # ANTHROPIC_API_KEY etc.
|-- CLAUDE.md                    # verbindlicher Projektkontext
|-- synthetic_data/              # handgefertigter Demo-Datensatz
|   |-- people.json
|   |-- strategy/
|   |   |-- techco_strategy_2026.md      # ausfuehrliche Strategie
|   |   `-- techco_steckbrief_2026.md    # Einseiter-Steckbrief
|   |-- slack/{leadership,engineering,sales}.json
|   |-- mails/{ceo_mails,leadership_mails}.json
|   |-- meeting_notes/leadership_meetings.json
|   `-- calendar/techco_calendar.json
|-- backend/
|   |-- Dockerfile
|   |-- requirements.txt
|   |-- migrations/001_init.sql
|   |-- app/
|   |   |-- config.py            # pydantic-settings aus .env
|   |   |-- db.py                # SQLAlchemy Engine + Session
|   |   |-- models.py            # ORM, gespiegelt zum SQL
|   |   |-- normalize.py         # gemeinsame Ingest- und Datei-Normalisierung
|   |   |-- main.py              # FastAPI: /health /stats /people /pillars
|   |   |                        #          /heatmap /evidence /strategy
|   |   `-- agents/
|   |       |-- llm.py           # Anthropic-Wrapper (lazy) + JSON-Parsing
|   |       |-- pillar_extractor.py
|   |       |-- energy_mapper.py
|   |       |-- drift_tracker.py
|   |       |-- evidence_bridge.py
|   |       `-- graph.py         # LangGraph-Orchestrierung
|   `-- scripts/
|       |-- ingest.py            # synthetic_data in die DB
|       `-- analyze.py           # --from-files oder DB-Modus, --dump
`-- docs/                        # per GitHub-Pages-Konvention (Pages-Root)
    |-- index.html               # self-contained Heat-Map mit Drill-Down
    |-- drift_data.json          # generiert von analyze --dump
    `-- build_frontend.py        # baut index.html aus drift_data.json
```

## Quickstart

Drei Wege, je nach dem, wie tief du einsteigen willst.

### 1. Sofort ansehen (keine Installation)

Nach dem Klonen einfach die Datei im Browser oeffnen:

```
open docs/index.html
```

`index.html` ist self-contained, die Analyse-Daten sind eingebettet. Kein
Server, keine Build-Kette, keine Abhaengigkeiten.

Was zu sehen ist:

- Die Heat-Map zeigt vier Zeitfenster (Mai bis Juni 2026) mal drei Saeulen.
  Farbe zeigt die Drift gegen den Soll-Wert, Balken zeigen den Ist-Anteil,
  der amberfarbene Strich markiert das Soll.
- Der Button **Strategy** oben rechts oeffnet ein Modal mit dem
  Strategie-Steckbrief (Sponsor, Freigabe, Grundsatz und Kriterien je
  Saeule) und darunter den aus dem Strategiedokument abgeleiteten Ziel-
  Saeulen. So ist die Grundlage der Auswertung an einem Klick sichtbar.
- Der Button **Guided Tour** fuehrt in vier Schritten durch die Drift-
  Geschichte: Ausgangslage, groesste Abweichung, Kehrseite, Endzustand.
- Klick auf eine Zelle oeffnet den Drill-Down rechts. Jede Nachricht
  laesst sich per **Show full message** aufklappen. Darunter erklaert
  der Block **How the engine read this**, welche Signale die Zuordnung
  ausgeloest haben: positive Signale (gruen), negative Signale (rot, mit
  Klartext "reduces Quality over Speed") und die Confidence als Zahl plus
  Klartext-Einordnung (very high, high, moderate, low).

### 2. Pipeline selbst laufen lassen (mock-Modus, ohne API-Kosten)

Braucht Docker Compose und Python 3.

```bash
# Analyse gegen die synthetischen Daten laufen lassen und Dump schreiben
docker compose run --rm backend python -m scripts.analyze \
    --from-files --mode mock --dump /app/docs/drift_data.json

# Heat-Map-HTML daraus bauen
python3 docs/build_frontend.py

# Ansehen
open docs/index.html
```

Der Mock-Klassifikator laeuft in-memory ohne Datenbank und ohne
`anthropic`-Paket. Das Kommando erzeugt einen frischen `drift_data.json`-
Dump, den `build_frontend.py` in `index.html` einbettet.

### 3. Voller Stack (DB, API, optional Claude)

```bash
cp .env.example .env             # Anthropic-Key eintragen falls --mode claude
make up                          # Postgres+pgvector und Backend hoch
make ingest                      # synthetic_data in die DB normalisieren

# Analyse gegen die DB (schreibt Pillars, Mappings, Drift-Aggregate, Run)
docker compose run --rm backend python -m scripts.analyze --mode claude
```

Danach steht die API auf `http://localhost:8000` bereit:

| Endpunkt    | Zweck                                                             |
|-------------|-------------------------------------------------------------------|
| `/health`   | Liveness-Check                                                    |
| `/stats`    | Zaehler ueber Personen, Saeulen, Quellen, Mappings, letzter Lauf  |
| `/people`   | Personen mit Org-Feldern                                          |
| `/pillars`  | Saeulen mit Grundsatz, Kriterien, Soll-Gewicht                    |
| `/strategy` | Steckbrief-Markdown plus alle Pillars aus der DB                  |
| `/heatmap`  | Drift-Aggregate als Zellen (Fenster mal Saeule), Soll und Ist     |
| `/evidence` | Beitragende Quellen einer Zelle, sortiert nach Konfidenz          |

Interaktive Doku unter `http://localhost:8000/docs`.

`MODE=claude make analyze` schaltet vom Mock- auf den Anthropic-Klassifikator.
`MODE=mock` funktioniert genauso, dann ohne API-Kosten.

## Governance und Datenschutz

Der Prototyp arbeitet nach vier Grundregeln, damit die Auswertung nicht in
individuelle Ueberwachung kippt:

- **Nur freigegebene offene Kanaele.** Analysiert werden Team-Kanaele,
  Meeting-Notizen und Kalender-Metadaten. Kein Zugriff auf private
  Channels oder persoenliche Postfaecher ausserhalb einer expliziten
  Freigabe der Betroffenen.
- **Metadaten vor Inhalten.** Kalender-Events werden ueber ihre Kategorie
  ausgewertet, nicht ueber ihren Inhalt. Textkanaele werden inhaltlich
  klassifiziert, aber nur so grob, wie es fuer die Drift-Aggregation
  noetig ist.
- **Keine Direktnachrichten.** DMs sind aus dem Design ausgeschlossen.
- **Aggregation statt Einzelbewertung.** Die Ausgabe ist eine Drift je
  Fenster und Saeule. Personen erscheinen nur im Drill-Down als Autor
  einzelner Quellen, nicht als Metrik. Ranking oder Scoring von Personen
  ist ausdruecklich kein Ziel.

## Datenbasis

Der Datensatz unter `synthetic_data/` ist handgefertigt, beschreibt ein
fiktives Unternehmen namens TechCo und dient ausschliesslich der
Demonstration. Er enthaelt eine bewusst eingebaute Drift (Enterprise-
Aufmerksamkeit steigt auf Kosten von Customer-Led Growth und Quality over
Speed), damit die Auswertung ueberhaupt etwas zeigt. Alle Namen, Zahlen und
Nachrichten sind erfunden.

## Weiterfuehrend

- `CLAUDE.md` beschreibt den verbindlichen Projektkontext, die Konventionen
  (Docstrings deutsch, Identifier englisch, zwei Modi ueberall) und die
  Details des Mock-Klassifikators.
- Die Migration `backend/migrations/001_init.sql` ist die Quelle der
  Wahrheit fuer das Datenmodell; `backend/app/models.py` spiegelt sie fuer
  API und Skripte.
