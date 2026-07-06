"""Ingest: normalisiert synthetic_data in die Datenbank.

Liest people, Slack, Mails, Meeting-Notes und Kalender und schreibt sie in die
Tabellen people und sources. Idempotent ueber (source_type, external_id):
ein erneuter Lauf aktualisiert statt zu duplizieren. Embeddings bleiben leer
und werden spaeter von der Analyse gesetzt.

Aufruf: python -m scripts.ingest [--data-dir PFAD]
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db import session_scope
from app.models import Person, Source


def _find_data_dir(explicit: str | None) -> Path:
    """Findet synthetic_data: explizites Argument, sonst bekannte Kandidaten."""
    if explicit:
        p = Path(explicit).resolve()
        if not p.is_dir():
            raise SystemExit(f"data-dir nicht gefunden: {p}")
        return p

    here = Path(__file__).resolve()
    candidates = [
        Path("/app/synthetic_data"),          # im Container gemountet
        here.parents[2] / "synthetic_data",   # Repo-Root (backend/scripts/..)
        here.parents[3] / "synthetic_data",   # falls tiefer verschachtelt
        Path.cwd() / "synthetic_data",
    ]
    for c in candidates:
        if c.is_dir():
            return c
    raise SystemExit("synthetic_data nicht gefunden. Mit --data-dir angeben.")


def _load(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def _combine(date_str: str, time_str: str | None) -> datetime:
    """Baut ein datetime aus Datum plus optionaler Startzeit (HH:MM oder HH:MM-HH:MM)."""
    if time_str:
        start = time_str.split("-")[0].strip()
        return datetime.fromisoformat(f"{date_str}T{start}:00")
    return datetime.fromisoformat(f"{date_str}T00:00:00")


# --- people ---------------------------------------------------------------

def ingest_people(session, data_dir: Path) -> int:
    """Schreibt Personen. reports_to wird in zweitem Pass gesetzt (self-FK)."""
    people = _load(data_dir / "people.json")["people"]

    known = {p["id"] for p in people}
    reports = {}

    for person in people:
        meta = {"position_in_pillars": person.get("position_in_pillars", {})}
        stmt = pg_insert(Person).values(
            id=person["id"],
            name=person["name"],
            role=person.get("role"),
            team=person.get("team"),
            reports_to=None,  # erst nach dem Einfuegen aller Personen setzen
            voice=person.get("voice"),
            meta=meta,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[Person.id],
            set_={
                "name": stmt.excluded.name,
                "role": stmt.excluded.role,
                "team": stmt.excluded.team,
                "voice": stmt.excluded.voice,
                "meta": stmt.excluded.meta,
            },
        )
        session.execute(stmt)
        rt = person.get("reports_to")
        if rt and rt in known:
            reports[person["id"]] = rt

    session.flush()
    for pid, rt in reports.items():
        session.get(Person, pid).reports_to = rt

    return len(people)


# --- sources ---------------------------------------------------------------

def _upsert_source(session, **values) -> None:
    """Upsert einer Quelle ueber (source_type, external_id)."""
    stmt = pg_insert(Source).values(**values)
    stmt = stmt.on_conflict_do_update(
        index_elements=[Source.source_type, Source.external_id],
        set_={
            "channel": stmt.excluded.channel,
            "author_id": stmt.excluded.author_id,
            "ts": stmt.excluded.ts,
            "text": stmt.excluded.text,
            "meta": stmt.excluded.meta,
        },
    )
    session.execute(stmt)


def _author(known: set[str], candidate: str | None) -> str | None:
    """Nur bekannte Personen als author_id setzen (sonst FK-Verletzung)."""
    return candidate if candidate in known else None


def ingest_slack(session, data_dir: Path, known: set[str]) -> int:
    n = 0
    for path in sorted((data_dir / "slack").glob("*.json")):
        data = _load(path)
        channel = data.get("channel", path.stem)
        for msg in data.get("messages", []):
            ts = msg["ts"]
            _upsert_source(
                session,
                source_type="slack",
                channel=channel,
                external_id=f"{channel}:{ts}",
                author_id=_author(known, msg.get("user")),
                ts=datetime.fromisoformat(ts),
                text=msg.get("text", ""),
                meta={
                    "thread_ts": msg.get("thread_ts"),
                    "reactions": msg.get("reactions", []),
                    "raw_user": msg.get("user"),
                },
            )
            n += 1
    return n


def ingest_mails(session, data_dir: Path, known: set[str]) -> int:
    n = 0
    for path in sorted((data_dir / "mails").glob("*.json")):
        data = _load(path)
        mailbox = path.stem  # z.B. ceo_mails
        for mail in data.get("mails", []):
            subject = mail.get("subject", "")
            body = mail.get("body", "")
            _upsert_source(
                session,
                source_type="mail",
                channel=mailbox,
                external_id=mail["id"],
                author_id=_author(known, mail.get("from")),
                ts=datetime.fromisoformat(mail["date"]),
                text=f"{subject}\n\n{body}".strip(),
                meta={
                    "subject": subject,
                    "to": mail.get("to", []),
                    "cc": mail.get("cc", []),
                    "raw_from": mail.get("from"),
                },
            )
            n += 1
    return n


def ingest_meeting_notes(session, data_dir: Path, known: set[str]) -> int:
    n = 0
    for path in sorted((data_dir / "meeting_notes").glob("*.json")):
        data = _load(path)
        for note in data.get("notes", []):
            _upsert_source(
                session,
                source_type="meeting_note",
                channel=note.get("type"),
                external_id=note["meeting_id"],
                author_id=_author(known, note.get("facilitator")),
                ts=_combine(note["date"], note.get("time")),
                text=note.get("notes", ""),
                meta={
                    "type": note.get("type"),
                    "attendees": note.get("attendees", []),
                    "agenda": note.get("agenda", []),
                    "facilitator": note.get("facilitator"),
                },
            )
            n += 1
    return n


def ingest_calendar(session, data_dir: Path, known: set[str]) -> int:
    n = 0
    for path in sorted((data_dir / "calendar").glob("*.json")):
        data = _load(path)
        for event in data.get("events", []):
            _upsert_source(
                session,
                source_type="calendar",
                channel=event.get("category"),
                external_id=event["id"],
                author_id=None,  # Kalender-Events haben keinen Autor
                ts=_combine(event["date"], event.get("start")),
                text=event.get("title", ""),
                meta={
                    "category": event.get("category"),
                    "duration_min": event.get("duration_min"),
                    "attendees": event.get("attendees", []),
                },
            )
            n += 1
    return n


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest synthetic_data in die DB.")
    parser.add_argument("--data-dir", default=None, help="Pfad zu synthetic_data")
    args = parser.parse_args()

    data_dir = _find_data_dir(args.data_dir)
    print(f"Ingest aus: {data_dir}")

    with session_scope() as session:
        n_people = ingest_people(session, data_dir)
        known = set(session.execute(select(Person.id)).scalars().all())
        n_slack = ingest_slack(session, data_dir, known)
        n_mails = ingest_mails(session, data_dir, known)
        n_notes = ingest_meeting_notes(session, data_dir, known)
        n_cal = ingest_calendar(session, data_dir, known)

    total = n_slack + n_mails + n_notes + n_cal
    print(
        f"Fertig. people={n_people} sources={total} "
        f"(slack={n_slack} mail={n_mails} meeting_note={n_notes} calendar={n_cal})"
    )


if __name__ == "__main__":
    main()
