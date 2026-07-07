"""Ingest: normalisiert synthetic_data in die Datenbank.

Nutzt app.normalize fuer die Normalisierung (dieselbe Logik wie analyze
--from-files) und schreibt people und sources idempotent ueber ihre
Unique-Keys. Embeddings bleiben leer und werden spaeter von der Analyse gesetzt.

Aufruf: python -m scripts.ingest [--data-dir PFAD]
"""

from __future__ import annotations

import argparse

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db import session_scope
from app.models import Person, Source
from app.normalize import find_data_dir, load_people, load_sources


def ingest_people(session, people: list[dict]) -> int:
    """Schreibt Personen. reports_to wird in zweitem Pass gesetzt (self-FK)."""
    reports = {}
    for person in people:
        stmt = pg_insert(Person).values(
            id=person["id"],
            name=person["name"],
            role=person["role"],
            team=person["team"],
            reports_to=None,  # erst nach dem Einfuegen aller Personen setzen
            voice=person["voice"],
            meta=person["meta"],
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
        if person["reports_to"]:
            reports[person["id"]] = person["reports_to"]

    session.flush()
    for pid, rt in reports.items():
        session.get(Person, pid).reports_to = rt

    return len(people)


def ingest_sources(session, sources: list[dict]) -> dict[str, int]:
    """Upsert der Quellen ueber (source_type, external_id). Zaehlt je Typ."""
    counts: dict[str, int] = {}
    for src in sources:
        stmt = pg_insert(Source).values(
            source_type=src["source_type"],
            channel=src["channel"],
            external_id=src["external_id"],
            author_id=src["author_id"],
            ts=src["ts"],
            text=src["text"],
            meta=src["meta"],
        )
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
        counts[src["source_type"]] = counts.get(src["source_type"], 0) + 1
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest synthetic_data in die DB.")
    parser.add_argument("--data-dir", default=None, help="Pfad zu synthetic_data")
    args = parser.parse_args()

    data_dir = find_data_dir(args.data_dir)
    print(f"Ingest aus: {data_dir}")

    people = load_people(data_dir)
    known = {p["id"] for p in people}
    sources = load_sources(data_dir, known)

    with session_scope() as session:
        n_people = ingest_people(session, people)
        counts = ingest_sources(session, sources)

    total = sum(counts.values())
    by_type = " ".join(f"{k}={v}" for k, v in sorted(counts.items()))
    print(f"Fertig. people={n_people} sources={total} ({by_type})")


if __name__ == "__main__":
    main()
