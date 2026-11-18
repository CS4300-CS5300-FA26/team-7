"""Cover artwork appears throughout song and playlist listings."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from crate.models import Playlist, Song


class CoverDisplayTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="cover_user", password="pass12345")
        self.client.force_login(self.user)
        self.with_cover = Song.objects.create(title="With artwork", artist="Artist", user=self.user, cover="covers/sample.jpg")
        self.no_cover = Song.objects.create(title="Without artwork", artist="Artist", user=self.user)
        self.playlist = Playlist.objects.create(name="Favorites", user=self.user)
        self.playlist.songs.add(self.with_cover, self.no_cover)

    def test_song_list_shows_cover_and_placeholder(self):
        response = self.client.get(reverse("song_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "covers/sample.jpg")
        self.assertContains(response, "No cover art for Without artwork")

    def test_playlist_detail_shows_cover_and_placeholder(self):
        response = self.client.get(reverse("playlist_detail", args=[self.playlist.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "covers/sample.jpg")
        self.assertContains(response, "No cover art for Without artwork")

    def test_playlist_index_shows_cover_and_placeholder(self):
        response = self.client.get(reverse("playlists"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "covers/sample.jpg")
        self.assertContains(response, "No cover art for Without artwork")
