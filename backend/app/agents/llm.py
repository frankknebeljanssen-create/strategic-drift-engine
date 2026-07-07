"""Duenner Anthropic-Wrapper plus robustes JSON-Parsing.

Wichtig: das anthropic-Paket wird erst INNERHALB von client() importiert (lazy),
damit der Mock-Modus komplett ohne installiertes anthropic-Paket laeuft. Auf
Modulebene darf nichts aus anthropic oder aus der Konfiguration gezogen werden.
"""

from __future__ import annotations

import json


def client():
    """Baut einen Anthropic-Client. Lazy-Import, damit der Mock-Modus ihn nie braucht."""
    from anthropic import Anthropic  # lazy: nur im claude-Modus vorhanden

    from app.config import get_settings

    settings = get_settings()
    if not settings.anthropic_api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY fehlt. Fuer --mode claude in .env setzen "
            "oder --mode mock verwenden."
        )
    return Anthropic(api_key=settings.anthropic_api_key)


def call_claude(system: str, user: str, max_tokens: int = 4096) -> str:
    """Ein Claude-Aufruf. Liefert den zusammengesetzten Text-Content zurueck."""
    from app.config import get_settings

    model = get_settings().anthropic_model
    resp = client().messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    # content ist eine Liste von Bloecken; nur Text-Bloecke einsammeln.
    parts = [block.text for block in resp.content if getattr(block, "type", None) == "text"]
    return "".join(parts)


def parse_json(text: str):
    """Extrahiert das erste balancierte JSON-Objekt oder -Array aus einem Text.

    Toleriert ```json-Fences und umgebende Prosa: sucht das erste { oder [,
    liest bis zur passenden schliessenden Klammer (unter Beachtung von Strings
    und Escapes) und parst genau diesen Ausschnitt.
    """
    if text is None:
        raise ValueError("parse_json: leerer Text")

    cleaned = _strip_fences(text)
    start = _first_json_start(cleaned)
    if start is None:
        raise ValueError("parse_json: kein JSON-Objekt/-Array gefunden")

    snippet = _balanced_slice(cleaned, start)
    return json.loads(snippet)


def _strip_fences(text: str) -> str:
    """Entfernt ```json ... ```-Fences, laesst den Inhalt stehen."""
    if "```" not in text:
        return text
    out = []
    in_fence = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue  # Fence-Zeile selbst verwerfen
        out.append(line)
    # Falls die Fences unbalanciert waren, gib den Originaltext zurueck.
    return "\n".join(out) if out else text


def _first_json_start(text: str) -> int | None:
    """Index des ersten { oder [ (was zuerst kommt)."""
    candidates = [i for i in (text.find("{"), text.find("[")) if i != -1]
    return min(candidates) if candidates else None


def _balanced_slice(text: str, start: int) -> str:
    """Schneidet ab start bis zur passenden schliessenden Klammer."""
    open_char = text[start]
    close_char = "}" if open_char == "{" else "]"
    depth = 0
    in_string = False
    escape = False

    for i in range(start, len(text)):
        ch = text[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == open_char:
            depth += 1
        elif ch == close_char:
            depth -= 1
            if depth == 0:
                return text[start : i + 1]

    raise ValueError("parse_json: keine passende schliessende Klammer gefunden")
