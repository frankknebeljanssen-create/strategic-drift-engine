"""CLI-Runner der Analyse.

Zwei Betriebsarten:
- --from-files: baut die sources in-memory aus synthetic_data (dieselbe
  Normalisierung wie ingest, ohne DB) und ruft run_analysis.
- DB-Modus (Standard): liest sources aus Postgres, ruft run_analysis, schreibt
  Pillars und Mappings zurueck und legt einen Run an.

Die Persistenz sitzt bewusst hier, nicht im LangGraph-Graphen.

Aufruf:
  python -m scripts.analyze --from-files --mode mock
  python -m scripts.analyze --mode claude
"""

from __future__ import annotations

import argparse

from app.agents.graph import run_analysis
from app.normalize import find_data_dir, load_people, load_sources, read_strategy


def _summary(state: dict) -> None:
    """Druckt das Log und eine Kurzstatistik des Laufs."""
    for line in state.get("log", []):
        print(f"  {line}")
    pillars = state.get("pillars", [])
    mappings = state.get("mappings", [])
    assigned = sum(1 for m in mappings if m["pillar_key"] is not None)
    off = len(mappings) - assigned
    print(
        f"Ergebnis: pillars={len(pillars)} "
        f"mappings={len(mappings)} (zugeordnet={assigned}, strategie-fern={off})"
    )
    for p in pillars:
        print(f"  - {p['key']}: soll_gewicht={p['soll_gewicht']}")


# --- from-files ------------------------------------------------------------

def run_from_files(mode: str, path: str | None) -> None:
    """In-memory Analyse gegen synthetic_data, ohne Datenbank."""
    data_dir = find_data_dir(path)
    print(f"Analyse (--from-files, mode={mode}) aus: {data_dir}")

    strategy_text = read_strategy(data_dir)
    known = {p["id"] for p in load_people(data_dir)}
    raw = load_sources(data_dir, known)
    sources = [
        {
            "id": s["external_id"],
            "source_type": s["source_type"],
            "channel": s["channel"],
            "ts": s["ts"].isoformat(),
            "text": s["text"],
            "meta": s["meta"],
        }
        for s in raw
    ]

    state = run_analysis(strategy_text, sources, run_id=f"files-{mode}", mode=mode)
    _summary(state)


# --- DB-Modus --------------------------------------------------------------

def run_db(mode: str, path: str | None) -> None:
    """Liest sources aus Postgres, analysiert und schreibt Ergebnisse zurueck."""
    # DB-Importe bewusst lazy: der from-files/mock-Pfad soll ohne sie laufen.
    from datetime import datetime, timezone

    from sqlalchemy import select

    from app.db import session_scope
    from app.models import Run, Source

    data_dir = find_data_dir(path)
    strategy_text = read_strategy(data_dir)
    run_id = f"run-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
    print(f"Analyse (DB-Modus, mode={mode}, run_id={run_id})")

    with session_scope() as session:
        rows = session.execute(select(Source)).scalars().all()
        sources = [
            {
                "id": s.id,
                "source_type": s.source_type,
                "channel": s.channel,
                "ts": s.ts.isoformat() if s.ts else None,
                "text": s.text,
                "meta": s.meta or {},
            }
            for s in rows
        ]
        if not sources:
            raise SystemExit("Keine sources in der DB. Erst 'make ingest' ausfuehren.")

        state = run_analysis(strategy_text, sources, run_id=run_id, mode=mode)

        pillar_id_by_key = _persist_pillars(session, state["pillars"])
        _persist_mappings(session, state["mappings"], pillar_id_by_key, run_id)
        _persist_run(session, Run, run_id, rows, state)

    _summary(state)


def _persist_pillars(session, pillars: list[dict]) -> dict[str, int]:
    """Upsert der Saeulen ueber key. Gibt key -> id zurueck."""
    from sqlalchemy import select
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    from app.models import Pillar

    for p in pillars:
        stmt = pg_insert(Pillar).values(
            key=p["key"],
            title=p["title"],
            grundsatz=p.get("grundsatz"),
            kriterien=p.get("kriterien", []),
            soll_gewicht=p.get("soll_gewicht"),
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[Pillar.key],
            set_={
                "title": stmt.excluded.title,
                "grundsatz": stmt.excluded.grundsatz,
                "kriterien": stmt.excluded.kriterien,
                "soll_gewicht": stmt.excluded.soll_gewicht,
            },
        )
        session.execute(stmt)
    session.flush()

    rows = session.execute(select(Pillar.key, Pillar.id)).all()
    return {key: pid for key, pid in rows}


def _persist_mappings(session, mappings, pillar_id_by_key, run_id) -> None:
    """Schreibt die Mappings dieses Laufs neu (idempotent je run_id)."""
    from sqlalchemy import delete

    from app.models import Mapping

    session.execute(delete(Mapping).where(Mapping.run_id == run_id))
    for m in mappings:
        pillar_key = m["pillar_key"]
        session.add(
            Mapping(
                source_id=m["source_id"],
                pillar_id=pillar_id_by_key.get(pillar_key) if pillar_key else None,
                is_off_strategy=pillar_key is None,
                confidence=m["confidence"],
                rationale=m["rationale"],
                run_id=run_id,
            )
        )


def _persist_run(session, Run, run_id, source_rows, state) -> None:
    """Legt die Run-Zeile mit Fensterrand und Zaehlern an."""
    from datetime import datetime, timezone

    ts_values = [s.ts for s in source_rows if s.ts]
    window_start = min(ts_values).date() if ts_values else None
    window_end = max(ts_values).date() if ts_values else None
    session.add(
        Run(
            run_id=run_id,
            finished_at=datetime.now(timezone.utc),
            window_start=window_start,
            window_end=window_end,
            n_sources=len(source_rows),
            n_pillars=len(state["pillars"]),
            status="mapped",
            notes="; ".join(state.get("log", [])),
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Fuehrt die Analyse-Agenten aus.")
    parser.add_argument("--mode", choices=["claude", "mock"], default="mock")
    parser.add_argument(
        "--from-files",
        action="store_true",
        help="In-memory gegen synthetic_data, ohne DB",
    )
    parser.add_argument("--path", default=None, help="Pfad zu synthetic_data")
    args = parser.parse_args()

    if args.from_files:
        run_from_files(args.mode, args.path)
    else:
        run_db(args.mode, args.path)


if __name__ == "__main__":
    main()
