from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .helpers import STRONG_PASSWORD


User = get_user_model()
 
 
# ============ HOME VIEW TESTS ==============


class HomeViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("alice", password=STRONG_PASSWORD)
 
    def test_home_resolves_at_root(self):
        self.assertEqual(reverse("home"), "/")
 
    def test_home_anonymous_shows_login_and_signup_links(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "crate/home.html")
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
 

