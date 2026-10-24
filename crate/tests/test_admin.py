from django.contrib.auth import get_user_model
from django.test import override_settings, TestCase
from django.urls import reverse
 
from crate.models import Playlist, Song
from .helpers import STRONG_PASSWORD
 
User = get_user_model()

# ============ ADMIN ==============

PLAIN_STATIC_STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


@override_settings(STORAGES=PLAIN_STATIC_STORAGES)
class AdminOwnershipTests(TestCase):
    def setUp(self):
        self.boss = User.objects.create_superuser("boss", password=STRONG_PASSWORD)
        self.client.force_login(self.boss)
        self.alice = User.objects.create_user("alice", password=STRONG_PASSWORD)

    def test_admin_can_assign_an_owner_to_an_existing_song(self):
        song = Song.objects.create(title="Legacy", artist="L", audio_file="audio/l.mp3")
        response = self.client.get(reverse("admin:crate_song_change", args=[song.pk]))
        self.assertContains(response, 'name="user"')

    def test_admin_lists_the_owner_column(self):
        Song.objects.create(title="Owned", artist="L", audio_file="audio/l.mp3", user=self.alice)
        response = self.client.get(reverse("admin:crate_song_changelist"))
        self.assertContains(response, "alice")

    def test_playlist_admin_shows_owner(self):
        Playlist.objects.create(name="PL", user=self.alice)
        response = self.client.get(reverse("admin:crate_playlist_changelist"))
        self.assertContains(response, "alice")