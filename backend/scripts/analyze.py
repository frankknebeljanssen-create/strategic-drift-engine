"""CLI-Runner der Analyse.

Zwei Betriebsarten:
- --from-files: baut die sources in-memory aus synthetic_data (dieselbe
  Normalisierung wie ingest, ohne DB) und ruft run_analysis.
- DB-Modus (Standard): liest sources aus Postgres, ruft run_analysis, schreibt
  Pillars, Mappings und Drift-Aggregate zurueck und legt einen Run an.

Die Persistenz sitzt bewusst hier, nicht im LangGraph-Graphen.

Aufruf:
  python -m scripts.analyze --from-files --mode mock --dump /tmp/hm.json
  python -m scripts.analyze --mode claude --bucket-days 15
"""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime

from app.agents.graph import run_analysis
from app.normalize import find_data_dir, load_people, load_sources, read_strategy


# --- Ausgabe ---------------------------------------------------------------

def _iso(value):
    """date/datetime -> ISO-String, alles andere unveraendert."""
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def build_payload(state: dict) -> dict:
    """Erzeugt ein JSON-serialisierbares Heat-Map- und Evidence-Paket."""
    windows = [
        {"index": i, "start": _iso(s), "end": _iso(e)}
        for i, (s, e) in enumerate(state.get("windows", []))
    ]
    cells = [
        {**agg, "window_start": _iso(agg["window_start"]), "window_end": _iso(agg["window_end"])}
        for agg in state.get("drift", [])
    ]
    pillars = [
        {
            "key": p["key"],
            "title": p["title"],
            # Beide Namen mitgeben: soll_anteil erwartet das Frontend
            # (Sparkline, Row-Label), soll_gewicht ist die kanonische Bezeichnung
            # in DB und /pillars-API.
            "soll_anteil": p["soll_gewicht"],
            "soll_gewicht": p["soll_gewicht"],
            "grundsatz": p.get("grundsatz", ""),
            "kriterien": p.get("kriterien", []),
        }
        for p in state.get("pillars", [])
    ]
    return {
        "run_id": state.get("run_id"),
        "pillars": pillars,
        "windows": windows,
        "cells": cells,
        "evidence": state.get("evidence", {}),
    }


def print_drift_table(state: dict) -> None:
    """Kompakte Drift-Tabelle: je Fenster die ist-Anteile und Drift je Saeule."""
    pillar_keys = [p["key"] for p in state.get("pillars", [])]
    by_wi: dict[int, dict[str, dict]] = {}
    for agg in state.get("drift", []):
        by_wi.setdefault(agg["window_index"], {})[agg["pillar_key"]] = agg

    print("Drift-Tabelle (ist-Anteil, Drift gegen soll):")
    for wi, (w_start, w_end) in enumerate(state.get("windows", [])):
        parts = []
        for key in pillar_keys:
            agg = by_wi.get(wi, {}).get(key)
            if agg is None:
                continue
            parts.append(
                f"{key}={agg['ist_anteil'] * 100:4.0f}% (d {agg['drift'] * 100:+3.0f})"
            )
        print(f"  W{wi} {_iso(w_start)}..{_iso(w_end)}: " + "   ".join(parts))


def _summary(state: dict) -> None:
    for line in state.get("log", []):
        print(f"  {line}")
    n_evidence = sum(len(v) for v in state.get("evidence", {}).values())
    print(
        f"Ergebnis: pillars={len(state.get('pillars', []))} "
        f"windows={len(state.get('windows', []))} "
        f"cells={len(state.get('drift', []))} evidence={n_evidence}"
    )
    print_drift_table(state)


def _dump(state: dict, path: str) -> None:
    payload = build_payload(state)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    print(
        f"Dump geschrieben: {path} "
        f"({len(payload['cells'])} cells, "
        f"{sum(len(v) for v in payload['evidence'].values())} Belege)"
    )


# --- from-files ------------------------------------------------------------

