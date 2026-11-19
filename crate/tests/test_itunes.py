from unittest.mock import patch, Mock

from django.test import TestCase 
from crate import itunes 

SAMPLE = {
    "resultCount": 2,
    "results": [
        {"trackName": "Shake It Off", "artistName": "Taylor Swift", "collectionName": "1989",
         "trackTimeMillis": 219200, "artworkUrl100": "https://img/ts100.jpg",
         "trackViewUrl": "https://music.apple.com/ts"},
        {"trackName": "Partial", "artistName": "Someone"},
    ],
}
EMPTY = {"resultCount": 0, "results": []}

class ParseTests(TestCase):
    def test_parses_core_fields(self):
        s = itunes._parse(SAMPLE)[0]
        self.assertEqual(s["title"], "Shake It Off")
        self.assertEqual(s["artist"], "Taylor Swift")
        self.assertEqual(s["album"], "1989")
        self.assertEqual(s["length"], "3:39")
        self.assertEqual(s["artwork"], "https://img/ts100.jpg")

    def test_missing_fields_do_not_crash(self):
        s = itunes._parse(SAMPLE)[1]
        self.assertEqual(s["album"], "")
        self.assertEqual(s["length"], "")
        self.assertEqual(s["artwork"], "")

    def test_empty(self):
        self.assertEqual(itunes._parse(EMPTY), [])


class SearchTests(TestCase):
    @patch("crate.itunes.requests.get")
    def test_calls_api_and_parses(self, mock_get):
        resp = Mock()
        resp.json.return_value = SAMPLE 
        resp.raise_for_status.return_value = None 
        mock_get.return_value = resp 
        songs = itunes.search_songs("shake it off")
        args, kwargs = mock_get.call_args
        self.assertEqual(args[0], itunes.SEARCH_URL)
        self.assertEqual(kwargs["params"]["term"], "shake it off")
        self.assertEqual(kwargs["params"]["entity"], "song")
        self.assertEqual(songs[0]["artist"], "Taylor Swift")