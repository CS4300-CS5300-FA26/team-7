from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse 

from .helpers import STRONG_PASSWORD

User = get_user_model()

MANY = [
    {"title": f"Song {i}", "artist": f"Artist {i}", "album": "Al",
     "length": "3:00", "artwork": f"https://img/{i}.jpg", "itunes_url": "u"}
    for i in range(25)
]

class PaginationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("alice", password=STRONG_PASSWORD)
        self.client.force_login(self.user)
        self.url = reverse("search")

    @patch("crate.views.itunes.search_songs", return_value=MANY)
    def test_first_page_has_10_and_three_pages_total(self, _m):
        r = self.client.get(self.url, {"q": "song"})
        page = r.context["web_page"]
        self.assertEqual(len(page.object_list), 10)
        self.assertEqual(page.paginator.num_pages, 3)
        self.assertEqual(page.number, 1)

    @patch("crate.views.itunes.search_songs", return_value=MANY)
    def test_second_page_shows_next_items(self, _m):
        r = self.client.get(self.url, {"q": "song", "page": "2"})
        titles = [x["title"] for x in r.context["web_page"]]
        self.assertEqual(titles[0], "Song 10")
        self.assertEqual(len(titles), 10)

    @patch("crate.views.itunes.search_songs", return_value=MANY)
    def test_album_art_renders(self, _m):
        r = self.client.get(self.url, {"q": "song"})
        self.assertContains(r, 'src="https://img/0.jpg"')

    @patch("crate.views.itunes.search_songs", return_value=MANY)
    def test_pagination_controls_render(self, _m):
        r = self.client.get(self.url, {"q": "song"})
        self.assertContains(r, "pagination")
        self.assertContains(r, "page=2")

    @patch("crate.views.itunes.search_songs", return_value=MANY)
    def test_bad_page_falls_back_gracefully(self, _m):
        r = self.client.get(self.url, {"q": "song", "page": "999"})
        self.assertEqual(r.context["web_page"].number, 3)