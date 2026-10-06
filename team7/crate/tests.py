from django.test import TestCase
from django.contrib.auth import get_user_model, SESSION_KEY
from django.contrib.auth.forms import UserCreationForm
from django.urls import reverse
 
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
        self.assertIsNone(song.duration_seconds)
 
    def test_all_fields_are_saved(self):
        song = Song.objects.create(
            title="So What",
            artist="Miles Davis",
            genre="Jazz",
            album="Kind of Blue",
            duration_seconds=562,
        )
        song.refresh_from_db()
        self.assertEqual(song.genre, "Jazz")
        self.assertEqual(song.album, "Kind of Blue")
        self.assertEqual(song.duration_seconds, 562)
 
    def test_duration_must_be_non_negative(self):
        song = Song(title="Bad", artist="Artist", duration_seconds=-5)
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
        Song.objects.create(
            title="So What", artist="Miles Davis", genre="Jazz", duration_seconds=562
        )
        Song.objects.create(title="Africa", artist="Toto", genre="Rock")
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(len(response.context["songs"]), 2)
        self.assertContains(response, "So What")
        self.assertContains(response, "Miles Davis")
        self.assertContains(response, "Jazz")
        self.assertContains(response, "562 seconds")
        self.assertContains(response, "Africa")
        self.assertNotContains(response, "No songs are currently available.")
 
    def test_song_content_is_html_escaped(self):
        Song.objects.create(title="<script>alert(1)</script>", artist="X")
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertNotContains(response, "<script>alert(1)</script>")
        self.assertContains(response, "&lt;script&gt;")
 
 
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
