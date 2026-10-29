"""Tests for the song list page."""
import json 
from unittest.mock import patch
 
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
 
from crate.models import Song
from .helpers import *
 
User = get_user_model()
 


# ============ SONG LIST TESTS ==============
 
class SongListViewTests(TestCase):
    
    def setUp(self):
        self.user = User.objects.create_user("alice", password=STRONG_PASSWORD)
        self.url = reverse("song_list")
 
    def test_anonymous_user_redirected_to_login(self):
        response = self.client.get(self.url)
        self.assertRedirects(response, f"{reverse('login')}?next={self.url}")
 
    def test_anonymous_user_cannot_see_songs(self):
        Song.objects.create(title="Secret Song", artist="Hidden", user=self.user)
        response = self.client.get(self.url, follow=True)
        self.assertNotContains(response, "Secret Song")
 
    def test_authenticated_user_sees_page(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "crate/song_list.html")
 
    def test_empty_state_message(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertContains(response, "No songs are currently available.")
        self.assertEqual(len(response.context["songs"]), 0)

    @patch("cloudinary.uploader.upload", return_value={"public_id": "audio/test"})
    def test_lists_all_songs(self, mock_upload):
        audio = SimpleUploadedFile("test.mp3", b"fake audio bytes", content_type="audio/mpeg")
        Song.objects.create(
            title="So What", artist="Miles Davis", genre="Jazz", minutes=9, seconds=22, audio_file=audio,
            user=self.user,
        ) 
        Song.objects.create(title="Africa", artist="Toto", genre="Rock", audio_file=audio, user=self.user)
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(len(response.context["songs"]), 2)
        self.assertContains(response, "So What")
        self.assertContains(response, "Miles Davis")
        self.assertContains(response, "Jazz")
        self.assertContains(response, "9:22")
        self.assertContains(response, "Africa")
        self.assertNotContains(response, "No songs are currently available.")
        
    @patch("cloudinary.uploader.upload", return_value={"public_id": "audio/test"})
    def test_song_content_is_html_escaped(self, mock_upload):
        audio = SimpleUploadedFile("test.mp3", b"fake audio bytes", content_type="audio/mpeg")
        Song.objects.create(title="<script>alert(1)</script>", artist="X", audio_file=audio, user=self.user)
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertNotContains(response, "<script>alert(1)</script>")
        self.assertContains(response, "&lt;script&gt;")

