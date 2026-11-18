from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse 

from crate import views 
from crate.models import Song

from .helpers import STRONG_PASSWORD

User = get_user_model()

# What the mocked MusicBrainz client returns
WEB = [
    {"title": "Creep", "artist": "Radiohead", "album": "Pablo Honey", "length": "3:58", "mbid": "m1"},
    {"title": "Karma Police", "artist": "Radiohead", "album": "OK Computer", "length": "4:21", "mbid": "m2"},
]


class SearchWebResultsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("alice", password=STRONG_PASSWORD)
        self.client.force_login(self.user)
        self.url = reverse("search")

    @patch("crate.views.musicbrainz.search_songs", return_value=WEB)
    def test_web_results_shown_when_searching(self, _mock):
        r = self.client.get(self.url, {"q": "radiohead"})
        titles = [w["title"] for w in r.context["web_results"]]
        self.assertEqual(titles, ["Creep", "Karma Police"])

    @patch("crate.views.musicbrainz.search_songs", return_value=WEB)
    def test_web_results_get_royalty_free_url_and_source(self, _mock):
        r = self.client.get(self.url, {"q": "radiohead"})
        w = r.context["web_results"][0]
        self.assertEqual(w["source"], "web")
        self.assertEqual(w["audio_url"], views.ROYALTY_FREE_AUDIO_URL)

    @patch("crate.views.musicbrainz.search_songs", return_value=WEB)
    def test_owned_song_is_deduped_from_web_results(self, _mock):
        # Alice owns "Creep" by Radiohead -> it should NOT appear in web_results
        Song.objects.create(title="Creep", artist="Radiohead", genre="Rock",
                            minutes=3, seconds=58, user=self.user)
        r = self.client.get(self.url, {"q": "radiohead"})
        web_titles = [w["title"] for w in r.context["web_results"]]
        self.assertNotIn("Creep", web_titles)        # shown in library instead
        self.assertIn("Karma Police", web_titles)    # not owned -> still web

    @patch("crate.views.musicbrainz.search_songs", return_value=WEB)
    def test_no_api_call_without_a_query(self, mock_search):
        self.client.get(self.url)                    # no q
        mock_search.assert_not_called()

    @patch("crate.views.musicbrainz.search_songs",
           side_effect=views.requests.RequestException("down"))
    def test_api_failure_degrades_gracefully(self, _mock):
        Song.objects.create(title="Mine", artist="Me", genre="Rock",
                            minutes=2, seconds=0, user=self.user)
        r = self.client.get(self.url, {"q": "me"})
        self.assertTrue(r.context["web_error"])          # flagged
        self.assertEqual(r.context["web_results"], [])    # no web results
        self.assertEqual(len(r.context["songs"]), 1)      # local search still works