"""Agent 2: Energy Mapper.

Ordnet jeden Datenpunkt einer Saeule zu oder markiert ihn als strategie-fern
(pillar_key None), mit confidence und rationale.

claude-Modus: Claude klassifiziert in Batches von 15 Datenpunkten (ein
JSON-Array je Batch). mock-Modus: deterministischer Klassifikator, der die in
CLAUDE.md beschriebene, eingebaute Drift reproduziert (Kalender-Kategorie plus
Keyword-Scoring plus quality_negative-Signal).

Rueckgabe je Datenpunkt: {source_id, pillar_key (oder None), confidence, rationale}.
"""

from __future__ import annotations

from app.agents.llm import call_claude, parse_json

BATCH_SIZE = 15

# --- Mock-Klassifikator ----------------------------------------------------

# Kalender-Kategorie -> Saeule (None = strategie-fern).
_CALENDAR_MAP = {
    "customer_led": "customer_led_growth",
    "quality": "quality_over_speed",
    "enterprise": "enterprise_ready",
    "sales": "enterprise_ready",
    "speed_delivery": None,
    "leadership": None,
    "neutral": None,
}

# Keyword-Signale je Saeule fuer Text-Kanaele (lowercase, Substring-Match).
_KEYWORDS = {
    "customer_led_growth": [
        "kunde", "kunden", "customer", "nps", "discovery", "customer success",
        "cs-", " cs ", "ticket", "feedback", "interview", "retention", "signal",
        "customer-anker", "roadmap", "nutzer", "onboarding",
    ],
    "quality_over_speed": [
        "qualitaet", "quality", "test", "coverage", "bug", "bugs", "qa",
        "regression", "triage", "reife", "stabil", "zuverlaessig",
        "technische schuld", "tech debt", "veto",
    ],
    "enterprise_ready": [
        "enterprise", "soc2", "soc 2", "sso", "saml", "azure ad", "okta",
        "audit", "audit-log", "compliance", "dsgvo", "iso 27001", "deal",
        "pipeline", "playbook", "zertifiz", "series c",
    ],
}

# Signal gegen die Quality-Saeule (Speed-/Ship-Kultur), wird abgezogen.
_QUALITY_NEGATIVE = [
    "ship it", "fix later", "move fast", "momentum", "velocity",
    "schnell liefern", "speed", "quick win", "hotfix schnell",
]


def map_energy(sources: list[dict], pillars: list[dict], mode: str) -> list[dict]:
    """Klassifiziert alle Datenpunkte. mode: 'claude' oder 'mock'."""
    if mode == "claude":
        return _map_claude(sources, pillars)
    return [_map_one_mock(src) for src in sources]


# --- Mock ------------------------------------------------------------------

def _map_one_mock(src: dict) -> dict:
    if src.get("source_type") == "calendar":
        return _map_calendar_mock(src)
    return _map_text_mock(src)


def _map_calendar_mock(src: dict) -> dict:
    category = (src.get("meta") or {}).get("category")
    pillar = _CALENDAR_MAP.get(category)
    if pillar is None:
        return _result(src, None, 0.6, f"mock: Kalender-Kategorie '{category}' ist strategie-fern")
    return _result(src, pillar, 0.9, f"mock: Kalender-Kategorie '{category}' -> {pillar}")


def _map_text_mock(src: dict) -> dict:
    text = (src.get("text") or "").lower()

    scores = {key: _count_hits(text, words) for key, words in _KEYWORDS.items()}
    # quality_negative-Signal von der Quality-Saeule abziehen.
    neg = _count_hits(text, _QUALITY_NEGATIVE)
    scores["quality_over_speed"] -= neg

    best_key = max(scores, key=scores.get)
    best_score = scores[best_key]

    if best_score <= 0:
        reason = "keine Saeulen-Signale" if neg == 0 else f"nur Speed-Signal (neg={neg})"
        return _result(src, None, 0.5, f"mock: {reason} -> strategie-fern")

    confidence = min(0.95, 0.5 + 0.1 * best_score)
    return _result(
        src,
        best_key,
        round(confidence, 3),
        f"mock: Keyword-Score {best_key}={best_score} (neg={neg})",
    )


def _count_hits(text: str, words: list[str]) -> int:
    return sum(text.count(w) for w in words)


def _result(src: dict, pillar_key, confidence: float, rationale: str) -> dict:
    return {
        "source_id": src["id"],
        "pillar_key": pillar_key,
        "confidence": confidence,
        "rationale": rationale,
    }


# --- Claude ----------------------------------------------------------------

_SYSTEM = (
    "Du bist ein Analyst, der interne Kommunikation strategischen Saeulen "
    "zuordnet. Du antwortest ausschliesslich mit JSON."
)


def _map_claude(sources: list[dict], pillars: list[dict]) -> list[dict]:
    results: list[dict] = []
    for start in range(0, len(sources), BATCH_SIZE):
        batch = sources[start : start + BATCH_SIZE]
        results.extend(_map_claude_batch(batch, pillars))
    return results


def _map_claude_batch(batch: list[dict], pillars: list[dict]) -> list[dict]:
    pillar_lines = "\n".join(
        f'- "{p["key"]}": {p["title"]} — {p.get("grundsatz", "")}' for p in pillars
    )
    item_lines = "\n".join(
        f'{i}. [{s.get("source_type")}/{s.get("channel")}] {_shorten(s.get("text"))}'
        for i, s in enumerate(batch)
    )
    user = _USER_TEMPLATE.format(pillars=pillar_lines, items=item_lines)

    data = parse_json(call_claude(_SYSTEM, user))
    if not isinstance(data, list):
        raise ValueError("Energy Mapper: erwartet ein JSON-Array je Batch")

    by_index = {int(d["index"]): d for d in data if "index" in d}
    out = []
    for i, src in enumerate(batch):
        d = by_index.get(i, {})
        pillar = d.get("pillar")
        out.append(
            _result(
                src,
                pillar if pillar else None,
                float(d.get("confidence", 0.5)),
                d.get("rationale", "claude: keine Begruendung"),
            )
        )
    return out


def _shorten(text: str | None, limit: int = 500) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= limit else text[:limit] + " ..."


_USER_TEMPLATE = """Ordne jeden Datenpunkt genau einer strategischen Saeule zu oder markiere ihn
als strategie-fern.

Saeulen:
{pillars}

Antworte mit einem JSON-Array. Ein Objekt je Datenpunkt:
- "index": die Nummer des Datenpunkts
- "pillar": der key der Saeule, oder null wenn strategie-fern
- "confidence": Zahl zwischen 0 und 1
- "rationale": kurze Begruendung (ein Satz)

Datenpunkte:
{items}

Nur das JSON-Array, keine Prosa.
"""