def run_from_files(mode: str, path: str | None, bucket_days: int, dump: str | None) -> None:
    """In-memory Analyse gegen synthetic_data, ohne Datenbank."""
    data_dir = find_data_dir(path)
    print(f"Analyse (--from-files, mode={mode}, bucket_days={bucket_days}) aus: {data_dir}")

    strategy_text = read_strategy(data_dir)
    known = {p["id"] for p in load_people(data_dir)}
    sources = [
        {
            "id": s["external_id"],
            "source_type": s["source_type"],
            "channel": s["channel"],
            "author_id": s["author_id"],
            "ts": s["ts"].isoformat(),
            "text": s["text"],
            "meta": s["meta"],
        }
        for s in load_sources(data_dir, known)
    ]

    state = run_analysis(strategy_text, sources, run_id=f"files-{mode}", mode=mode, bucket_days=bucket_days)
    _summary(state)
    if dump:
        _dump(state, dump)


# --- DB-Modus --------------------------------------------------------------

def run_db(mode: str, path: str | None, bucket_days: int, dump: str | None) -> None:
    """Liest sources aus Postgres, analysiert und schreibt Ergebnisse zurueck."""
    # DB-Importe bewusst lazy: der from-files/mock-Pfad soll ohne sie laufen.
    from datetime import timezone

    from sqlalchemy import select

    from app.db import session_scope
    from app.models import Run, Source

    data_dir = find_data_dir(path)
    strategy_text = read_strategy(data_dir)
    run_id = f"run-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
    print(f"Analyse (DB-Modus, mode={mode}, run_id={run_id}, bucket_days={bucket_days})")

    with session_scope() as session:
        rows = session.execute(select(Source)).scalars().all()
        sources = [
            {
                "id": s.id,
                "source_type": s.source_type,
                "channel": s.channel,
                "author_id": s.author_id,
                "ts": s.ts.isoformat() if s.ts else None,
                "text": s.text,
                "meta": s.meta or {},
            }
            for s in rows
        ]
        if not sources:
            raise SystemExit("Keine sources in der DB. Erst 'make ingest' ausfuehren.")

        state = run_analysis(
            strategy_text, sources, run_id=run_id, mode=mode, bucket_days=bucket_days
        )

        pillar_id_by_key = _persist_pillars(session, state["pillars"])
        _persist_mappings(session, state["mappings"], pillar_id_by_key, run_id)
        _persist_drift(session, state["drift"], pillar_id_by_key, run_id)
        _persist_run(session, Run, run_id, state, bucket_days)

    _summary(state)
    if dump:
        _dump(state, dump)


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


def _persist_drift(session, aggregates, pillar_id_by_key, run_id) -> None:
    """Schreibt die Drift-Aggregate dieses Laufs neu (idempotent je run_id)."""
    from sqlalchemy import delete

    from app.models import DriftAggregate

    session.execute(delete(DriftAggregate).where(DriftAggregate.run_id == run_id))
    for agg in aggregates:
        session.add(
            DriftAggregate(
                run_id=run_id,
                pillar_id=pillar_id_by_key.get(agg["pillar_key"]),
                window_start=agg["window_start"],
                window_end=agg["window_end"],
                ist_anteil=agg["ist_anteil"],
                soll_anteil=agg["soll_anteil"],
                drift=agg["drift"],
                n_sources=agg["n_sources"],
            )
        )


def _persist_run(session, Run, run_id, state, bucket_days) -> None:
    """Legt die Run-Zeile mit Fenster, Zaehlern und Status 'done' an."""
    from datetime import timezone

    session.add(
        Run(
            run_id=run_id,
            finished_at=datetime.now(timezone.utc),
            window_start=state["window_start"],
            window_end=state["window_end"],
            bucket_days=bucket_days,
            n_sources=len(state["sources"]),
            n_pillars=len(state["pillars"]),
            status="done",
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
    parser.add_argument("--bucket-days", type=int, default=15, help="Fenstergroesse in Tagen")
    parser.add_argument("--dump", default=None, help="Pfad fuer das Heat-Map-/Evidence-JSON")
    args = parser.parse_args()

    if args.from_files:
        run_from_files(args.mode, args.path, args.bucket_days, args.dump)
    else:
        run_db(args.mode, args.path, args.bucket_days, args.dump)


if __name__ == "__main__":
    main()
