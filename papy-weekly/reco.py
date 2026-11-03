#!/usr/bin/env python3
"""Papy Weekly recommender.

Expands the user's seed artists per category through Deezer "related artists"
(listener-based similarity), ranks candidate artists by how many seeds point to
them, then picks ONE track per artist (weekly rotation among its top tracks).

Inputs (WORKDIR, default /tmp/papy/):
  seeds.json   {"category": ["Seed artist", ...], ...}
  known.txt    artists the user already listens to (one per line)
  recent.txt   artists currently in Papy Weekly / Papy Daily (one per line)
  exclude.txt  "spotify_id|title|artist" lines: tracks never to propose
Output:
  candidates.json  {"category": [{artist, title, isrc, album, score, known, because}, ...]}
Exit codes: 0 ok, 2 bad input, 3 Deezer unreachable.
"""
import json
import math
import random
import re
import sys
import time
from collections import defaultdict
from datetime import date
from urllib.parse import urlencode
from urllib.request import Request, urlopen

sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
from rules import JUNK, QUOTAS, SEARCH_ONLY, guard_error, norm, read_excluded, read_names, track_key

WORKDIR = (sys.argv[1] if len(sys.argv) > 1 else "/tmp/papy").rstrip("/") + "/"
BUFFER = 1.6  # candidates per slot, absorbs tracks missing on Spotify or rejected on review
KNOWN_FACTOR = 0.5  # discovery first: artists the user already plays are penalised
RECENT_FACTOR = 0.15  # weekly rotation: artists proposed last time are strongly penalised
SECOND_HOP = 6  # best new artists per category whose own related artists are explored


def get(path, **params):
    url = "https://api.deezer.com/" + path + ("?" + urlencode(params) if params else "")
    for _ in range(4):
        try:
            with urlopen(Request(url, headers={"User-Agent": "papy-weekly"}), timeout=15) as r:
                data = json.load(r)
            time.sleep(0.12)  # Deezer quota: 50 requests / 5 s
            if isinstance(data, dict) and "error" in data:
                if data["error"].get("code") == 4:  # quota exceeded
                    time.sleep(3)
                    continue
                return None
            return data
        except Exception:
            time.sleep(1.5)
    raise ConnectionError(url)


def resolve(name):
    hits = (get("search/artist", q=name, limit=10) or {}).get("data", [])
    exact = [h for h in hits if norm(h["name"]) == norm(name)]
    pool = exact or hits[:1]
    return max(pool, key=lambda h: h.get("nb_fan", 0)) if pool else None


def related(artist_id):
    return (get(f"artist/{artist_id}/related", limit=25) or {}).get("data", [])


def pick_track(artist, category, week, excluded_keys, taken):
    tracks = []
    for t in (get(f"artist/{artist['id']}/top", limit=10) or {}).get("data", []):
        title, album = t.get("title", ""), (t.get("album") or {}).get("title", "")
        if (t.get("artist") or {}).get("id") != artist["id"]:
            continue  # keep tracks where this artist is the main artist
        if t.get("duration", 0) < 90 or re.search(JUNK, norm(f"{title} {album}")):
            continue
        if guard_error(category, f"{title} {album}"):
            continue
        key = track_key(title, artist["name"])
        if key in excluded_keys or key in taken:
            continue
        tracks.append(t)
    if not tracks:
        return None
    top = tracks[:5]
    t = random.Random(f"{week}-{artist['id']}").choices(top, weights=[5, 4, 3, 2, 1][: len(top)])[0]
    full = get(f"track/{t['id']}") or {}
    taken.add(track_key(t["title"], artist["name"]))
    return {
        "title": t["title"],
        "isrc": full.get("isrc"),
        "album": (t.get("album") or {}).get("title", ""),
        "contributors": [c["name"] for c in full.get("contributors", [])] or [artist["name"]],
    }


def main():
    try:
        seeds = json.load(open(WORKDIR + "seeds.json"))
    except Exception as e:
        print(f"seeds.json illisible : {e}")
        sys.exit(2)
    known = read_names(WORKDIR + "known.txt")
    recent = read_names(WORKDIR + "recent.txt")
    _, excluded_keys = read_excluded(WORKDIR + "exclude.txt")
    seed_names = {norm(s) for names in seeds.values() for s in names}
    year, wk, _ = date.today().isocalendar()
    week = f"{year}-W{wk}"

    try:
        get("search/artist", q="daft punk", limit=1)
    except ConnectionError:
        print("DEEZER_UNREACHABLE")
        sys.exit(3)

    scores = defaultdict(lambda: defaultdict(float))  # artist -> category -> score
    info = {}  # artist -> {"id", "name", "because": {category: set(seed names)}}

    def add(category, artist, weight, because):
        n = norm(artist["name"])
        if n in seed_names:
            return
        scores[n][category] += weight
        entry = info.setdefault(n, {"id": artist["id"], "name": artist["name"], "because": defaultdict(set)})
        entry["because"][category] |= because

    for category, names in seeds.items():
        if category not in QUOTAS or category in SEARCH_ONLY:
            continue
        for name in names:
            seed = resolve(name)
            if not seed:
                print(f"  [{category}] seed introuvable sur Deezer : {name}")
                continue
            rel = related(seed["id"])
            for rank, artist in enumerate(rel):
                add(category, artist, 1 - rank / len(rel), {name})
        hop = sorted(
            (n for n in scores if category in scores[n] and n not in known and n not in recent),
            key=lambda n: scores[n][category],
            reverse=True,
        )[:SECOND_HOP]
        for n in hop:
            rel = related(info[n]["id"])
            for rank, artist in enumerate(rel):
                add(category, artist, 0.5 * (1 - rank / len(rel)), info[n]["because"][category])

    ranked = defaultdict(list)
    for n, by_category in scores.items():
        category = max(by_category, key=by_category.get)  # one artist = one category
        score = by_category[category] * (RECENT_FACTOR if n in recent else KNOWN_FACTOR if n in known else 1)
        ranked[category].append((score, n))

    out, taken, credited = {}, set(), defaultdict(int)
    for category in seeds:
        if category not in QUOTAS or category in SEARCH_ONLY:
            continue
        need = math.ceil(QUOTAS[category] * BUFFER)
        picks = []
        for score, n in sorted(ranked[category], reverse=True):
            if len(picks) >= need:
                break
            artist = info[n]
            if credited[n] >= 2:
                continue  # already featured on 2 picked tracks
            track = pick_track(artist, category, week, excluded_keys, taken)
            if track and all(credited[norm(c)] < 2 for c in track["contributors"]):
                for c in track["contributors"]:
                    credited[norm(c)] += 1
                picks.append({
                    "artist": artist["name"],
                    **track,
                    "score": round(score, 2),
                    "known": n in known,
                    "because": sorted(artist["because"][category])[:4],
                })
        out[category] = picks
        flag = "" if len(picks) >= QUOTAS[category] else "  ⚠ MOINS QUE LE QUOTA : ajoute des seeds"
        print(f"{category}: {len(picks)} candidats (quota {QUOTAS[category]}){flag}")
        for p in picks[:6]:
            print(f"   {p['artist']} — {p['title']}  (score {p['score']}, via {', '.join(p['because'])})")

    json.dump(out, open(WORKDIR + "candidates.json", "w"), ensure_ascii=False, indent=1)
    print(f"→ {WORKDIR}candidates.json")


if __name__ == "__main__":
    main()
