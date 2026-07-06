# Strategic Drift Engine

Ein Multi-Agenten-System, das die Luecke zwischen formulierter Strategie und
tatsaechlichem Organisationsverhalten misst. Vier Agenten analysieren interne
Kommunikation (Slack, Mail, Meeting-Notizen, Kalender), ordnen sie den
strategischen Saeulen zu und machen die Abweichung (Drift) ueber die Zeit
sichtbar. Jede Zahl bleibt bis zur Einzelquelle nachvollziehbar. Ausgabe: eine
interaktive Heat-Map mit Drill-Down.

Der verbindliche Projektkontext steht in [CLAUDE.md](CLAUDE.md).

## Stand

Dieses Geruest enthaelt Infrastruktur, Datenmodell, Ingest und die Lese-API.
Die vier Agenten (`app/agents/`), der Analyse-Runner (`scripts/analyze.py`)
und das Frontend folgen als naechste Schritte.

## Voraussetzungen

- Docker und Docker Compose
- Fuer `--mode claude`: ein `ANTHROPIC_API_KEY` in `.env`

## Schnellstart

```bash
cp .env.example .env      # Werte eintragen (API-Key nur fuer claude-Modus)
make up                   # Postgres+pgvector und Backend starten
make ingest               # synthetic_data in die DB normalisieren
```

Die Migration `backend/migrations/001_init.sql` laeuft beim ersten Init des
leeren DB-Volumes automatisch.

## API

Nach `make up` erreichbar unter `http://localhost:8000`:

| Endpunkt    | Zweck                                                      |
|-------------|------------------------------------------------------------|
| `/health`   | Liveness-Check                                             |
| `/stats`    | Zaehler ueber Personen, Saeulen, Quellen, Mappings         |
| `/people`   | Personen mit Org-Feldern                                   |
| `/pillars`  | Strategische Saeulen mit Soll-Gewicht                      |
| `/heatmap`  | Drift-Aggregate als Zellen (Fenster x Saeule)              |
| `/evidence` | Drill-Down einer Zelle: beitragende Quellen nach Konfidenz |

`/heatmap` und `/evidence` liefern erst Daten, sobald die Analyse gelaufen ist.
Interaktive Doku unter `http://localhost:8000/docs`.

## Make-Targets

| Target        | Wirkung                                                   |
|---------------|-----------------------------------------------------------|
| `make up`     | DB und Backend bauen und starten                          |
| `make db`     | nur die Datenbank starten                                 |
| `make ingest` | synthetic_data in die DB schreiben                        |
| `make analyze`| Agenten ausfuehren und Frontend-Dump schreiben (folgt)    |
| `make psql`   | psql-Shell in der DB                                      |
| `make logs`   | Backend-Logs folgen                                       |

`MODE=claude make analyze` schaltet vom Mock- auf den Anthropic-Klassifikator.

## Datenmodell

Sechs Tabellen (`people`, `pillars`, `sources`, `mappings`, `drift_aggregates`,
`runs`), definiert in `backend/migrations/001_init.sql` und gespiegelt in
`backend/app/models.py`. Details in [CLAUDE.md](CLAUDE.md).
