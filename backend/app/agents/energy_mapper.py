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
# Bei Gleichstand gewinnt die zuerst genannte Saeule (Reihenfolge dieses Dicts).
# customer_led bewusst eng gehalten (nur starke Kundensignale), damit generelle
# Prozess-/Leadership-Chatter nicht faelschlich Pillar 1 aufblaeht.
_KEYWORDS = {
    "customer_led_growth": [
        "nps", "kunde", "kunden", "customer", "discovery", "retention",
        "interview", "churn", "customer success", "customer-anker",
        "kundengespraech",
    ],
    "quality_over_speed": [
        "qualitaet", "quality", "test", "coverage", "bug", "bugs", "qa",
        "regression", "triage", "reife", "stabil", "zuverlaessig",
        "technische schuld", "tech debt", "veto",
    ],
    "enterprise_ready": [
        "enterprise", "soc2", "soc 2", "sso", "saml", "azure ad", "okta",
        "audit", "audit-log", "compliance", "dsgvo", "iso 27001", "deal",
        "pipeline", "playbook", "zertifiz", "series c", "prospect",
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
    titles = {p["key"]: p.get("title", p["key"]) for p in pillars}
    return [_map_one_mock(src, titles) for src in sources]


# --- Mock ------------------------------------------------------------------

# Menschenlesbare Labels fuer strategie-ferne Kalender-Kategorien.
_OFF_STRATEGY_LABELS = {
    "leadership": "internal leadership chatter",
    "neutral": "neutral admin, 1:1s or all-hands",
    "speed_delivery": "speed and delivery focus",
}


def _map_one_mock(src: dict, titles: dict[str, str]) -> dict:
    if src.get("source_type") == "calendar":
        return _map_calendar_mock(src, titles)
    return _map_text_mock(src, titles)


def _map_calendar_mock(src: dict, titles: dict[str, str]) -> dict:
    category = (src.get("meta") or {}).get("category")
    pillar = _CALENDAR_MAP.get(category)
    if pillar is None:
        label = _OFF_STRATEGY_LABELS.get(category, f"category '{category}'")
        return _result(
            src,
            None,
            0.6,
            rationale=f"mock: calendar category '{category}' is off-strategy",
            signals=[f"calendar category: {category} (no pillar mapping)"],
            contribution=f"Off-strategy: this event is {label}, not tied to any pillar.",
        )
    title = titles.get(pillar, pillar)
    return _result(
        src,
        pillar,
        0.9,
        rationale=f"mock: calendar category '{category}' -> {pillar}",
        signals=[f"calendar category: {category} -> {pillar}"],
        contribution=f"Contributes to {title}: calendar event categorized as '{category}'.",
    )


def _map_text_mock(src: dict, titles: dict[str, str]) -> dict:
    text = (src.get("text") or "").lower()

    hits = {key: _hits(text, words) for key, words in _KEYWORDS.items()}
    scores = {key: total for key, (total, _matches) in hits.items()}
    # quality_negative-Signal von der Quality-Saeule abziehen.
    neg_total, neg_matched = _hits(text, _QUALITY_NEGATIVE)
    scores["quality_over_speed"] -= neg_total

    best_key = max(scores, key=scores.get)
    best_score = scores[best_key]

    # Signale: alle Keyword-Treffer, das quality_negative-Signal, dann Scores.
    signals = []
    for key, (_total, matches) in hits.items():
        if matches:
            signals.append(f"{key}: " + ", ".join(f"'{w}'" for w in matches))
    if neg_matched:
        signals.append(
            "quality_negative: " + ", ".join(f"'{w}'" for w in neg_matched)
        )
    signals.append(
        "scores: " + ", ".join(f"{k}={scores[k]}" for k in _KEYWORDS)
    )

    if best_score <= 0:
        any_pillar_hit = any(matches for _, matches in hits.values())
        if not any_pillar_hit and neg_total == 0:
            contribution = "Off-strategy: no keyword signals from any pillar."
            reason = "no pillar signals"
        elif not any_pillar_hit and neg_total > 0:
            contribution = (
                "Off-strategy: only speed and quality-negative keywords, "
                "no positive pillar signal."
            )
            reason = f"only quality_negative signal (neg={neg_total})"
        else:
            contribution = (
                "Off-strategy: pillar signals do not outweigh the "
                "quality-negative counter-signal."
            )
            reason = f"pillar signals cancelled by quality_negative (neg={neg_total})"
        return _result(
            src,
            None,
            0.5,
            rationale=f"mock: {reason} -> off-strategy",
            signals=signals,
            contribution=contribution,
        )

    signals.append(f"chosen: {best_key} (score {best_score})")
    confidence = min(0.95, 0.5 + 0.1 * best_score)
    title = titles.get(best_key, best_key)
    chosen_words = hits[best_key][1]
    kw_phrase = ", ".join(f"'{w}'" for w in chosen_words[:3])
    contribution = (
        f"Contributes to {title}: keywords {kw_phrase} outweigh other signals."
        if kw_phrase
        else f"Contributes to {title} on keyword scoring."
    )
    return _result(
        src,
        best_key,
        round(confidence, 3),
        rationale=f"mock: keyword score {best_key}={best_score} (neg={neg_total})",
        signals=signals,
        contribution=contribution,
    )


def _hits(text: str, words: list[str]) -> tuple[int, list[str]]:
    """Zaehlt Substring-Vorkommen und gibt die tatsaechlich getroffenen Wortformen zurueck.

    Reihenfolge folgt der Keyword-Liste, damit die Signale deterministisch sind.
    """
    matched: list[str] = []
    total = 0
    for w in words:
        n = text.count(w)
        if n > 0:
            matched.append(w)
            total += n
    return total, matched


def _result(
    src: dict,
    pillar_key,
    confidence: float,
    rationale: str,
    signals: list[str] | None = None,
    contribution: str = "",
) -> dict:
    return {
        "source_id": src["id"],
        "pillar_key": pillar_key,
        "confidence": confidence,
        "rationale": rationale,
        "signals": signals or [],
        "contribution": contribution,
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
        rationale = d.get("rationale", "claude: no rationale")
        # Fuer den claude-Pfad reichen wir die Rationale als contribution
        # durch; der Mock-Pfad liefert strukturierte signals/contribution.
        out.append(
            _result(
                src,
                pillar if pillar else None,
                float(d.get("confidence", 0.5)),
                rationale,
                signals=[],
                contribution=rationale,
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
