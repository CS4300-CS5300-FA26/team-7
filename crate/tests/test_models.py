from django.test import TestCase
from django.contrib.auth import get_user_model
from .helpers import *

from crate.models import Song
 
User = get_user_model()
 
STRONG_PASSWORD = "Sup3r-Secret-Pass!"
 
 
# ============ MODEL TESTS ==============
 
class SongModelTests(TestCase):
    def test_str_includes_title_and_artist(self):
        song = Song.objects.create(title="Blue in Green", artist="Miles Davis")
        self.assertEqual(str(song), "Blue in Green — Miles Davis")
 
    def test_optional_fields_default_to_blank_or_null(self):
        song = Song.objects.create(title="Song", artist="Artist")
        self.assertEqual(song.genre, "")
        self.assertEqual(song.album, "")
        self.assertEqual(song.audio_file, "")
        self.assertIsNone(song.minutes)
        self.assertIsNone(song.seconds)
 
    def test_all_fields_are_saved(self):
        song = Song.objects.create(
            title="So What",
            artist="Miles Davis",
            genre="Jazz",
            album="Kind of Blue",
            audio_file="media/kindofblue.mp3",
            minutes=9,
            seconds=22,
        )
        song.refresh_from_db()
        self.assertEqual(song.genre, "Jazz")
        self.assertEqual(song.album, "Kind of Blue")
        self.assertEqual(song.audio_file, "media/kindofblue.mp3")
        self.assertEqual(song.minutes, 9)
        self.assertEqual(song.seconds, 22)
 
    def test_duration_must_be_non_negative(self):
        song = Song(title="Bad", artist="Artist", minutes=-5, seconds=-5)
        with self.assertRaises(Exception):
            song.full_clean()