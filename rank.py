"""Ranking: which assets did something unusual, and what was it?

One lead note per asset (its highest-scoring note; the rest become context
lines), then assets sorted by that score.
"""


def rank(notes, top_n):
    """Returns (top notes, number of assets with at least one note)."""
    by_asset = {}
    for n in notes:
        by_asset.setdefault(n["ticker"], []).append(n)

    leads = []
    for asset_notes in by_asset.values():
        asset_notes.sort(key=lambda n: n["score"], reverse=True)
        lead = dict(asset_notes[0])
        lead["also"] = asset_notes[1:]
        leads.append(lead)

    leads.sort(key=lambda n: n["score"], reverse=True)
    return leads[:top_n], len(leads)
