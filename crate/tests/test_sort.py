from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from crate.models import Song
from .helpers import STRONG_PASSWORD

User = get_user_model()

class SearchViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("alice", password=STRONG_PASSWORD)
        self.other = User.objects.create_user("bob", password=STRONG_PASSWORD)
        self.url = reverse("search")
        rows = [
            ("Zebra", "Beta", "Jazz", 3, 30),
            ("apple", "alpha", "rock", 1, 5),
            ("Mango", "Gamma", "", 10, 0),
            ("Kiwi", "Delta", "Blues", None, None),
        ]
        for title, artist, genre, minutes, seconds in rows:
            Song.objects.create(
                title=title, artist=artist, genre=genre,
                minutes=minutes, seconds=seconds, user=self.user,
            )
        self.client.force_login(self.user)

    def titles(self, **params):
        response = self.client.get(self.url, params)
        self.assertEqual(response.status_code, 200)
        return [song.title for song in response.context["songs"]]

    # ---- access ----

    def test_anonymous_user_redirected_to_login(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertRedirects(response, f"{reverse('login')}?next={self.url}")

    def test_logged_in_user_sees_page(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "crate/search.html")

    def test_lists_all_own_songs_when_not_searching(self):
        self.assertEqual(len(self.titles()), 4)

    def test_never_shows_another_users_songs(self):
        Song.objects.create(title="Aaa Bobs Song", artist="Bob", user=self.other)
        self.assertNotIn("Aaa Bobs Song", self.titles())
        self.assertNotIn("Aaa Bobs Song", self.titles(q="Bobs"))

    # ---- searching ----

    def test_search_matches_title_case_insensitively(self):
        self.assertEqual(self.titles(q="ZEB"), ["Zebra"])

    def test_search_matches_artist(self):
        self.assertEqual(self.titles(q="gamma"), ["Mango"])

    def test_search_matches_genre(self):
        self.assertEqual(self.titles(q="blues"), ["Kiwi"])

    def test_blank_search_returns_everything(self):
        self.assertEqual(len(self.titles(q="   ")), 4)

    def test_no_match_message(self):
        response = self.client.get(self.url, {"q": "nothing like this"})
        self.assertContains(response, "No songs match your search.")

    def test_empty_library_message(self):
        User.objects.create_user("carol", password=STRONG_PASSWORD)
        self.client.force_login(User.objects.get(username="carol"))
        response = self.client.get(self.url)
        self.assertContains(response, "No songs are currently available.")

    # ---- sorting ----

    def test_sort_menu_is_shown_with_all_four_criteria(self):
        response = self.client.get(self.url)
        for label in ("Title", "Artist", "Genre", "Length"):
            self.assertContains(response, f">{label}</option>")

    def test_sort_by_genre_puts_blank_genres_last(self):
        self.assertEqual(self.titles(sort="genre"), ["Kiwi", "Zebra", "apple", "Mango"])

    def test_sort_by_length_puts_unknown_length_last(self):
        self.assertEqual(self.titles(sort="length"), ["apple", "Zebra", "Mango", "Kiwi"])

    def test_descending_reverses_order(self):
        self.assertEqual(self.titles(sort="title", dir="desc"), ["Zebra", "Mango", "Kiwi", "apple"])
        self.assertEqual(self.titles(sort="length", dir="desc"), ["Mango", "Zebra", "apple", "Kiwi"])

    def test_descending_still_puts_blank_genre_last(self):
        self.assertEqual(self.titles(sort="genre", dir="desc"), ["apple", "Zebra", "Kiwi", "Mango"])

    def test_invalid_sort_is_ignored(self):
        response = self.client.get(self.url, {"sort": "password; DROP TABLE"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["songs"]), 4)
        self.assertEqual(response.context["current_sort"], "")

    def test_equal_values_are_ordered_by_title(self):
        Song.objects.create(title="Banana", artist="Beta", genre="Jazz", user=self.user)
        self.assertEqual(self.titles(sort="artist")[1:3], ["Banana", "Zebra"])

    def test_selected_options_are_remembered_in_the_form(self):
        response = self.client.get(self.url, {"sort": "length", "dir": "desc"})
        self.assertContains(response, '<option value="length" selected>')
        self.assertContains(response, '<option value="desc" selected>')

    # ---- searching and sorting together ----

    def test_sorting_applies_to_search_results_only(self):
        # "r" matches Zebra (Zebra) and apple (rock) only
        self.assertEqual(self.titles(q="r"), ["Zebra", "apple"])
        self.assertEqual(self.titles(q="r", sort="title"), ["apple", "Zebra"])
        self.assertEqual(self.titles(q="r", sort="length", dir="desc"), ["Zebra", "apple"])