"""Shared rules for the Papy Weekly routine: quotas, genre guards, normalisation."""
import re
import unicodedata

PLAYLIST_SIZE = 100

# Exact number of tracks per category. Dict order = playlist order (electro and
# non-electro blocks alternate so the playlist never feels "tech only").
QUOTAS = {
    "rave_ht_fr": 22,
    "rap_fr_drill": 22,
    "frenchcore_uptempo": 10,
    "metal": 16,
    "hardstyle_rawstyle": 6,
    "funk_nudisco": 12,
    "acid_hardtek": 6,
    "metal_techno_remix": 6,
}

# Categories filled by Spotify search instead of Deezer expansion.
SEARCH_ONLY = {"metal_techno_remix"}

HARD = r"\b(techno|tekno|hardtek|tribecore|frapcore|frenchcore|uptempo|hardstyle|rawstyle|gabber|schranz|acid|rave|kick edit)\b"
BANNED = r"reggae|reggaeton|dembow"
JUNK = r"\b(intro|interlude|skit|outro|karaoke|instrumental|sped up|slowed|nightcore|8d audio|acapella|a cappella)\b"

# category -> (forbidden regex, required regex), applied to "title album"
GUARDS = {
    "rap_fr_drill": (HARD + r"|remix|bootleg|hardcore", None),
    "metal": (HARD + r"|remix|bootleg", None),
    "funk_nudisco": (HARD + r"|hardcore", None),
    "metal_techno_remix": (None, r"techno|tekno|rave|remix|version|edit|bootleg|rework|flip|hard"),
}


def norm(s):
    s = unicodedata.normalize("NFKD", (s or "").lower()).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s).strip()


def base_title(title):
    t = re.sub(r"\(.*?\)|\[.*?\]", "", norm(title))
    return re.sub(r"\s+-\s+.*$|\s(feat|ft)\..*$", "", t).strip()


def track_key(title, artist):
    return base_title(title) + "|" + norm(artist)


def guard_error(category, text):
    """Return why a track does not belong to its category, or None."""
    text = norm(text)
    if re.search(BANNED, text):
        return "genre interdit (reggae/reggaeton)"
    forbidden, required = GUARDS.get(category, (None, None))
    if forbidden and re.search(forbidden, text):
        return f"version électro/remix dans {category}"
    if required and not re.search(required, text):
        return "pas une version techno/remix"
    return None


def read_names(path):
    try:
        return {norm(line) for line in open(path) if line.strip()}
    except FileNotFoundError:
        return set()


def read_excluded(path):
    """exclude.txt lines: 'spotify_id|title|artist'. Returns (ids, track keys)."""
    ids, keys = set(), set()
    try:
        for line in open(path):
            parts = [p.strip() for p in line.split("|")]
            if parts and re.fullmatch(r"[0-9A-Za-z]{22}", parts[0]):
                ids.add(parts[0])
            if len(parts) >= 3:
                keys.add(track_key(parts[1], parts[2]))
    except FileNotFoundError:
        pass
    return ids, keys
