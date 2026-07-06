"""FastAPI-App: Read-Endpunkte auf das Datenmodell.

Die Analyse selbst laeuft ueber scripts/analyze.py (Agenten, folgt spaeter).
Diese API liest nur, was Ingest und Analyse in die DB geschrieben haben.
Endpunkte: /health /stats /people /pillars /heatmap /evidence.
"""

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import (
    DriftAggregate,
    Mapping,
    Person,
    Pillar,
    Run,
    Source,
)

app = FastAPI(title="Strategic Drift Engine", version="0.1.0")


@app.get("/health")
def health() -> dict:
    """Liveness-Check ohne DB-Zugriff."""
    return {"status": "ok"}


@app.get("/stats")
def stats(db: Session = Depends(get_session)) -> dict:
    """Zaehlt die Kernentitaeten und nennt den letzten Lauf."""
    n_sources_by_type = dict(
        db.execute(
            select(Source.source_type, func.count()).group_by(Source.source_type)
        ).all()
    )
    latest_run = db.execute(
        select(Run).order_by(Run.started_at.desc()).limit(1)
    ).scalar_one_or_none()

    return {
        "people": db.scalar(select(func.count()).select_from(Person)),
        "pillars": db.scalar(select(func.count()).select_from(Pillar)),
        "sources_total": sum(n_sources_by_type.values()),
        "sources_by_type": n_sources_by_type,
        "mappings": db.scalar(select(func.count()).select_from(Mapping)),
        "latest_run": latest_run.run_id if latest_run else None,
    }


@app.get("/people")
def list_people(db: Session = Depends(get_session)) -> list[dict]:
    """Alle Personen mit Org-Feldern."""
    rows = db.execute(select(Person).order_by(Person.team, Person.name)).scalars().all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "role": p.role,
            "team": p.team,
            "reports_to": p.reports_to,
        }
        for p in rows
    ]


@app.get("/pillars")
def list_pillars(db: Session = Depends(get_session)) -> list[dict]:
    """Die strategischen Saeulen mit Soll-Gewicht (Embedding wird nicht ausgeliefert)."""
    rows = db.execute(select(Pillar).order_by(Pillar.id)).scalars().all()
    return [
        {
            "id": p.id,
            "key": p.key,
            "title": p.title,
            "grundsatz": p.grundsatz,
            "kriterien": p.kriterien,
            "soll_gewicht": float(p.soll_gewicht) if p.soll_gewicht is not None else None,
        }
        for p in rows
    ]


@app.get("/heatmap")
def heatmap(
    run_id: str | None = Query(default=None, description="Lauf; default = letzter Lauf"),
    db: Session = Depends(get_session),
) -> dict:
    """Drift-Aggregate als Zellen (Fenster x Saeule) fuer die Heat-Map."""
    run_id = _resolve_run_id(db, run_id)
    if run_id is None:
        return {"run_id": None, "cells": []}

    rows = (
        db.execute(
            select(DriftAggregate, Pillar.key, Pillar.title)
            .join(Pillar, Pillar.id == DriftAggregate.pillar_id, isouter=True)
            .where(DriftAggregate.run_id == run_id)
            .order_by(DriftAggregate.window_start, DriftAggregate.pillar_id)
        )
        .all()
    )
    cells = [
        {
            "pillar_id": agg.pillar_id,
            "pillar_key": key,
            "pillar_title": title,
            "window_start": agg.window_start.isoformat() if agg.window_start else None,
            "window_end": agg.window_end.isoformat() if agg.window_end else None,
            "ist_anteil": _f(agg.ist_anteil),
            "soll_anteil": _f(agg.soll_anteil),
            "drift": _f(agg.drift),
            "n_sources": agg.n_sources,
        }
        for agg, key, title in rows
    ]
    return {"run_id": run_id, "cells": cells}


@app.get("/evidence")
def evidence(
    pillar_id: int = Query(..., description="Saeule"),
    window_start: str = Query(..., description="Fensterbeginn YYYY-MM-DD"),
    window_end: str = Query(..., description="Fensterende YYYY-MM-DD"),
    run_id: str | None = Query(default=None),
    db: Session = Depends(get_session),
) -> dict:
    """Drill-Down einer Zelle: beitragende Quellen, sortiert nach confidence."""
    run_id = _resolve_run_id(db, run_id)
    if run_id is None:
        raise HTTPException(status_code=404, detail="Kein Lauf vorhanden.")

    rows = (
        db.execute(
            select(Source, Mapping)
            .join(Mapping, Mapping.source_id == Source.id)
            .where(
                Mapping.run_id == run_id,
                Mapping.pillar_id == pillar_id,
                Source.ts >= window_start,
                Source.ts <= f"{window_end} 23:59:59+00",
            )
            .order_by(Mapping.confidence.desc().nullslast())
        )
        .all()
    )
    items = [
        {
            "source_id": src.id,
            "source_type": src.source_type,
            "channel": src.channel,
            "author_id": src.author_id,
            "ts": src.ts.isoformat() if src.ts else None,
            "text": src.text,
            "confidence": _f(mp.confidence),
            "rationale": mp.rationale,
        }
        for src, mp in rows
    ]
    return {
        "run_id": run_id,
        "pillar_id": pillar_id,
        "window_start": window_start,
        "window_end": window_end,
        "evidence": items,
    }


def _resolve_run_id(db: Session, run_id: str | None) -> str | None:
    """Gibt den angefragten Lauf zurueck oder faellt auf den letzten Lauf zurueck."""
    if run_id is not None:
        return run_id
    latest = db.execute(
        select(Run.run_id).order_by(Run.started_at.desc()).limit(1)
    ).scalar_one_or_none()
    return latest


def _f(value) -> float | None:
    """Numeric aus der DB in float fuer sauberes JSON."""
    return float(value) if value is not None else None
