"""Normalisierung von synthetic_data in einheitliche Datenstrukturen.

Reine Funktionen ohne DB- oder Anthropic-Abhaengigkeiten, damit sie sowohl vom
Ingest (schreibt in Postgres) als auch von analyze --from-files (in-memory,
ohne DB) genutzt werden koennen. Dieselbe Normalisierung, eine Quelle.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


def find_data_dir(explicit: str | None) -> Path:
    """Findet synthetic_data: explizites Argument, sonst bekannte Kandidaten."""
    if explicit:
        p = Path(explicit).resolve()
        if not p.is_dir():
            raise SystemExit(f"data-dir nicht gefunden: {p}")
        return p

    here = Path(__file__).resolve()
    candidates = [
        Path("/app/synthetic_data"),      # im Container gemountet
        Path.cwd() / "synthetic_data",
    ]
    candidates += [p / "synthetic_data" for p in here.parents]

    for c in candidates:
        if c.is_dir():
            return c
    raise SystemExit("synthetic_data nicht gefunden. Mit --path angeben.")


def read_strategy(data_dir: Path) -> str:
    """Liest das Strategiedokument als Text."""
    return (data_dir / "strategy" / "techco_strategy_2026.md").read_text(encoding="utf-8")


def _load(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def _combine(date_str: str, time_str: str | None) -> datetime:
    """Baut ein datetime aus Datum plus optionaler Startzeit (HH:MM oder HH:MM-HH:MM)."""
    if time_str:
        start = time_str.split("-")[0].strip()
        return datetime.fromisoformat(f"{date_str}T{start}:00")
    return datetime.fromisoformat(f"{date_str}T00:00:00")


def load_people(data_dir: Path) -> list[dict]:
    """Personen als Dicts. reports_to nur, wenn die Zielperson bekannt ist."""
    people = _load(data_dir / "people.json")["people"]
    known = {p["id"] for p in people}
    out = []
    for person in people:
        rt = person.get("reports_to")
        out.append(
            {
                "id": person["id"],
                "name": person["name"],
                "role": person.get("role"),
                "team": person.get("team"),
                "reports_to": rt if rt in known else None,
                "voice": person.get("voice"),
                "meta": {"position_in_pillars": person.get("position_in_pillars", {})},
            }
        )
    return out


def _author(known: set[str], candidate: str | None) -> str | None:
    """Nur bekannte Personen als author_id (sonst FK-Verletzung im DB-Modus)."""
    return candidate if candidate in known else None


def load_sources(data_dir: Path, known: set[str]) -> list[dict]:
    """Alle Kanaele in eine normalisierte Quellenliste.

    Felder je Quelle: source_type, channel, external_id, author_id, ts (datetime),
    text, meta. Der Ingest ergaenzt daraus DB-Zeilen, analyze nutzt sie direkt.
    """
    sources: list[dict] = []
    sources += _load_slack(data_dir, known)
    sources += _load_mails(data_dir, known)
    sources += _load_meeting_notes(data_dir, known)
    sources += _load_calendar(data_dir)
    return sources


def _load_slack(data_dir: Path, known: set[str]) -> list[dict]:
    out = []
    for path in sorted((data_dir / "slack").glob("*.json")):
        data = _load(path)
        channel = data.get("channel", path.stem)
        for msg in data.get("messages", []):
            ts = msg["ts"]
            out.append(
                {
                    "source_type": "slack",
                    "channel": channel,
                    "external_id": f"{channel}:{ts}",
                    "author_id": _author(known, msg.get("user")),
                    "ts": datetime.fromisoformat(ts),
                    "text": msg.get("text", ""),
                    "meta": {
                        "thread_ts": msg.get("thread_ts"),
                        "reactions": msg.get("reactions", []),
                        "raw_user": msg.get("user"),
                    },
                }
            )
    return out


def _load_mails(data_dir: Path, known: set[str]) -> list[dict]:
    out = []
    for path in sorted((data_dir / "mails").glob("*.json")):
        data = _load(path)
        mailbox = path.stem
        for mail in data.get("mails", []):
            subject = mail.get("subject", "")
            body = mail.get("body", "")
            out.append(
                {
                    "source_type": "mail",
                    "channel": mailbox,
                    "external_id": mail["id"],
                    "author_id": _author(known, mail.get("from")),
                    "ts": datetime.fromisoformat(mail["date"]),
                    "text": f"{subject}\n\n{body}".strip(),
                    "meta": {
                        "subject": subject,
                        "to": mail.get("to", []),
                        "cc": mail.get("cc", []),
                        "raw_from": mail.get("from"),
                    },
                }
            )
    return out


def _load_meeting_notes(data_dir: Path, known: set[str]) -> list[dict]:
    out = []
    for path in sorted((data_dir / "meeting_notes").glob("*.json")):
        data = _load(path)
        for note in data.get("notes", []):
            out.append(
                {
                    "source_type": "meeting_note",
                    "channel": note.get("type"),
                    "external_id": note["meeting_id"],
                    "author_id": _author(known, note.get("facilitator")),
                    "ts": _combine(note["date"], note.get("time")),
                    "text": note.get("notes", ""),
                    "meta": {
                        "type": note.get("type"),
                        "attendees": note.get("attendees", []),
                        "agenda": note.get("agenda", []),
                        "facilitator": note.get("facilitator"),
                    },
                }
            )
    return out


def _load_calendar(data_dir: Path) -> list[dict]:
    out = []
    for path in sorted((data_dir / "calendar").glob("*.json")):
        data = _load(path)
        for event in data.get("events", []):
            out.append(
                {
                    "source_type": "calendar",
                    "channel": event.get("category"),
                    "external_id": event["id"],
                    "author_id": None,  # Kalender-Events haben keinen Autor
                    "ts": _combine(event["date"], event.get("start")),
                    "text": event.get("title", ""),
                    "meta": {
                        "category": event.get("category"),
                        "duration_min": event.get("duration_min"),
                        "attendees": event.get("attendees", []),
                    },
                }
            )
    return out
