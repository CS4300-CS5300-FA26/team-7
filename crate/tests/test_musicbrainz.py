from unittest.mock import patch, Mock 

from django.test import TestCase 

from crate import musicbrainz

# Realistically-shaped MusicBrainz /recording search response
SAMPLE = {
    "count": 2,
    "recordings": [
        {
            "id": "mbid-1",
            "title": "Creep",
            "length": 238000,
            "artist-credit": [{"name": "Radiohead", "joinphrase": ""}],
            "releases": [{"id": "rel-1", "title": "Pablo Honey", "date": "1993-02-22"}],
        },
        {
            "id": "mbid-2",
            "title": "Stronger",
            "length": None,  # length often missing
            "artist-credit": [
                {"name": "Kanye West", "joinphrase": " feat. "},
                {"name": "Daft Punk", "joinphrase": ""},
            ],
            "releases": [],  # releases can be empty
        },
    ],
}

EMPTY = {"count": 0, "recordings": []}

class ParseTests(TestCase):
    def test_parses_basic_recording(self):
        songs = musicbrainz._parse(SAMPLE)
        self.assertEqual(songs[0]["title"], "Creep")
        self.assertEqual(songs[0]["artist"], "Radiohead")
        self.assertEqual(songs[0]["album"], "Pablo Honey")
        self.assertEqual(songs[0]["length"], "3:58")   # 238000 ms
        self.assertEqual(songs[0]["mbid"], "mbid-1")

    def test_joins_collaborating_artists(self):
        songs = musicbrainz._parse(SAMPLE)
        self.assertEqual(songs[1]["artist"], "Kanye West feat. Daft Punk")

    def test_missing_length_and_release_do_not_crash(self):
        songs = musicbrainz._parse(SAMPLE)
        self.assertEqual(songs[1]["length"], "")
        self.assertEqual(songs[1]["album"], "")

    def test_empty_response(self):
        self.assertEqual(musicbrainz._parse(EMPTY), [])


class SearchTests(TestCase):
    @patch("crate.musicbrainz.requests.get")
    def test_sends_user_agent_and_parses(self, mock_get):
        resp = Mock()
        resp.json.return_value = SAMPLE 
        resp.raise_for_status.return_value = None 
        mock_get.return_value = resp 

        songs, total = musicbrainz.search_songs("radiohead creep")

        args, kwargs = mock_get.call_args
        self.assertEqual(args[0], musicbrainz.SEARCH_URL)
        self.assertEqual(kwargs["params"]["query"], "radiohead creep")
        self.assertIn("User-Agent", kwargs["headers"])          # required by MusicBrainz
        self.assertTrue(kwargs["headers"]["User-Agent"])
        self.assertEqual(songs[0]["title"], "Creep")

    @patch("crate.musicbrainz.requests.get")
    def test_http_error_propagates(self, mock_get):
        resp = Mock()
        resp.raise_for_status.side_effect = musicbrainz.requests.HTTPError("503")
        mock_get.return_value = resp 
        with self.assertRaises(musicbrainz.requests.HTTPError):
            musicbrainz.search_songs("x")