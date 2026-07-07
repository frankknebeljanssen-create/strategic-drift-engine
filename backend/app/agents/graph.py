"""LangGraph-Orchestrierung der Analyse.

Der Graph arbeitet nur auf einem gemeinsamen State und bleibt frei von
DB-Session-Handling; die Persistenz macht der CLI-Runner (analyze.py) drumherum.
So laeuft der Graph auch rein in-memory.

Kette: START -> extract_pillars -> map_energy -> END
(Die weiteren Knoten drift_tracker und evidence_bridge folgen spaeter.)
"""

from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.agents.energy_mapper import map_energy
from app.agents.pillar_extractor import extract_pillars


class AnalysisState(TypedDict, total=False):
    """Gemeinsamer Zustand, den die Knoten fortschreiben."""

    run_id: str
    mode: str
    strategy_text: str
    sources: list[dict]
    pillars: list[dict]
    mappings: list[dict]
    log: list[str]


def _node_extract_pillars(state: AnalysisState) -> dict:
    pillars = extract_pillars(state["strategy_text"], state["mode"])
    log = state.get("log", []) + [f"extract_pillars: {len(pillars)} Saeulen ({state['mode']})"]
    return {"pillars": pillars, "log": log}


def _node_map_energy(state: AnalysisState) -> dict:
    mappings = map_energy(state["sources"], state["pillars"], state["mode"])
    assigned = sum(1 for m in mappings if m["pillar_key"] is not None)
    off = len(mappings) - assigned
    log = state.get("log", []) + [
        f"map_energy: {len(mappings)} Datenpunkte, {assigned} zugeordnet, {off} strategie-fern"
    ]
    return {"mappings": mappings, "log": log}


def build_graph():
    """Baut und kompiliert den StateGraph."""
    graph = StateGraph(AnalysisState)
    graph.add_node("extract_pillars", _node_extract_pillars)
    graph.add_node("map_energy", _node_map_energy)
    graph.add_edge(START, "extract_pillars")
    graph.add_edge("extract_pillars", "map_energy")
    graph.add_edge("map_energy", END)
    return graph.compile()


def run_analysis(
    strategy_text: str,
    sources: list[dict],
    run_id: str,
    mode: str,
) -> AnalysisState:
    """Fuehrt den Graphen aus und gibt den finalen State zurueck (ohne Persistenz)."""
    app = build_graph()
    initial: AnalysisState = {
        "run_id": run_id,
        "mode": mode,
        "strategy_text": strategy_text,
        "sources": sources,
        "pillars": [],
        "mappings": [],
        "log": [],
    }
    return app.invoke(initial)
