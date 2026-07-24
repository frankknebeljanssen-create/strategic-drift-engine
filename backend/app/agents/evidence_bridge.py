"""Agent 4: Evidence Bridge.

Haelt fuer jede Zelle (Fenster x Saeule) die Liste der beitragenden Quellen fuer
den Drill-Down, sortiert nach confidence. Nur zugeordnete Datenpunkte landen im
Register (strategie-ferne bilden keine Zelle).
"""

from __future__ import annotations

from datetime import date

from app.agents.drift_tracker import to_date

_SNIPPET_LEN = 200


def bridge_evidence(
    sources: list[dict],
    mappings: list[dict],
    windows: list[tuple[date, date]],
) -> dict[str, list[dict]]:
    """Baut das Register "windowindex:pillar_key" -> Liste von Quell-Datensaetzen."""
    src_by_id = {s["id"]: s for s in sources}
    register: dict[str, list[dict]] = {}

    for m in mappings:
        pillar_key = m["pillar_key"]
        if pillar_key is None:
            continue
        src = src_by_id.get(m["source_id"])
        if src is None or src.get("ts") is None:
            continue

        wi = _index_for(windows, to_date(src["ts"]))
        cell_key = f"{wi}:{pillar_key}"
        register.setdefault(cell_key, []).append(
            {
                "source_id": m["source_id"],
                "ts": src["ts"],
                "type": src.get("source_type"),
                "channel": src.get("channel"),
                "author": src.get("author_id"),
                "confidence": m["confidence"],
                "rationale": m["rationale"],
                "signals": m.get("signals", []),
                "contribution": m.get("contribution", ""),
                "snippet": _snippet(src.get("text")),
                "text_full": src.get("text") or "",
            }
        )

    for records in register.values():
        records.sort(key=lambda r: r["confidence"] or 0.0, reverse=True)
    return register


def evidence_for_cell(evidence: dict, window_index: int, pillar_key: str) -> list[dict]:
    """Belege einer einzelnen Zelle (Fenster x Saeule)."""
    return evidence.get(f"{window_index}:{pillar_key}", [])


def _index_for(windows: list[tuple[date, date]], d: date) -> int:
    """Fensterindex per Enthaltensein, geklemmt auf den gueltigen Bereich."""
    for i, (start, end) in enumerate(windows):
        if start <= d <= end:
            return i
    if windows and d < windows[0][0]:
        return 0
    return len(windows) - 1 if windows else 0


def _snippet(text: str | None) -> str:
    return " ".join((text or "").split())[:_SNIPPET_LEN]
