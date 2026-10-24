"""Tests for signing up, logging in and out, and the full auth flow."""
 
from django.contrib.auth import get_user_model, SESSION_KEY
from django.contrib.auth.forms import UserCreationForm
from django.test import TestCase
from django.urls import reverse
 
from .helpers import STRONG_PASSWORD
 
User = get_user_model()
 
 
User = get_user_model()
 
 
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

