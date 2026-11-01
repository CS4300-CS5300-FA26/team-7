"""Tests for the pages that feed the site-wide player and queue: the bar in base.html and the
Play / Queue buttons on the song list and playlist pages. (The queue itself runs in the browser.)"""
import re

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils.html import escape

from crate.models import Playlist, Song
from crate.tests.helpers import STRONG_PASSWORD

User = get_user_model()

HOSTILE = 'He said "hi" <img src=x onerror=alert(1)>'


class PlayerBarTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user("alice", password=STRONG_PASSWORD)

    def test_logged_in_pages_have_the_player_bar(self):
        self.client.force_login(self.alice)
        for name in ("home", "song_list", "playlists", "my_account", "upload_song"):
            with self.subTest(page=name):
                html = self.client.get(reverse(name)).content.decode()
                self.assertEqual(html.count('id="player-bar"'), 1)
                self.assertEqual(html.count('<audio id="player"'), 1)

    def test_bar_is_tagged_with_the_users_id_so_queues_stay_separate(self):
        self.client.force_login(self.alice)
        html = self.client.get(reverse("song_list")).content.decode()
        self.assertIn(f'data-user-id="{self.alice.pk}"', html)

    def test_bar_starts_hidden(self):
        self.client.force_login(self.alice)
        html = self.client.get(reverse("song_list")).content.decode()
        self.assertRegex(html, r'<div id="player-bar"[^>]*\bhidden\b')

    def test_logged_out_pages_have_no_player(self):
        for name in ("home", "login", "signup"):
            with self.subTest(page=name):
                html = self.client.get(reverse(name)).content.decode()
                self.assertNotIn("player-bar", html)
                self.assertNotIn("<audio", html)

    def test_logout_form_is_marked_so_the_queue_can_be_cleared(self):
        self.client.force_login(self.alice)
        html = self.client.get(reverse("home")).content.decode()
        self.assertRegex(html, r'<form action="[^"]*logout/" method="post" data-logout>')

    def test_page_has_no_unrendered_template_tags(self):
        # the player script is inline in base.html; make sure Django didn't trip over it
        self.client.force_login(self.alice)
        html = self.client.get(reverse("song_list")).content.decode()
        self.assertNotIn("{%", html)
        self.assertNotIn("{{", html)

    def test_player_script_is_present_once(self):
        self.client.force_login(self.alice)
        html = self.client.get(reverse("song_list")).content.decode()
        self.assertEqual(html.count("crate-queue-"), 1)


class SongListPlayerButtonsTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user("alice", password=STRONG_PASSWORD)
        self.bob = User.objects.create_user("bob", password=STRONG_PASSWORD)
        self.client.force_login(self.alice)
        self.song = Song.objects.create(
            title="Alpha", artist="Ann", audio_file="audio/alpha.mp3", user=self.alice)

    def page(self):
        return self.client.get(reverse("song_list")).content.decode()

    def test_row_carries_everything_the_player_needs(self):
        html = self.page()
        self.assertIn(f'data-song data-song-id="{self.song.id}"', html)
        self.assertIn('data-title="Alpha"', html)
        self.assertIn('data-artist="Ann"', html)
        self.assertIn(f'data-url="{escape(self.song.audio_file.url)}"', html)

    def test_row_has_play_and_queue_buttons(self):
        html = self.page()
        self.assertIn('data-queue-action="play"', html)
        self.assertIn('data-queue-action="add"', html)
        self.assertEqual(html.count('type="button" class="btn btn-sm btn-primary" data-queue-action="play"'), 1)

    def test_rows_no_longer_have_their_own_audio_players(self):
        # one <audio> element for the whole site now, in the bar (comments mention the word, so count real tags)
        self.assertEqual(len(re.findall(r"<audio\s", self.page())), 1)

    def test_old_one_at_a_time_script_is_gone(self):
        self.assertNotIn("addEventListener('play'", self.page())

    def test_song_without_audio_gets_no_buttons(self):
        Song.objects.create(title="Silent Song", artist="Sam", user=self.alice)
        html = self.page()
        self.assertIn("Silent Song", html)
        self.assertIn("No audio file", html)
        self.assertEqual(html.count("data-song "), 1)   # only Alpha

    def test_titles_with_quotes_and_html_are_escaped_in_attributes(self):
        Song.objects.create(title=HOSTILE, artist="Xe", audio_file="audio/x.mp3", user=self.alice)
        html = self.page()
        self.assertIn(f'data-title="{escape(HOSTILE)}"', html)
        self.assertNotIn(HOSTILE, html)   # never written out raw
        self.assertIn("&quot;hi&quot;", html)

    def test_other_users_songs_never_get_buttons(self):
        Song.objects.create(title="Bob's Secret", artist="Bob", audio_file="audio/bob.mp3", user=self.bob)
        html = self.page()
        self.assertNotIn("Bob's Secret", html)
        self.assertNotIn("bob.mp3", html)
        self.assertEqual(html.count("data-song "), 1)

    def test_column_is_headed_play(self):
        self.assertIn("<th>Play</th>", self.page())


class PlaylistPlayerButtonsTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user("alice", password=STRONG_PASSWORD)
        self.bob = User.objects.create_user("bob", password=STRONG_PASSWORD)
        self.client.force_login(self.alice)
        self.a = Song.objects.create(title="Alpha", artist="Ann", audio_file="audio/a.mp3", user=self.alice)
        self.b = Song.objects.create(title="Bravo", artist="Bo", audio_file="audio/b.mp3", user=self.alice)
        self.silent = Song.objects.create(title="Silent", artist="Sam", user=self.alice)
        self.outside = Song.objects.create(title="Outside", artist="Oz", audio_file="audio/o.mp3", user=self.alice)
        self.playlist = Playlist.objects.create(name="Mix", user=self.alice)
        self.playlist.songs.set([self.a, self.b, self.silent])

    def page(self, playlist=None):
        playlist = playlist or self.playlist
        return self.client.get(reverse("playlist_detail", args=[playlist.id])).content.decode()

    def test_toolbar_has_play_shuffle_and_add_buttons(self):
        html = self.page()
        for action in ("play-all", "shuffle-all", "add-all"):
            with self.subTest(action=action):
                self.assertEqual(html.count(f'data-queue-action="{action}" data-queue-scope="#playlist-songs"'), 1)
        for label in ("Play playlist", "Shuffle", "Add to queue"):
            self.assertIn(label, html)

    def test_toolbar_scope_exists_and_contains_the_playlists_songs(self):
        html = self.page()
        self.assertEqual(html.count('id="playlist-songs"'), 1)
        inside = html[html.index('id="playlist-songs"'):]
        inside = inside[:inside.index("</table>")]
        self.assertIn('data-title="Alpha"', inside)
        self.assertIn('data-title="Bravo"', inside)

    def test_only_playable_songs_in_the_playlist_are_queueable(self):
        html = self.page()
        titles = re.findall(r'data-song data-song-id="\d+" data-title="([^"]*)"', html)
        self.assertEqual(titles, ["Alpha", "Bravo"])

    def test_songs_without_audio_are_marked(self):
        self.assertIn("No audio file", self.page())

    def test_songs_not_in_the_playlist_are_not_queued_by_play_playlist(self):
        html = self.page()
        self.assertIn("Outside", html)   # listed under "Add Songs"...
        self.assertNotIn('data-title="Outside"', html)   # ...but not part of what Play playlist collects

    def test_buttons_are_not_shown_for_an_empty_playlist(self):
        empty = Playlist.objects.create(name="Empty", user=self.alice)
        html = self.page(empty)
        self.assertNotIn("Play playlist", html)
        self.assertIn("This playlist is empty", html)

    def test_other_users_playlist_is_still_a_404(self):
        theirs = Playlist.objects.create(name="Theirs", user=self.bob)
        response = self.client.get(reverse("playlist_detail", args=[theirs.id]))
        self.assertEqual(response.status_code, 404)