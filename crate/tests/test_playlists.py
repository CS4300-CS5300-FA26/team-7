"""Tests for creating playlists and adding and removing songs."""
 
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
 
from crate.models import Playlist, Song
 
User = get_user_model()
 

# ============ Playlist Tests ==============
class PlaylistFeatureTests(TestCase):
    def setUp(self):
        # Create a user and log in.
        self.user = User.objects.create_user(
            username="testuser",
            password="testpassword123",
        )
        self.client.login(
            username="testuser",
            password="testpassword123",
        )

        # Create two songs.
        self.song1 = Song.objects.create(
            title="Test Song One",
            artist="Test Artist",
            genre="Pop",
            album="Test Album",
            minutes=3,
            seconds=30,
            user=self.user,
        )

        self.song2 = Song.objects.create(
            title="Test Song Two",
            artist="Test Artist2",
            genre="Rock",
            album="Test Album2",
            minutes=4,
            seconds=15,
            user=self.user,
        )

        # Create two playlists.
        self.playlist1 = Playlist.objects.create(
            name="Test Playlist1", user=self.user
        )
        self.playlist2 = Playlist.objects.create(
            name="Test Playlist2", user=self.user
        )

    def test_add_song_to_playlist(self):
        response = self.client.post(
            reverse("add_song_to_playlist", args=[self.song1.id]),
            {
                "playlist_id": self.playlist1.id,
                "next": "song_list",
            },
        )

        self.assertRedirects(response, reverse("song_list"))
        self.assertTrue(
            self.playlist1.songs.filter(id=self.song1.id).exists()
        )

    def test_remove_song_from_playlist(self):
        self.playlist1.songs.add(self.song1, self.song2)

        response = self.client.post(
            reverse(
                "remove_song_from_playlist",
                args=[self.playlist1.id, self.song1.id],
            )
        )

        self.assertRedirects(
            response,
            reverse("playlist_detail", args=[self.playlist1.id]),
        )
        self.assertFalse(
            self.playlist1.songs.filter(id=self.song1.id).exists()
        )
        self.assertTrue(
            self.playlist1.songs.filter(id=self.song2.id).exists()
        )

        # Removing from a playlist should not delete the Song itself.
        self.assertTrue(Song.objects.filter(id=self.song1.id).exists())

    def test_playlist_detail_displays_songs(self):
        self.playlist1.songs.add(self.song1)

        response = self.client.get(
            reverse("playlist_detail", args=[self.playlist1.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Playlist1")
        self.assertContains(response, "Test Song One")

        # Songs not in the playlist should be offered in the Add Songs section.
        self.assertContains(response, "Test Song Two")

        self.assertQuerySetEqual(
            response.context["songs"],
            [self.song1],
        )
        self.assertQuerySetEqual(
            response.context["available_songs"],
            [self.song2],
        )

    def test_song_list_requires_login(self):
        """Logged-out users are redirected to login."""
        self.client.logout()

        response = self.client.get(reverse("song_list"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.url)