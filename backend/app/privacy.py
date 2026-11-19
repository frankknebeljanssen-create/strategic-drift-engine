"""Pseudonymisierung der Ausgabe: Team-Label statt Name, Kuerzel oder Rolle.

Die Analyse arbeitet auf den Originaldaten. Erst die Ausgabe (Dump fuer das
Frontend, /evidence-API) wird bereinigt: Autoren-Kuerzel, Personennamen und
Rollenbezeichnungen in Nachrichtentexten werden durch ein Team-Label ersetzt.

Schutzziel: Aus einem Label darf nie auf eine einzelne Person zu schliessen
sein, auch nicht fuer jemanden, der die Organisation kennt. Deshalb:
- keine Rollen im Label (Head of X, VP X, CEO, CTO sind einzigartig),
- Mindestgruppengroesse: Teams mit weniger als MIN_GROUP Personen werden zu
  einem gemeinsamen Sammel-Label zusammengefasst, sonst waere "Team Marketing"
  mit einer Person genauso ein Name wie "Head of Marketing".
Dieselbe Person bekommt ueberall dasselbe Label, damit Muster erkennbar bleiben.

Reine Funktionen ohne DB- oder Anthropic-Abhaengigkeit.
"""

from __future__ import annotations

import re
from collections import Counter

MIN_GROUP = 3
POOLED_LABEL = "Leitung und Stabsfunktionen"


def build_labels(people: list[dict]) -> dict[str, str]:
    """Team-Label je Person-ID, kleine Teams werden zusammengefasst."""
    sizes = Counter((p.get("team") or "").strip() for p in people)
    labels: dict[str, str] = {}
    for p in people:
        team = (p.get("team") or "").strip()
        if not team:
            labels[p["id"]] = POOLED_LABEL
        elif sizes[team] >= MIN_GROUP:
            labels[p["id"]] = f"Team {team}"
        else:
            labels[p["id"]] = POOLED_LABEL
    return labels


class Pseudonymizer:
    """Ersetzt Autoren-IDs, Namen und Rollentitel durch Team-Labels."""

    def __init__(self, people: list[dict]):
        self._labels = build_labels(people)
        pairs: list[tuple[str, str]] = []
        for p in people:
            label = self._labels[p["id"]]
            name = (p.get("name") or "").strip()
            parts = name.split()
            tokens = [name, p["id"]] + (parts if len(parts) > 1 else [])
            # Rollentitel sind einzigartig und damit selbst ein Identifikator.
            role = (p.get("role") or "").strip()
            if role:
                tokens.append(role)
            for token in tokens:
                if len(token) >= 3:
                    pairs.append((token, label))
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
        return self._labels.get(author_id, POOLED_LABEL)

    def text(self, value: str | None) -> str:
        """Namen, Kuerzel und Rollentitel im Text durch [Label] ersetzen."""
        if not value or self._pattern is None:
            return value or ""

        def sub(m: re.Match) -> str:
            tok = m.group(0).lower()
            label = self._by_token.get(tok)
            if label is None and tok.endswith("s"):
                label = self._by_token.get(tok[:-1])
            return f"[{label}]" if label else m.group(0)

        return self._pattern.sub(sub, value)
