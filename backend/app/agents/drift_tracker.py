"""Agent 3: Drift Tracker.

Teilt den Analysezeitraum in Fenster (Standard 15 Tage) und berechnet je Fenster
und Saeule ist_anteil (Anteil an den ZUGEORDNETEN Datenpunkten des Fensters,
strategie-ferne werden separat gezaehlt), soll_anteil und drift = ist - soll.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta


def to_date(value) -> date:
    """Robuste Datumsbehandlung: datetime, date oder ISO-String (auch mit Offset/Z)."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        s = value.strip().replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(s).date()
        except ValueError:
            return date.fromisoformat(s[:10])
    raise TypeError(f"Kein Datum: {value!r}")


def make_windows(window_start, window_end, bucket_days: int) -> list[tuple[date, date]]:
    """Zerlegt [start, end] in zusammenhaengende Fenster von je bucket_days Tagen."""
    start = to_date(window_start)
    end = to_date(window_end)
    if bucket_days < 1:
        raise ValueError("bucket_days muss >= 1 sein")

    windows: list[tuple[date, date]] = []
    cur = start
    while cur <= end:
        w_end = min(cur + timedelta(days=bucket_days - 1), end)
        windows.append((cur, w_end))
        cur = cur + timedelta(days=bucket_days)
    return windows


def window_index(windows: list[tuple[date, date]], start: date, bucket_days: int, d: date) -> int:
    """Fensterindex eines Datums, geklemmt auf gueltigen Bereich."""
    idx = (d - start).days // bucket_days
    if idx < 0:
        return 0
    if idx >= len(windows):
        return len(windows) - 1
    return idx


def track_drift(
    sources: list[dict],
    mappings: list[dict],
    pillars: list[dict],
    window_start,
    window_end,
    bucket_days: int = 15,
) -> dict:
    """Berechnet Drift je Fenster und Saeule.

    Rueckgabe: {"windows": [(start, end), ...], "aggregates": [ {...}, ... ]}.
    Ein Aggregat je (Fenster, Saeule): window_index, window_start, window_end,
    pillar_key, ist_anteil, soll_anteil, drift, n_sources, n_assigned, n_off.
    """
    start = to_date(window_start)
    windows = make_windows(window_start, window_end, bucket_days)
    src_ts = {s["id"]: to_date(s["ts"]) for s in sources if s.get("ts") is not None}

    pillar_keys = [p["key"] for p in pillars]
    soll = {p["key"]: float(p.get("soll_gewicht") or 0.0) for p in pillars}

    n_assigned = [0] * len(windows)
    n_off = [0] * len(windows)
    counts = [dict.fromkeys(pillar_keys, 0) for _ in windows]

    for m in mappings:
        d = src_ts.get(m["source_id"])
        if d is None:
            continue
        wi = window_index(windows, start, bucket_days, d)
        key = m["pillar_key"]
        if key is None:
            n_off[wi] += 1
        else:
            n_assigned[wi] += 1
            if key in counts[wi]:
                counts[wi][key] += 1

    aggregates = []
    for wi, (w_start, w_end) in enumerate(windows):
        assigned = n_assigned[wi]
        for key in pillar_keys:
            n = counts[wi][key]
            ist = (n / assigned) if assigned else 0.0
            aggregates.append(
                {
                    "window_index": wi,
                    "window_start": w_start,
                    "window_end": w_end,
                    "pillar_key": key,
                    "ist_anteil": round(ist, 4),
                    "soll_anteil": round(soll[key], 4),
                    "drift": round(ist - soll[key], 4),
                    "n_sources": n,
                    "n_assigned": assigned,
                    "n_off": n_off[wi],
                }
            )

    return {"windows": windows, "aggregates": aggregates}
