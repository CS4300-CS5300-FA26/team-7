"""Tests for reading title/artist/album/genre tags out of uploaded audio files,
and the upload page's autofill that uses them.
"""
 
import io
import json
 
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
 
from crate.models import read_audio_metadata
from .helpers import make_flac, make_mp3, STRONG_PASSWORD, upload
 
User = get_user_model()
 
 

# ============ THE TAG READER ==============
 
class ReadAudioMetadataTests(TestCase):
    def test_reads_all_four_tags(self):
        data = make_mp3(title="So What", artist="Miles Davis", album="Kind of Blue", genre="Jazz")
        self.assertEqual(
            read_audio_metadata(io.BytesIO(data)),
            {"title": "So What", "artist": "Miles Davis", "album": "Kind of Blue", "genre": "Jazz"},
        )
 
    def test_only_returns_the_tags_that_exist(self):
        data = make_mp3(title="Just A Title")
        self.assertEqual(read_audio_metadata(io.BytesIO(data)), {"title": "Just A Title"})
 
    def test_untagged_audio_gives_empty_dict(self):
        self.assertEqual(read_audio_metadata(io.BytesIO(make_mp3())), {})
 
    def test_non_audio_gives_empty_dict(self):
        self.assertEqual(read_audio_metadata(io.BytesIO(b"just some text")), {})
 
    def test_empty_file_gives_empty_dict(self):
        self.assertEqual(read_audio_metadata(io.BytesIO(b"")), {})
 
    def test_whitespace_only_tags_are_ignored(self):
        data = make_mp3(title="   ", artist="Someone")
        self.assertEqual(read_audio_metadata(io.BytesIO(data)), {"artist": "Someone"})
 
    def test_long_values_are_trimmed_to_model_limit(self):
        data = make_mp3(title="x" * 500)
        self.assertEqual(len(read_audio_metadata(io.BytesIO(data))["title"]), 200)
 
    def test_multiple_values_use_the_first(self):
        data = make_mp3(artist=["First Artist", "Second Artist"])
        self.assertEqual(read_audio_metadata(io.BytesIO(data))["artist"], "First Artist")
 
    def test_file_is_rewound_so_it_can_still_be_saved(self):
        fileobj = io.BytesIO(make_mp3(title="T"))
        read_audio_metadata(fileobj)
        self.assertEqual(fileobj.tell(), 0)
 
 
# ============ FLAC FILES ==============
 
class FlacMetadataTests(TestCase):
    def read(self, **kwargs):
        # Uploaded files always carry their filename, and mutagen uses the
        # extension to tell an ID3-prefixed FLAC apart from an MP3.
        fileobj = io.BytesIO(make_flac(**kwargs))
        fileobj.name = "track.flac"
        return read_audio_metadata(fileobj)
 
    def test_reads_flac_vorbis_comments(self):
        self.assertEqual(
            self.read(vorbis={"title": "So What", "artist": "Miles Davis",
                              "album": "Kind of Blue", "genre": "Jazz"}),
            {"title": "So What", "artist": "Miles Davis", "album": "Kind of Blue", "genre": "Jazz"},
        )
 
    def test_flac_tag_names_are_case_insensitive(self):
        self.assertEqual(
            self.read(vorbis={"TITLE": "Loud Tags", "ARTIST": "Shouty"}),
            {"title": "Loud Tags", "artist": "Shouty"},
        )
 
    def test_flac_with_only_an_id3_header_is_read(self):
        self.assertEqual(
            self.read(id3={"title": "ID3 Title", "artist": "ID3 Artist",
                           "album": "ID3 Album", "genre": "Rock"}),
            {"title": "ID3 Title", "artist": "ID3 Artist", "album": "ID3 Album", "genre": "Rock"},
        )
 
    def test_flac_own_tags_win_over_id3_header(self):
        result = self.read(vorbis={"title": "Vorbis Title"}, id3={"title": "ID3 Title", "artist": "ID3 Artist"})
        self.assertEqual(result["title"], "Vorbis Title")
        self.assertEqual(result["artist"], "ID3 Artist")  # missing natively, so ID3 fills the gap
 
    def test_untagged_flac_gives_empty_dict(self):
        self.assertEqual(self.read(), {})
 
    def test_album_artist_is_used_when_there_is_no_artist(self):
        self.assertEqual(
            self.read(vorbis={"title": "Track", "albumartist": "Various Artists"}),
            {"title": "Track", "artist": "Various Artists"},
        )
 
    def test_artist_is_preferred_over_album_artist(self):
        result = self.read(vorbis={"artist": "Real Artist", "albumartist": "Various Artists"})
        self.assertEqual(result["artist"], "Real Artist")
 
    def test_flac_upload_through_the_endpoint(self):
        user = User.objects.create_user("flacfan", password=STRONG_PASSWORD)
        self.client.force_login(user)
        data = make_flac(vorbis={"title": "So What", "artist": "Miles Davis"})
        response = self.client.post(
            reverse("song_metadata"),
            {"audio_file": upload(data, "so_what.flac", "audio/flac")},
        )
        self.assertEqual(response.json(), {"title": "So What", "artist": "Miles Davis"})
 
 
