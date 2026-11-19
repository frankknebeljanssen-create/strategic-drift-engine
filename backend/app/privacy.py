"""Pseudonymisierung der Ausgabe: Rolle plus Team statt Name oder Kuerzel.

Die Analyse arbeitet auf den Originaldaten. Erst die Ausgabe (Dump fuer das
Frontend, /evidence-API) wird bereinigt: Autoren-Kuerzel und Personennamen in
Nachrichtentexten werden durch ein stabiles Label aus Team und Rolle ersetzt.
Dieselbe Person bekommt ueberall dasselbe Label, damit Muster erkennbar
bleiben, ohne dass ein Beleg auf einen Namen zurueckfuehrt.

Reine Funktionen ohne DB- oder Anthropic-Abhaengigkeit.
"""

from __future__ import annotations

import re


def role_label(person: dict) -> str:
    """Label aus Team und Rolle, z.B. "Engineering, Senior Engineer"."""
    team = (person.get("team") or "").strip()
    role = (person.get("role") or "").strip()
    if not role:
        return team or "Unbekannt"
    if not team or team.lower() in role.lower():
        return role  # Team steckt schon in der Rolle ("Head of Engineering")
    return f"{team}, {role}"


class Pseudonymizer:
    """Ersetzt Autoren-IDs und Personennamen durch Rolle-plus-Team-Labels."""

    def __init__(self, people: list[dict]):
        self._labels = {p["id"]: role_label(p) for p in people}
        pairs: list[tuple[str, str]] = []
        for p in people:
            label = self._labels[p["id"]]
            name = (p.get("name") or "").strip()
            parts = name.split()
            for token in ([name, p["id"]] + (parts if len(parts) > 1 else [])):
                if len(token) >= 3:
                    pairs.append((token, label))
        # Laengste Treffer zuerst, damit "Sarah Mendes" vor "Sarah" greift.
        pairs.sort(key=lambda t: -len(t[0]))
        self._pattern = None
        self._by_token: dict[str, str] = {}
        if pairs:
            self._by_token = {tok.lower(): lab for tok, lab in pairs}
            alt = "|".join(re.escape(tok) for tok, _ in pairs)
            # Optionales Genitiv-s ("Sarahs") wird mit ersetzt.
            self._pattern = re.compile(rf"\b(?:{alt})(?:s)?\b", re.IGNORECASE)

    def author(self, author_id: str | None) -> str | None:
        """Label fuer eine Autoren-ID, None bleibt None (z.B. Kalender)."""
        if author_id is None:
            return None
        return self._labels.get(author_id, "Unbekannt")

    def text(self, value: str | None) -> str:
        """Namen und Kuerzel im Text durch [Label] ersetzen."""
        if not value or self._pattern is None:
            return value or ""

        def sub(m: re.Match) -> str:
            tok = m.group(0).lower()
            label = self._by_token.get(tok)
            if label is None and tok.endswith("s"):
                label = self._by_token.get(tok[:-1])
            return f"[{label}]" if label else m.group(0)

        return self._pattern.sub(sub, value)
