import io, json, os, tempfile, struct
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model, SESSION_KEY
from django.contrib.auth.forms import UserCreationForm
from django.urls import reverse
from mutagen.easyid3 import EasyID3
from mutagen.flac import FLAC
from mutagen.id3 import ID3, TALB, TCON, TIT2, TPE1

from crate.models import Song, read_audio_metadata
 
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
 
 
# ============ HOME VIEW TESTS ==============
 
class HomeViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("alice", password=STRONG_PASSWORD)
 
    def test_home_resolves_at_root(self):
        self.assertEqual(reverse("home"), "/")
 
    def test_home_anonymous_shows_login_and_signup_links(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "home.html")
        self.assertContains(response, "You are not logged in.")
        self.assertContains(response, reverse("login"))
        self.assertContains(response, reverse("signup"))
        self.assertNotContains(response, "Log Out")
 
    def test_home_authenticated_shows_username_and_logout(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "alice")
        self.assertContains(response, "Log Out")
        self.assertContains(response, reverse("song_list"))
        self.assertNotContains(response, "You are not logged in.")
 
 
# ============ SIGNUP TESTS ==============
 
class SignupViewTests(TestCase):
    url = "/accounts/signup/"
 
    def valid_data(self, **overrides):
        data = {
            "username": "newuser",
            "password1": STRONG_PASSWORD,
            "password2": STRONG_PASSWORD,
        }
        data.update(overrides)
        return data
 
    def test_signup_url_name_resolves(self):
        self.assertEqual(reverse("signup"), self.url)
 
    def test_get_renders_form(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "registration/signup.html")
        self.assertIsInstance(response.context["form"], UserCreationForm)
 
    def test_valid_signup_creates_user(self):
        self.client.post(self.url, self.valid_data())
        self.assertTrue(User.objects.filter(username="newuser").exists())
 
    def test_valid_signup_hashes_password(self):
        self.client.post(self.url, self.valid_data())
        user = User.objects.get(username="newuser")
        self.assertNotEqual(user.password, STRONG_PASSWORD)
        self.assertTrue(user.check_password(STRONG_PASSWORD))
 
    def test_valid_signup_logs_user_in_and_redirects_home(self):
        response = self.client.post(self.url, self.valid_data())
        self.assertRedirects(response, reverse("home"))
        user = User.objects.get(username="newuser")
        self.assertEqual(int(self.client.session[SESSION_KEY]), user.pk)
 
    def test_mismatched_passwords_rejected(self):
        response = self.client.post(
            self.url, self.valid_data(password2="Different-Pass-123!")
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="newuser").exists())
        self.assertIn("password2", response.context["form"].errors)
        self.assertNotIn(SESSION_KEY, self.client.session)
 
    def test_duplicate_username_rejected(self):
        User.objects.create_user("newuser", password=STRONG_PASSWORD)
        response = self.client.post(self.url, self.valid_data())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.filter(username="newuser").count(), 1)
        self.assertIn("username", response.context["form"].errors)
 
    def test_duplicate_username_is_case_insensitive(self):
        User.objects.create_user("NewUser", password=STRONG_PASSWORD)
        response = self.client.post(self.url, self.valid_data(username="newuser"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.count(), 1)
 
    def test_common_password_rejected(self):
        response = self.client.post(
            self.url, self.valid_data(password1="password", password2="password")
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="newuser").exists())
 
    def test_short_password_rejected(self):
        response = self.client.post(
            self.url, self.valid_data(password1="Ab1!x", password2="Ab1!x")
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="newuser").exists())
 
    def test_password_similar_to_username_rejected(self):
        response = self.client.post(
            self.url,
            self.valid_data(username="johnsmith1", password1="johnsmith1", password2="johnsmith1"),
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="johnsmith1").exists())
 
    def test_missing_fields_rejected(self):
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.count(), 0)
        errors = response.context["form"].errors
        self.assertIn("username", errors)
        self.assertIn("password1", errors)
 
    def test_signup_page_links_to_login(self):
        response = self.client.get(self.url)
        self.assertContains(response, reverse("login"))
 
 
# ============ LOGIN TESTS ==============
 
class LoginTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("alice", password=STRONG_PASSWORD)
        self.url = reverse("login")
 
    def test_get_renders_login_template(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "registration/login.html")
 
    def test_login_page_links_to_signup(self):
        response = self.client.get(self.url)
        self.assertContains(response, reverse("signup"))
 
    def test_valid_login_redirects_home_and_sets_session(self):
        response = self.client.post(
            self.url, {"username": "alice", "password": STRONG_PASSWORD}
        )
        self.assertRedirects(response, reverse("home"))
        self.assertEqual(int(self.client.session[SESSION_KEY]), self.user.pk)
 
    def test_wrong_password_rejected(self):
        response = self.client.post(
            self.url, {"username": "alice", "password": "wrong-password"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(SESSION_KEY, self.client.session)
        self.assertTrue(response.context["form"].errors)
 
    def test_unknown_user_rejected(self):
        response = self.client.post(
            self.url, {"username": "nobody", "password": STRONG_PASSWORD}
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(SESSION_KEY, self.client.session)
 
    def test_inactive_user_cannot_log_in(self):
        self.user.is_active = False
        self.user.save()
        response = self.client.post(
            self.url, {"username": "alice", "password": STRONG_PASSWORD}
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(SESSION_KEY, self.client.session)
 
    def test_login_honors_next_parameter(self):
        response = self.client.post(
            f"{self.url}?next={reverse('song_list')}",
            {"username": "alice", "password": STRONG_PASSWORD},
        )
        self.assertRedirects(response, reverse("song_list"))
 
    def test_login_rejects_external_next_redirect(self):
        response = self.client.post(
            f"{self.url}?next=https://evil.example.com/",
            {"username": "alice", "password": STRONG_PASSWORD},
        )
        self.assertRedirects(response, reverse("home"))
 
 
# ============ LOGOUT TESTS ==============
 
class LogoutTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("alice", password=STRONG_PASSWORD)
        self.client.force_login(self.user)
 
    def test_post_logout_clears_session_and_redirects_home(self):
        response = self.client.post(reverse("logout"))
        self.assertRedirects(response, reverse("home"))
        self.assertNotIn(SESSION_KEY, self.client.session)
 
    def test_get_logout_is_not_allowed(self):
        # Django 5+ requires POST for logout
        response = self.client.get(reverse("logout"))
        self.assertEqual(response.status_code, 405)
        self.assertIn(SESSION_KEY, self.client.session)
 
    def test_logged_out_user_sees_anonymous_home(self):
        self.client.post(reverse("logout"))
        response = self.client.get(reverse("home"))
        self.assertContains(response, "You are not logged in.")
 
 
# ============ SONG LIST TESTS ==============
 
class SongListViewTests(TestCase):
    
    def setUp(self):
        self.user = User.objects.create_user("alice", password=STRONG_PASSWORD)
        self.url = reverse("song_list")
 
    def test_anonymous_user_redirected_to_login(self):
        response = self.client.get(self.url)
        self.assertRedirects(response, f"{reverse('login')}?next={self.url}")
 
    def test_anonymous_user_cannot_see_songs(self):
        Song.objects.create(title="Secret Song", artist="Hidden")
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
 
    def test_lists_all_songs(self):
        audio = SimpleUploadedFile("test.mp3", b"fake audio bytes", content_type="audio/mpeg")
        Song.objects.create(
            title="So What", artist="Miles Davis", genre="Jazz", minutes=9, seconds=22, audio_file=audio
        ) 
        Song.objects.create(title="Africa", artist="Toto", genre="Rock", audio_file=audio)
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(len(response.context["songs"]), 2)
        self.assertContains(response, "So What")
        self.assertContains(response, "Miles Davis")
        self.assertContains(response, "Jazz")
        self.assertContains(response, "9:22")
        self.assertContains(response, "Africa")
        self.assertNotContains(response, "No songs are currently available.")
        
 
    def test_song_content_is_html_escaped(self):
        audio = SimpleUploadedFile("test.mp3", b"fake audio bytes", content_type="audio/mpeg")
        Song.objects.create(title="<script>alert(1)</script>", artist="X", audio_file=audio)
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertNotContains(response, "<script>alert(1)</script>")
        self.assertContains(response, "&lt;script&gt;")

# =============== PAGES TEST ================

class PagesTest(TestCase):
    PAGES = [
        ("playlists", "crate/playlists.html"),
        ("recommendations", "crate/recommendations.html"),
        ("my_account", "crate/my_account.html"),
    ]
 
    def setUp(self):
        self.user = User.objects.create_user("alice", password=STRONG_PASSWORD)
 
    def test_pages_require_login(self):
        for name, _ in self.PAGES:
            with self.subTest(page=name):
                url = reverse(name)
                response = self.client.get(url)
                self.assertRedirects(response, f"{reverse('login')}?next={url}")
 
    def test_pages_render_for_logged_in_user(self):
        self.client.force_login(self.user)
        for name, template in self.PAGES:
            with self.subTest(page=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, template)
 
    def test_nav_links_shown_only_when_logged_in(self):
        anon = self.client.get(reverse("home"))
        for name, _ in self.PAGES:
            self.assertNotContains(anon, f'href="{reverse(name)}"')
        self.client.force_login(self.user)
        authed = self.client.get(reverse("home"))
        for name, _ in self.PAGES:
            with self.subTest(page=name):
                self.assertContains(authed, f'href="{reverse(name)}"')
        self.assertContains(authed, f'href="{reverse("song_list")}"')
 


 
# ============ END-TO-END FLOW ==============
 
class AuthFlowIntegrationTests(TestCase):
    def test_signup_logout_login_and_access_songs(self):
        # Sign up (auto-login)
        self.client.post(
            reverse("signup"),
            {"username": "flow", "password1": STRONG_PASSWORD, "password2": STRONG_PASSWORD},
        )
        self.assertEqual(self.client.get(reverse("song_list")).status_code, 200)
 
        # Log out -> protected page redirects
        self.client.post(reverse("logout"))
        self.assertEqual(self.client.get(reverse("song_list")).status_code, 302)
 
        # Log back in -> access restored
        self.client.post(reverse("login"), {"username": "flow", "password": STRONG_PASSWORD})
        self.assertEqual(self.client.get(reverse("song_list")).status_code, 200)


# One valid MPEG-1 Layer III frame (128 kbps, 44.1 kHz), repeated: enough for
# mutagen to recognise the bytes as an MP3 without needing real audio.
MP3_FRAME = b"\xff\xfb\x90\x00" + b"\x00" * 413
MP3_BYTES = MP3_FRAME * 20
 
 
def make_mp3(**tags):
    """Return the bytes of a small MP3, with ID3 tags if any are given."""
    if not tags:
        return MP3_BYTES
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        f.write(MP3_BYTES)
        path = f.name
    try:
        id3 = EasyID3()
        id3.update(tags)
        id3.save(path)
        with open(path, "rb") as f:
            return f.read()
    finally:
        os.unlink(path)
 
 
def make_flac(vorbis=None, id3=None):
    """
    Return the bytes of a minimal, valid FLAC file (header only, no audio
    frames, which is all tag reading needs). `vorbis` is a dict of FLAC's own
    tags; `id3` is a dict of title/artist/album/genre to put in an ID3 header
    in front of the file, which some taggers do instead of using FLAC tags.
    """
    # STREAMINFO: 44.1 kHz, 2 channels, 16-bit, 1 second of samples
    streaminfo = struct.pack(">HHII", 4096, 4096, 0, 0)[:4] + b"\x00" * 6
    packed = (44100 << 44) | (1 << 41) | (15 << 36) | 44100
    streaminfo += struct.pack(">Q", packed) + b"\x00" * 16
    data = b"fLaC" + b"\x80" + struct.pack(">I", len(streaminfo))[1:] + streaminfo
    with tempfile.NamedTemporaryFile(suffix=".flac", delete=False) as f:
        f.write(data)
        path = f.name
    try:
        if vorbis:
            flac = FLAC(path)
            flac.add_tags()
            for key, value in vorbis.items():
                flac[key] = value
            flac.save()
        if id3:
            frames = {"title": TIT2, "artist": TPE1, "album": TALB, "genre": TCON}
            tag = ID3()
            for key, value in id3.items():
                tag.add(frames[key](encoding=3, text=value))
            tag.save(path)
        with open(path, "rb") as f:
            return f.read()
    finally:
        os.unlink(path)
 
 
def upload(data, name="track.mp3", content_type="audio/mpeg"):
    return SimpleUploadedFile(name, data, content_type=content_type)
 
 
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
 
