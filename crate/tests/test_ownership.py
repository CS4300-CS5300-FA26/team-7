"""Tests that every user only ever sees and changes their own songs and playlists."""
 
import shutil
import tempfile
from unittest.mock import patch
 
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings, TestCase
from django.urls import reverse
 
from crate.models import Playlist, Song
from .helpers import make_wav, STRONG_PASSWORD
 
User = get_user_model()
class TwoUsersTestCase(TestCase):
    """Alice and Bob each own a song and a playlist; the client starts logged in as Alice."""

    def setUp(self):
        self.alice = User.objects.create_user("alice", password=STRONG_PASSWORD)
        self.bob = User.objects.create_user("bob", password=STRONG_PASSWORD)
        # a stored file name is enough to render a song; the file itself isn't read
        self.alice_song = Song.objects.create(
            title="Alice Anthem", artist="A", audio_file="audio/a.mp3", user=self.alice)
        self.bob_song = Song.objects.create(
            title="Bob Ballad", artist="B", audio_file="audio/b.mp3", user=self.bob)
        self.alice_playlist = Playlist.objects.create(name="Alice Mix", user=self.alice)
        self.bob_playlist = Playlist.objects.create(name="Bob Mix", user=self.bob)
        self.alice_playlist.songs.add(self.alice_song)
        self.bob_playlist.songs.add(self.bob_song)
        self.client.force_login(self.alice)


# ============ SONG LIST ==============

class SongListOwnershipTests(TwoUsersTestCase):
    def test_user_sees_only_their_own_songs(self):
        response = self.client.get(reverse("song_list"))
        self.assertContains(response, "Alice Anthem")
        self.assertNotContains(response, "Bob Ballad")
        self.assertEqual(list(response.context["songs"]), [self.alice_song])

    def test_other_user_sees_only_theirs(self):
        self.client.force_login(self.bob)
        response = self.client.get(reverse("song_list"))
        self.assertContains(response, "Bob Ballad")
        self.assertNotContains(response, "Alice Anthem")

    def test_songs_with_no_owner_are_visible_to_nobody(self):
        Song.objects.create(title="Orphan Tune", artist="?", audio_file="audio/o.mp3")
        for user in (self.alice, self.bob):
            self.client.force_login(user)
            self.assertNotContains(self.client.get(reverse("song_list")), "Orphan Tune")

    def test_add_to_playlist_menu_only_offers_own_playlists(self):
        # the menu hides playlists a song is already in, so add one it isn't in
        chill = Playlist.objects.create(name="Alice Chill", user=self.alice)
        response = self.client.get(reverse("song_list"))
        self.assertContains(response, "Alice Chill")
        self.assertNotContains(response, "Bob Mix")
        self.assertCountEqual(response.context["playlists"], [self.alice_playlist, chill])

    def test_own_song_without_audio_is_listed_so_it_can_be_deleted(self):
        ghost = Song.objects.create(title="No Audio Song", artist="A", user=self.alice)
        response = self.client.get(reverse("song_list"))
        self.assertContains(response, "No Audio Song")
        self.assertContains(response, "No audio file")
        self.assertContains(response, reverse("song_delete", args=[ghost.id]))


# ============ PLAYLISTS PAGE ==============

class PlaylistsPageOwnershipTests(TwoUsersTestCase):
    def test_only_own_playlists_are_listed(self):
        response = self.client.get(reverse("playlists"))
        self.assertContains(response, "Alice Mix")
        self.assertNotContains(response, "Bob Mix")
        self.assertEqual(list(response.context["playlists"]), [self.alice_playlist])

    def test_other_users_song_titles_never_appear(self):
        response = self.client.get(reverse("playlists"))
        self.assertNotContains(response, "Bob Ballad")

    def test_create_playlist_picker_only_offers_own_songs(self):
        response = self.client.get(reverse("playlists"))
        self.assertEqual(list(response.context["songs"]), [self.alice_song])
        self.assertContains(response, "Alice Anthem")

    def test_ownerless_playlists_are_visible_to_nobody(self):
        Playlist.objects.create(name="Legacy Mix")
        self.assertNotContains(self.client.get(reverse("playlists")), "Legacy Mix")


# ============ CREATE PLAYLIST ==============

