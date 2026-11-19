"""Thin client for the MusicBrainz API (song/recording search).

No API key: MusicBrainz is open, but it REQUIRES a descriptive User-Agent
identifying the app (it returns 403 otherwise) and allows at most ~1
request/second. Returns a list of flat dicts; the view adds the `source`
tag and the audio URL when it merges these with the user's own songs.
"""
import requests 

SEARCH_URL = "https://musicbrainz.org/ws/2/recording"
USER_AGENT = "Crate/1.0 ( https://www.crate-music.app )"

def search_songs(query, *, limit=20, offset = 0, timeout=10):
    """Return a list of song-metadata dicts matching `query`.

    Raises requests.RequestException on network/HTTP errors.
    """
    params = {"query": query, "fmt": "json", "limit": limit, "offset": offset, "dismax": "true"}
    headers = {"User-Agent": USER_AGENT}
    response = requests.get(SEARCH_URL, params=params, headers=headers, timeout=timeout)
    response.raise_for_status()
    data = response.json()
    return _parse(data), data.get("count", 0)

def _parse(data):
    songs = []
    for rec in data.get("recordings", []):
        releases = rec.get("releases", [])
        first_release = releases[0] if releases else {}
        songs.append({
            "title": rec.get("title", ""),
            "artist": _artist_name(rec.get("artist-credit", [])),
            "album": first_release.get("title", ""),
            "length": _format_length(rec.get("length")),
            "mbid": rec.get("id", ""),
        })
    return songs

def _artist_name(artist_credit):
    """Join a MusicBrainz artist-credit list (handles collaborations)."""
    parts = []
    for credit in artist_credit:
        parts.append(credit.get("name", ""))
        parts.append(credit.get("joinphrase", ""))
    return "".join(parts).strip()

def _format_length(ms):
    """Convert a duration in milliseconds to 'M:SS', or '' if unknown."""
    if not ms:
        return ""
    total_seconds = round(ms / 1000)
    return f"{total_seconds // 60}:{total_seconds % 60:02d}"