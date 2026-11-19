"""Thin client for the iTunes Search API (song search).

No API key and no signup. Good consumer-search relevance, so a query like
"shake it off" returns the well-known recording first. Returns flat dicts
with the same keys the search template already uses (title/artist/album/length),
plus artwork and an itunes link. The view adds `source` and `audio_url`.
"""
import requests

SEARCH_URL = "https://itunes.apple.com/search"

def search_songs(query, *, limit=15, timeout=10):
    """Return a list of song-metadata dicts matching `query`."""
    params = {"term": query, "entity": "song", "media": "music", "limit": limit}
    response = requests.get(SEARCH_URL, params=params, timeout=timeout)
    response.raise_for_status()
    return _parse(response.json())

def _parse(data):
    songs = []
    for r in data.get("results", []):
        songs.append({
            "title": r.get("trackName", ""),
            "artist": r.get("artistName", ""),
            "album": r.get("collectionName", ""),
            "length": _format_length(r.get("trackTimeMillis")),
            "artwork": r.get("artworkUrl100", ""),
            "itunes_url": r.get("trackViewUrl", ""),
        })
    return songs 

def _format_length(ms):
    if not ms:
        return ""
    total_seconds = round(ms / 1000)
    return f"{total_seconds // 60}:{total_seconds % 60:02d}"