class CreatePlaylistOwnershipTests(TwoUsersTestCase):
    url = "/playlists/create/"

    def test_new_playlist_belongs_to_the_creator(self):
        self.client.post(self.url, {"name": "Fresh", "songs": [self.alice_song.id]})
        playlist = Playlist.objects.get(name="Fresh")
        self.assertEqual(playlist.user, self.alice)
        self.assertEqual(list(playlist.songs.all()), [self.alice_song])

    def test_other_users_songs_cannot_be_attached_even_if_ids_are_forged(self):
        self.client.post(self.url, {"name": "Sneaky", "songs": [self.alice_song.id, self.bob_song.id]})
        playlist = Playlist.objects.get(name="Sneaky")
        self.assertEqual(list(playlist.songs.all()), [self.alice_song])

    def test_junk_song_ids_are_ignored_not_a_server_error(self):
        response = self.client.post(self.url, {"name": "Junk", "songs": ["abc", "", str(self.alice_song.id)]})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(list(Playlist.objects.get(name="Junk").songs.all()), [self.alice_song])

    def test_blank_name_creates_nothing(self):
        before = Playlist.objects.count()
        self.client.post(self.url, {"name": "   ", "songs": [self.alice_song.id]})
        self.assertEqual(Playlist.objects.count(), before)


# ============ PLAYLIST DETAIL ==============