# ============ THE ENDPOINT ==============
 
 
# ============ THE UPLOAD PAGE ==============
 
class UploadPageAutofillWiringTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("alice", password=STRONG_PASSWORD)
        self.client.force_login(self.user)
 
    def test_page_points_its_script_at_the_metadata_endpoint(self):
        response = self.client.get(reverse("upload_song"))
        self.assertContains(response, reverse("song_metadata"))
        self.assertContains(response, 'id="id_audio_file"')
        self.assertContains(response, 'id="metadata-status"')
 
    def test_every_autofilled_field_exists_on_the_form(self):
        response = self.client.get(reverse("upload_song"))
        for name in ("title", "artist", "album", "genre"):
            with self.subTest(field=name):
                self.assertContains(response, f'id="id_{name}"')
 
    def test_page_includes_csrf_token_for_the_script_to_send(self):
        response = self.client.get(reverse("upload_song"))
        self.assertContains(response, "csrfmiddlewaretoken")


class SongMetadataViewTests(TestCase):
    def setUp(self):
        self.url = reverse("song_metadata")
        self.user = User.objects.create_user("alice", password=STRONG_PASSWORD)
 
    def test_url_shape(self):
        self.assertEqual(self.url, "/upload_song/metadata/")
 
    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.post(self.url, {"audio_file": upload(make_mp3(title="T"))})
        self.assertRedirects(response, f"{reverse('login')}?next={self.url}")
 
    def test_get_is_not_allowed(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(self.url).status_code, 405)
 
    def test_post_without_a_file_is_a_400(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())
 
    def test_returns_tags_as_json(self):
        self.client.force_login(self.user)
        data = make_mp3(title="So What", artist="Miles Davis", album="Kind of Blue", genre="Jazz")
        response = self.client.post(self.url, {"audio_file": upload(data)})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertEqual(
            response.json(),
            {"title": "So What", "artist": "Miles Davis", "album": "Kind of Blue", "genre": "Jazz"},
        )
 
    def test_untagged_file_returns_empty_object(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, {"audio_file": upload(make_mp3())})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {})
 
    def test_non_audio_file_returns_empty_object(self):
        self.client.force_login(self.user)
        junk = upload(b"not audio", "notes.txt", "text/plain")
        response = self.client.post(self.url, {"audio_file": junk})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {})
 
    def test_reading_tags_does_not_save_anything(self):
        from crate.models import Song
        self.client.force_login(self.user)
        self.client.post(self.url, {"audio_file": upload(make_mp3(title="T", artist="A"))})
        self.assertEqual(Song.objects.count(), 0)
 
    def test_tag_text_is_returned_as_data_not_markup(self):
        self.client.force_login(self.user)
        data = make_mp3(title="<script>alert(1)</script>")
        response = self.client.post(self.url, {"audio_file": upload(data)})
        # JSON-encoded, so the browser sets it via input.value (never as HTML)
        self.assertEqual(json.loads(response.content)["title"], "<script>alert(1)</script>")
 
