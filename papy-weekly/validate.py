#!/usr/bin/env python3
"""Papy Weekly gatekeeper: nothing is written to Spotify unless this prints PASS.

Input (WORKDIR, default /tmp/papy/):
  selection.json  [{"id", "title", "artists": [...], "album", "category", "isrc"?}, ...]
  exclude.txt / known.txt / recent.txt / candidates.json (same files as reco.py)
Output on PASS: final_ids.txt (playlist order) + the two batches of 50 IDs to add.
"""
import json
import math
import re
import sys
from collections import Counter

sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
from rules import PLAYLIST_SIZE, QUOTAS, SEARCH_ONLY, base_title, guard_error, norm, read_excluded, read_names, track_key

WORKDIR = (sys.argv[1] if len(sys.argv) > 1 else "/tmp/papy").rstrip("/") + "/"
MAX_KNOWN = 25  # at most 25 tracks whose main artist the user already plays
MAX_RECENT = 8  # at most 8 main artists already proposed in Papy Weekly / Daily
MIN_RECO_SHARE = 0.8  # >= 80 % of each recommended category comes from candidates.json


def main():
    sel = json.load(open(WORKDIR + "selection.json"))
    excluded_ids, excluded_keys = read_excluded(WORKDIR + "exclude.txt")
    known = read_names(WORKDIR + "known.txt")
    recent = read_names(WORKDIR + "recent.txt")
    try:
        cands = json.load(open(WORKDIR + "candidates.json"))
    except FileNotFoundError:
        cands = {}
    reco_isrc = {c["isrc"] for lst in cands.values() for c in lst if c.get("isrc")}
    reco_keys = {track_key(c["title"], c["artist"]) for lst in cands.values() for c in lst}

    errors, seen, keys = [], set(), set()
    counts, reco, main_artists, credited = Counter(), Counter(), Counter(), Counter()
    known_n = recent_n = 0

    for i, t in enumerate(sel):
        tid, cat, artists = t.get("id", ""), t.get("category"), t.get("artists") or [""]
        label = f"#{i} {t.get('title')} — {', '.join(artists)} [{cat}]"
        if not re.fullmatch(r"[0-9A-Za-z]{22}", tid):
            errors.append(f"ID Spotify invalide : {label}")
        if cat not in QUOTAS:
            errors.append(f"Catégorie inconnue : {label}")
            continue
        if tid in seen:
            errors.append(f"Doublon d'ID : {label}")
        seen.add(tid)
        key = track_key(t.get("title", ""), artists[0])
        if tid in excluded_ids or key in excluded_keys:
            errors.append(f"Déjà connu ou déjà proposé : {label}")
        if base_title(t.get("title", "")) + "|" + norm(artists[0]) in keys:
            errors.append(f"Même morceau en double : {label}")
        keys.add(key)
        reason = guard_error(cat, f"{t.get('title', '')} {t.get('album', '')}")
        if reason:
            errors.append(f"Hors catégorie ({reason}) : {label}")
        main_artists[norm(artists[0])] += 1
        for a in artists:
            credited[norm(a)] += 1
        known_n += norm(artists[0]) in known
        recent_n += norm(artists[0]) in recent
        counts[cat] += 1
        if t.get("isrc") in reco_isrc or key in reco_keys:
            reco[cat] += 1

    for a, n in main_artists.items():
        if n > 1:
            errors.append(f"Artiste principal répété : {a} ({n} titres, max 1)")
    for a, n in credited.items():
        if n > 2:
            errors.append(f"Artiste crédité trop souvent : {a} ({n} titres, max 2 en comptant les feats)")
    for cat, q in QUOTAS.items():
        if counts[cat] != q:
            diff = q - counts[cat]
            errors.append(f"Quota {cat} : {counts[cat]}/{q} ({'manque ' + str(diff) if diff > 0 else 'en trop ' + str(-diff)})")
        if cat not in SEARCH_ONLY and reco[cat] < math.floor(q * MIN_RECO_SHARE):
            errors.append(f"{cat} : seulement {reco[cat]} titres issus de candidates.json (min {math.floor(q * MIN_RECO_SHARE)})")
    if known_n > MAX_KNOWN:
        errors.append(f"Trop d'artistes déjà écoutés : {known_n} (max {MAX_KNOWN}) — c'est une playlist de découverte")
    if recent_n > MAX_RECENT:
        errors.append(f"Trop d'artistes déjà proposés récemment : {recent_n} (max {MAX_RECENT})")
    if len(sel) != PLAYLIST_SIZE:
        errors.append(f"Total : {len(sel)}/{PLAYLIST_SIZE}")

    print("Répartition : " + ", ".join(f"{c} {counts[c]}/{q}" for c, q in QUOTAS.items()))
    print(f"Artistes uniques : {len(main_artists)} · déjà écoutés : {known_n} · déjà proposés : {recent_n}")
    if errors:
        print(f"FAIL ({len(errors)} problèmes) — corrige selection.json et relance. N'écris RIEN sur Spotify.")
        print("\n".join("- " + e for e in errors))
        sys.exit(1)

    ids = [t["id"] for cat in QUOTAS for t in sel if t["category"] == cat]
    open(WORKDIR + "final_ids.txt", "w").write("\n".join(ids) + "\n")
    print("PASS")
    print("LOT 1 :", ",".join(ids[:50]))
    print("LOT 2 :", ",".join(ids[50:]))


if __name__ == "__main__":
    main()
