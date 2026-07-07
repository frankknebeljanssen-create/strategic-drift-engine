"""Agent 1: Pillar Extractor.

Zerlegt das Strategiedokument in strategische Saeulen (key, title, grundsatz,
kriterien, soll_gewicht). soll_gewicht wird auf Summe 1 normalisiert.

claude-Modus: Claude parst das Dokument. mock-Modus: erkennt die drei bekannten
TechCo-Saeulen anhand der "## Pillar N: ..."-Ueberschriften, ohne API.
"""

from __future__ import annotations

import re

from app.agents.llm import call_claude, parse_json

_SYSTEM = (
    "Du bist ein Strategie-Analyst. Du zerlegst ein Strategiedokument in seine "
    "strategischen Saeulen (Pillars) und antwortest ausschliesslich mit JSON."
)

_USER_TEMPLATE = """Zerlege das folgende Strategiedokument in seine strategischen Saeulen.

Gib ein JSON-Array zurueck. Jedes Element:
- "key": kurzer snake_case-Identifier (englisch), z.B. "customer_led_growth"
- "title": Titel der Saeule
- "grundsatz": der Grundsatz in einem Satz
- "kriterien": Array kurzer, operativer Kriterien (Strings)
- "soll_gewicht": relative strategische Gewichtung als Zahl (die Gewichte werden
  spaeter normalisiert, sie muessen sich noch nicht zu 1 summieren)

Nur das JSON-Array, keine Prosa.

--- STRATEGIEDOKUMENT ---
{strategy}
"""

# Zuordnung bekannter Ueberschriften zu stabilen keys (mock-Modus).
_KNOWN_KEYS = [
    (re.compile(r"customer[- ]led", re.I), "customer_led_growth"),
    (re.compile(r"quality", re.I), "quality_over_speed"),
    (re.compile(r"enterprise", re.I), "enterprise_ready"),
]


def extract_pillars(strategy_text: str, mode: str) -> list[dict]:
    """Extrahiert die Saeulen. mode: 'claude' oder 'mock'."""
    if mode == "claude":
        pillars = _extract_claude(strategy_text)
    else:
        pillars = _extract_mock(strategy_text)
    return _normalize_weights(pillars)


def _extract_claude(strategy_text: str) -> list[dict]:
    raw = call_claude(_SYSTEM, _USER_TEMPLATE.format(strategy=strategy_text))
    data = parse_json(raw)
    if not isinstance(data, list):
        raise ValueError("Pillar Extractor: erwartet ein JSON-Array von Saeulen")
    out = []
    for item in data:
        out.append(
            {
                "key": item["key"],
                "title": item.get("title", item["key"]),
                "grundsatz": item.get("grundsatz", ""),
                "kriterien": item.get("kriterien", []),
                "soll_gewicht": float(item.get("soll_gewicht", 1.0)),
            }
        )
    return out


def _extract_mock(strategy_text: str) -> list[dict]:
    """Parst die "## Pillar N: <Titel>"-Bloecke und mappt sie auf bekannte keys."""
    pillars = []
    for title, body in _iter_pillar_sections(strategy_text):
        key = _key_for_title(title)
        if key is None:
            continue  # nur die bekannten TechCo-Saeulen
        pillars.append(
            {
                "key": key,
                "title": title,
                "grundsatz": _extract_grundsatz(body),
                "kriterien": _extract_kriterien(body),
                "soll_gewicht": 1.0,  # gleich gewichtet, wird normalisiert
            }
        )
    if not pillars:
        raise ValueError("Pillar Extractor (mock): keine bekannten Saeulen gefunden")
    return pillars


def _iter_pillar_sections(text: str):
    """Liefert (title, body) je "## Pillar N: <Titel>"-Abschnitt."""
    pattern = re.compile(r"^##\s+Pillar\s+\d+:\s*(.+?)\s*$", re.M)
    matches = list(pattern.finditer(text))
    for i, m in enumerate(matches):
        title = m.group(1).strip()
        body_start = m.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        yield title, text[body_start:body_end]


def _key_for_title(title: str) -> str | None:
    for rx, key in _KNOWN_KEYS:
        if rx.search(title):
            return key
    return None


def _extract_grundsatz(body: str) -> str:
    """Erster nicht-leerer Absatz unter '### Grundsatz'."""
    m = re.search(r"###\s+Grundsatz\s*(.+?)(?=\n###|\Z)", body, re.S | re.I)
    if not m:
        return ""
    for para in m.group(1).strip().split("\n\n"):
        para = para.strip()
        if para:
            return " ".join(para.split())
    return ""


def _extract_kriterien(body: str) -> list[str]:
    """Bullet-Punkte unter '### Was das operativ bedeutet'."""
    m = re.search(
        r"###\s+Was das operativ bedeutet\s*(.+?)(?=\n###|\Z)", body, re.S | re.I
    )
    if not m:
        return []
    kriterien = []
    for line in m.group(1).splitlines():
        line = line.strip()
        if line.startswith("- "):
            kriterien.append(line[2:].strip())
    return kriterien


def _normalize_weights(pillars: list[dict]) -> list[dict]:
    """Normalisiert soll_gewicht auf Summe 1 (Gleichverteilung bei Summe 0)."""
    total = sum(p.get("soll_gewicht", 0) or 0 for p in pillars)
    n = len(pillars)
    for p in pillars:
        if total > 0:
            p["soll_gewicht"] = round(p["soll_gewicht"] / total, 3)
        else:
            p["soll_gewicht"] = round(1 / n, 3) if n else 0.0
    return pillars
