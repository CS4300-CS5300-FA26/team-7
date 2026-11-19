from unittest.mock import patch
from urllib.parse import parse_qs

import requests
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from crate import musicbrainz, views
from crate.models import Song

from .helpers import STRONG_PASSWORD

User = get_user_model()


def web_result(title, artist="Some Artist"):
    return {"title": title, "artist": artist}


class PaginationTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user("alice", password=STRONG_PASSWORD)
        self.url = reverse("search")
        for i in range(45):  # 3 pages: 20 / 20 / 5
            Song.objects.create(
                title=f"Song {i:02d}", artist="Artist", genre="Rock", user=self.user
            )
        self.client.force_login(self.user)
        patcher = patch("crate.views.musicbrainz.search_songs", return_value=([], 0))
        patcher.start()
        self.addCleanup(patcher.stop)

    def get(self, **params):
        response = self.client.get(self.url, params)
        self.assertEqual(response.status_code, 200)
        return response

    def titles(self, **params):
        return [s.title for s in self.get(**params).context["songs"]]

    def test_pages_split_songs_into_twenty_per_page(self):
        self.assertEqual(len(self.titles()), 20)
        self.assertEqual(self.titles(page=2)[0], "Song 20")
        self.assertEqual(self.titles(page=3), [f"Song {i:02d}" for i in range(40, 45)])
        self.assertEqual(self.get().context["total_pages"], 3)

    def test_page_past_the_end_is_clamped_to_last_page(self):
        response = self.get(page=99)
        self.assertEqual(response.context["page"], 3)
        self.assertEqual(len(response.context["songs"]), 5)

    def test_invalid_zero_and_negative_pages_fall_back_to_first_page(self):
        for bad in ("abc", "", "0", "-3"):
            with self.subTest(page=bad):
                self.assertEqual(self.get(page=bad).context["page"], 1)

    def test_prev_next_flags(self):
        first, middle, last = self.get(), self.get(page=2), self.get(page=3)
        self.assertEqual(
            (first.context["has_prev"], first.context["has_next"]), (False, True)
        )
        self.assertEqual(
            (middle.context["has_prev"], middle.context["has_next"]), (True, True)
        )
        self.assertEqual(
            (last.context["has_prev"], last.context["has_next"]), (True, False)
        )

    def test_paging_keeps_sort_order(self):
        self.assertEqual(self.titles(sort="title", dir="desc", page=2)[0], "Song 24")

    def test_pager_shown_with_songs_and_hidden_without(self):
        self.assertContains(self.get(), 'aria-label="Search pages"')
        Song.objects.all().delete()
        self.assertNotContains(self.get(), 'aria-label="Search pages"')

    def test_base_query_keeps_search_sort_and_is_encoded(self):
        parsed = parse_qs(self.get(q="Song", sort="title", dir="desc").context["base_query"])
        self.assertEqual(parsed, {"q": ["Song"], "sort": ["title"], "dir": ["desc"]})
        self.assertIn("q=rock+%26+roll", self.get(q="rock & roll").context["base_query"])
        self.assertEqual(parse_qs(self.get().context["base_query"]), {"dir": ["asc"]})


class WebPaginationTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user("alice", password=STRONG_PASSWORD)
        self.url = reverse("search")
        Song.objects.create(title="Owned Song", artist="Owned Artist", user=self.user)
        self.client.force_login(self.user)
        patcher = patch("crate.views.musicbrainz.search_songs", return_value=([], 0))
        self.mock_search = patcher.start()
        self.addCleanup(patcher.stop)

    def get(self, **params):
        response = self.client.get(self.url, params)
        self.assertEqual(response.status_code, 200)
        return response

    def test_web_not_queried_without_search_term(self):
        self.get()
        self.get(q="   ")
        self.mock_search.assert_not_called()

    def test_page_number_maps_to_offset(self):
        self.mock_search.return_value = ([], 100)
        self.get(q="beatles", page=2)
        self.mock_search.assert_called_once_with("beatles", limit=20, offset=20)

    def test_total_pages_from_web_count_and_capped(self):
        self.mock_search.return_value = ([web_result("A")], 45)
        self.assertEqual(self.get(q="a").context["total_pages"], 3)
        self.mock_search.return_value = ([web_result("A")], 100_000)
        self.assertEqual(self.get(q="a").context["total_pages"], views.MAX_WEB_PAGES)

    def test_page_beyond_web_limit_is_clamped_and_refetched(self):
        self.mock_search.return_value = ([web_result("Last")], 100_000)
        response = self.get(q="a", page=999)
        self.assertEqual(response.context["page"], views.MAX_WEB_PAGES)
        self.mock_search.assert_called_once_with(
            "a", limit=20, offset=(views.MAX_WEB_PAGES - 1) * 20
        )
        self.assertEqual([r["title"] for r in response.context["web_results"]], ["Last"])

    def test_web_results_tagged_and_owned_songs_filtered(self):
        self.mock_search.return_value = (
            [web_result("  OWNED song ", " owned ARTIST"), web_result("New Song")],
            2,
        )
        results = self.get(q="song").context["web_results"]
        self.assertEqual([r["title"] for r in results], ["New Song"])
        self.assertEqual(results[0]["source"], "web")
        self.assertEqual(results[0]["audio_url"], views.ROYALTY_FREE_AUDIO_URL)

    def test_web_failure_shows_library_only_with_message(self):
        self.mock_search.side_effect = requests.RequestException("down")
        response = self.get(q="owned")
        self.assertTrue(response.context["web_error"])
        self.assertEqual(response.context["web_results"], [])
        self.assertContains(response, "Couldn't reach the web music database")
        self.assertEqual([s.title for s in response.context["songs"]], ["Owned Song"])


class MusicBrainzSearchSongsTests(TestCase):
    def setUp(self):
        get_patcher = patch("crate.musicbrainz.requests.get")
        self.mock_get = get_patcher.start()
        self.addCleanup(get_patcher.stop)
        parse_patcher = patch("crate.musicbrainz._parse", return_value=["parsed"])
        parse_patcher.start()
        self.addCleanup(parse_patcher.stop)
        self.mock_get.return_value.json.return_value = {"count": 42, "recordings": []}

    def test_returns_results_and_total_and_sends_offset(self):
        results, total = musicbrainz.search_songs("beatles", limit=10, offset=40)
        self.assertEqual((results, total), (["parsed"], 42))
        params = self.mock_get.call_args.kwargs["params"]
        self.assertEqual((params["limit"], params["offset"]), (10, 40))

    def test_missing_count_defaults_to_zero(self):
        self.mock_get.return_value.json.return_value = {"recordings": []}
        self.assertEqual(musicbrainz.search_songs("beatles")[1], 0)