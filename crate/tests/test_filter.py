from django.contrib.auth import get_user_model 
from django.test import TestCase 
from django.urls import reverse 

from crate.models import Song 
from .helpers import STRONG_PASSWORD

User = get_user_model()

class SongFilterTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("alice", password=STRONG_PASSWORD)
        self.client.force_login(self.user)
        # (title, genre, minutes, seconds)
        for t, g, m, s in [
            ("So What", "Jazz", 9, 22),
            ("Blue in Green", "Jazz", 5, 37),
            ("Africa", "Rock", 4, 55),
            ("Short Jam", "Rock", 1, 30),
        ]:
            Song.objects.create(title=t, artist="A", genre=g, minutes=m, seconds=s, user=self.user)

    def shown(self, response):
        """Titles of the songs the page actually displays"""
        return sorted(s.title for s in response.context["songs"])

    def test_no_filter_shows_all_songs(self):
        r = self.client.get(reverse("song_list"))
        self.assertEqual(len(self.shown(r)), 4)
        self.assertContains(r, "fa-filter")      # filter icon prsent

    def test_name_filter_is_case_insensitive_substring(self):
        self.assertEqual(self.shown(self.client.get(reverse("song_list"), {"name": "afr"})), ["Africa"])

    def test_genre_filter(self):
        self.assertEqual(self.shown(self.client.get(reverse("song_list"), {"genre": "Jazz"})),
                         ["Blue in Green", "So What"])

    def test_length_short_is_under_3_minutes(self):
        self.assertEqual(self.shown(self.client.get(reverse("song_list"), {"length": "short"})), ["Short Jam"])

    def test_length_medium_is_3_to_5_minutes(self):
        self.assertEqual(self.shown(self.client.get(reverse("song_list"), {"length": "medium"})), ["Africa"])

    def test_length_long_is_over_5_minutes(self):
        self.assertEqual(self.shown(self.client.get(reverse("song_list"), {"length": "long"})),
                         ["Blue in Green", "So What"])

    def test_two_filters_combine_with_and(self):
        self.assertEqual(self.shown(self.client.get(reverse("song_list"), {"genre": "Jazz", "length": "long"})),
                         ["Blue in Green", "So What"])

    def test_all_three_filters_combine(self):
        self.assertEqual(self.shown(self.client.get(reverse("song_list"), {"name": "so", "genre": "Jazz", "length": "long"})),
                         ["So What"])

    def test_genre_dropdown_lists_users_distinct_genres(self):
        r = self.client.get(reverse("song_list"))
        self.assertEqual(sorted(r.context["genre_options"]), ["Jazz", "Rock"])

    def test_no_match_shows_filter_aware_message(self):
        r = self.client.get(reverse("song_list"), {"name": "zzz-no-match"})
        self.assertEqual(self.shown(r), [])
        self.assertContains(r, "No songs match your filters")

    def test_filters_only_apply_to_the_logged_in_user(self):
        bob = User.objects.create_user("bob", password=STRONG_PASSWORD)
        Song.objects.create(title="Bob Jazz", artist="B", genre="Jazz", minutes=6, seconds=0, user=bob)
        r = self.client.get(reverse("song_list"), {"genre": "Jazz"})
        self.assertNotIn("Bob Jazz", self.shown(r))