class PlaylistDetailOwnershipTests(TwoUsersTestCase):
    def test_owner_can_view_their_playlist(self):
        response = self.client.get(reverse("playlist_detail", args=[self.alice_playlist.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Alice Anthem")

    def test_other_users_playlist_is_a_404(self):
        response = self.client.get(reverse("playlist_detail", args=[self.bob_playlist.id]))
        self.assertEqual(response.status_code, 404)

    def test_ownerless_playlist_is_a_404(self):
        legacy = Playlist.objects.create(name="Legacy Mix")
        self.assertEqual(self.client.get(reverse("playlist_detail", args=[legacy.id])).status_code, 404)

    def test_available_songs_are_only_the_users_own(self):
        extra = Song.objects.create(title="Alice Extra", artist="A", audio_file="audio/x.mp3", user=self.alice)
        response = self.client.get(reverse("playlist_detail", args=[self.alice_playlist.id]))
        self.assertEqual(list(response.context["available_songs"]), [extra])
        self.assertNotContains(response, "Bob Ballad")

    def test_a_stray_foreign_song_inside_a_playlist_is_not_shown(self):
        # e.g. left over from before songs had owners, or added through the admin
        self.alice_playlist.songs.add(self.bob_song)
        response = self.client.get(reverse("playlist_detail", args=[self.alice_playlist.id]))
        self.assertNotContains(response, "Bob Ballad")
        self.assertEqual(list(response.context["songs"]), [self.alice_song])


# ============ ADD / REMOVE / DELETE ==============

class ChangingThingsOwnershipTests(TwoUsersTestCase):
    def add(self, song, playlist):
        return self.client.post(
            reverse("add_song_to_playlist", args=[song.id]), {"playlist_id": playlist.id})

    def test_can_add_own_song_to_own_playlist(self):
        extra = Song.objects.create(title="Extra", artist="A", audio_file="audio/x.mp3", user=self.alice)
        self.assertEqual(self.add(extra, self.alice_playlist).status_code, 302)
        self.assertTrue(self.alice_playlist.songs.filter(pk=extra.pk).exists())

    def test_cannot_add_someone_elses_song_to_your_playlist(self):
        self.assertEqual(self.add(self.bob_song, self.alice_playlist).status_code, 404)
        self.assertFalse(self.alice_playlist.songs.filter(pk=self.bob_song.pk).exists())

    def test_cannot_add_your_song_to_someone_elses_playlist(self):
        self.assertEqual(self.add(self.alice_song, self.bob_playlist).status_code, 404)
        self.assertFalse(self.bob_playlist.songs.filter(pk=self.alice_song.pk).exists())

    def test_cannot_remove_songs_from_someone_elses_playlist(self):
        url = reverse("remove_song_from_playlist", args=[self.bob_playlist.id, self.bob_song.id])
        self.assertEqual(self.client.post(url).status_code, 404)
        self.assertTrue(self.bob_playlist.songs.filter(pk=self.bob_song.pk).exists())

    def test_cannot_delete_someone_elses_song(self):
        response = self.client.post(reverse("song_delete", args=[self.bob_song.id]))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Song.objects.filter(pk=self.bob_song.pk).exists())

    def test_can_delete_own_song(self):
        response = self.client.post(reverse("song_delete", args=[self.alice_song.id]))
        self.assertRedirects(response, reverse("song_list"))
        self.assertFalse(Song.objects.filter(pk=self.alice_song.pk).exists())

    def test_all_of_these_still_require_login(self):
        self.client.logout()
        urls = [
            ("get", reverse("song_list")),
            ("get", reverse("playlists")),
            ("get", reverse("playlist_detail", args=[self.alice_playlist.id])),
            ("post", reverse("create_playlist")),
            ("post", reverse("add_song_to_playlist", args=[self.alice_song.id])),
            ("post", reverse("remove_song_from_playlist", args=[self.alice_playlist.id, self.alice_song.id])),
            ("post", reverse("song_delete", args=[self.alice_song.id])),
        ]
        for method, url in urls:
            with self.subTest(url=url):
                response = getattr(self.client, method)(url)
                self.assertEqual(response.status_code, 302)
                self.assertIn(reverse("login"), response.url)


# ============ DELETED SONGS AND PLAYLISTS ==============

class DeletedSongsLeavePlaylistsTests(TwoUsersTestCase):
    def test_deleting_a_song_removes_it_from_every_playlist_page(self):
        second = Playlist.objects.create(name="Second Mix", user=self.alice)
        second.songs.add(self.alice_song)

        self.client.post(reverse("song_delete", args=[self.alice_song.id]))

        self.assertEqual(Playlist.songs.through.objects.filter(song_id=self.alice_song.id).count(), 0)
        self.assertNotContains(self.client.get(reverse("playlists")), "Alice Anthem")
        for playlist in (self.alice_playlist, second):
            with self.subTest(playlist=playlist.name):
                page = self.client.get(reverse("playlist_detail", args=[playlist.id]))
                self.assertNotContains(page, "Alice Anthem")
                self.assertEqual(list(page.context["songs"]), [])

    def test_deleting_a_song_does_not_delete_the_playlist(self):
        self.client.post(reverse("song_delete", args=[self.alice_song.id]))
        self.assertTrue(Playlist.objects.filter(pk=self.alice_playlist.pk).exists())

    def test_deleting_a_user_removes_their_songs_and_playlists_only(self):
        self.bob.delete()
        self.assertFalse(Song.objects.filter(title="Bob Ballad").exists())
        self.assertFalse(Playlist.objects.filter(name="Bob Mix").exists())
        self.assertTrue(Song.objects.filter(title="Alice Anthem").exists())


# ============ UPLOAD ASSIGNS THE OWNER ==============

class UploadOwnershipTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        tmp = tempfile.mkdtemp()
        cls.addClassCleanup(shutil.rmtree, tmp, ignore_errors=True)
        cls.enterClassContext(override_settings(MEDIA_ROOT=tmp))

    @patch("cloudinary.uploader.upload", return_value={"public_id": "audio/test"})
    def test_uploaded_song_belongs_to_the_uploader(self, mock_upload):
        alice = User.objects.create_user("alice", password=STRONG_PASSWORD)
        self.client.force_login(alice)
        audio = SimpleUploadedFile("t.wav", make_wav(), content_type="audio/wav")
        response = self.client.post(reverse("upload_song"), {
            "title": "Mine", "artist": "Me", "genre": "", "album": "", "audio_file": audio})
        self.assertRedirects(response, reverse("song_list"))
        self.assertEqual(Song.objects.get(title="Mine").user, alice)

    @patch("cloudinary.uploader.upload", return_value={"public_id": "audio/test"})
    def test_the_uploader_sees_it_and_others_do_not(self, mock_upload):
        alice = User.objects.create_user("alice", password=STRONG_PASSWORD)
        bob = User.objects.create_user("bob", password=STRONG_PASSWORD)
        self.client.force_login(alice)
        audio = SimpleUploadedFile("t.wav", make_wav(), content_type="audio/wav")
        self.client.post(reverse("upload_song"), {
            "title": "Mine", "artist": "Me", "genre": "", "album": "", "audio_file": audio})
        self.assertContains(self.client.get(reverse("song_list")), "Mine")
        self.client.force_login(bob)
        self.assertNotContains(self.client.get(reverse("song_list")), "Mine")

    def test_upload_form_has_no_owner_field_to_tamper_with(self):
        alice = User.objects.create_user("alice", password=STRONG_PASSWORD)
        self.client.force_login(alice)
        response = self.client.get(reverse("upload_song"))
        self.assertNotIn("user", response.context["form"].fields)

