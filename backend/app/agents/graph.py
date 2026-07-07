"""LangGraph-Orchestrierung der Analyse.

Der Graph arbeitet nur auf einem gemeinsamen State und bleibt frei von
DB-Session-Handling; die Persistenz macht der CLI-Runner (analyze.py) drumherum.
So laeuft der Graph auch rein in-memory.

Kette: START -> extract_pillars -> map_energy -> track_drift -> bridge_evidence -> END
"""

from __future__ import annotations

from datetime import date
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.agents.drift_tracker import to_date, track_drift
from app.agents.energy_mapper import map_energy
from app.agents.evidence_bridge import bridge_evidence
from app.agents.pillar_extractor import extract_pillars


class AnalysisState(TypedDict, total=False):
    """Gemeinsamer Zustand, den die Knoten fortschreiben."""

    run_id: str
    mode: str
    strategy_text: str
    sources: list[dict]
    bucket_days: int
    window_start: date
    window_end: date
    pillars: list[dict]
    mappings: list[dict]
    windows: list[tuple[date, date]]
    drift: list[dict]
    evidence: dict[str, list[dict]]
    log: list[str]


def _node_extract_pillars(state: AnalysisState) -> dict:
    pillars = extract_pillars(state["strategy_text"], state["mode"])
    log = state.get("log", []) + [
        f"extract_pillars: {len(pillars)} Saeulen ({state['mode']})"
    ]
    return {"pillars": pillars, "log": log}


def _node_map_energy(state: AnalysisState) -> dict:
    mappings = map_energy(state["sources"], state["pillars"], state["mode"])
    assigned = sum(1 for m in mappings if m["pillar_key"] is not None)
    off = len(mappings) - assigned
    log = state.get("log", []) + [
        f"map_energy: {len(mappings)} Datenpunkte, {assigned} zugeordnet, {off} strategie-fern"
    ]
    return {"mappings": mappings, "log": log}


def _node_track_drift(state: AnalysisState) -> dict:
    result = track_drift(
        state["sources"],
        state["mappings"],
        state["pillars"],
        state["window_start"],
        state["window_end"],
        state.get("bucket_days", 15),
    )
    log = state.get("log", []) + [
        f"track_drift: {len(result['windows'])} Fenster, {len(result['aggregates'])} Aggregate"
    ]
    return {"windows": result["windows"], "drift": result["aggregates"], "log": log}


def _node_bridge_evidence(state: AnalysisState) -> dict:
    evidence = bridge_evidence(state["sources"], state["mappings"], state["windows"])
    n_records = sum(len(v) for v in evidence.values())
    log = state.get("log", []) + [
        f"bridge_evidence: {len(evidence)} Zellen, {n_records} Belege"
    ]
    return {"evidence": evidence, "log": log}


def build_graph():
    """Baut und kompiliert den StateGraph."""
    graph = StateGraph(AnalysisState)
    graph.add_node("extract_pillars", _node_extract_pillars)
    graph.add_node("map_energy", _node_map_energy)
    graph.add_node("track_drift", _node_track_drift)
    graph.add_node("bridge_evidence", _node_bridge_evidence)
    graph.add_edge(START, "extract_pillars")
    graph.add_edge("extract_pillars", "map_energy")
    graph.add_edge("map_energy", "track_drift")
    graph.add_edge("track_drift", "bridge_evidence")
    graph.add_edge("bridge_evidence", END)
    return graph.compile()


def run_analysis(
    strategy_text: str,
    sources: list[dict],
    run_id: str,
    mode: str,
    bucket_days: int = 15,
    window_start=None,
    window_end=None,
) -> AnalysisState:
    """Fuehrt den Graphen aus und gibt den finalen State zurueck (ohne Persistenz).

    Fehlen die Fenstergrenzen, werden sie aus min/max der Quellen-Zeitstempel
    abgeleitet.
    """
    dates = [to_date(s["ts"]) for s in sources if s.get("ts") is not None]
    if window_start is None:
        window_start = min(dates) if dates else date.today()
    if window_end is None:
        window_end = max(dates) if dates else window_start

    app = build_graph()
    initial: AnalysisState = {
        "run_id": run_id,
        "mode": mode,
        "strategy_text": strategy_text,
        "sources": sources,
        "bucket_days": bucket_days,
        "window_start": to_date(window_start),
        "window_end": to_date(window_end),
        "pillars": [],
        "mappings": [],
        "windows": [],
        "drift": [],
        "evidence": {},
        "log": [],
    }
    return app.invoke(initial)
