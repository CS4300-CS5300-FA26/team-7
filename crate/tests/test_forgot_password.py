# used to get code out of the email
import re

# get user model
from django.contrib.auth import get_user_model
# hold emails for tests
from django.core import mail
from django.test import TestCase
from django.urls import reverse

# get user model
User = get_user_model()


# tests for the "enter your email" step
class ForgotPasswordTests(TestCase):
    # class-level method so it runs once for the whole class
    @classmethod
    # sets up a user for the tests
    def setUpTestData(cls):
        # Create a test user and keep it on the class so every test can use it
        cls.user = User.objects.create_user(
            username="kaleb",
            email="kaleb@example.com",
            password="old-password-123",
        )

    # Test: the login page links to the forgot password page
    def test_login_page_has_forgot_password_link(self):
        """Given I'm on the login screen, I can see the forgot password button."""
        # Load the login page (GET request)
        response = self.client.get(reverse("login"))
        # passes if page loaded successfully and its HTML contains the forgot password URL
        self.assertContains(response, reverse("forgot_password"))

    # Test: a registered email gets a code emailed to it
    def test_registered_email_is_sent_a_code(self):
        """When I enter my account's email, then I am sent an email with a code."""
        # Submit the forgot-password form (POST request) with the user's email
        response = self.client.post(
            # The URL to post to, and the form data being submitted
            reverse("forgot_password"), {"email": "kaleb@example.com"}
        )

        # passes if you are redirected after typing password
        self.assertRedirects(response, reverse("verify_code"))
        # passes if one email was sent
        self.assertEqual(len(mail.outbox), 1)
        # passes if email sent only to the right person
        self.assertEqual(mail.outbox[0].to, ["kaleb@example.com"])
        # passes if message contains loging code
        self.assertIn("login code", mail.outbox[0].subject.lower())
        # The body contains a 6-digit code
        # passes if the body contains a 6-digit number
        self.assertRegex(mail.outbox[0].body, r"\b\d{6}\b")

    # Test: the email lookup ignores uppercase/lowercase
    def test_email_match_is_case_insensitive(self):
        # Submit the form with the email typed in different capitalization
        self.client.post(reverse("forgot_password"), {"email": "KALEB@Example.com"})
        # passes if an email was still sent, so the match worked
        self.assertEqual(len(mail.outbox), 1)

    # Test: an email with no account gets nothing
    def test_unknown_email_is_not_sent_anything(self):
        """When I enter an email not tied to an account, then no email is sent."""
        # Submit the form with an email that doesn't belong to any user
        response = self.client.post(
            # The URL to post to, and the form data being submitted
            reverse("forgot_password"), {"email": "nobody@example.com"}
        )

        # passes if no email was sent
        self.assertEqual(len(mail.outbox), 0)
        # passes if still redirected
        self.assertRedirects(response, reverse("verify_code"))

    # Test: a deactivated account gets nothing
    def test_inactive_user_is_not_sent_anything(self):
        # Mark the test user as deactivated
        self.user.is_active = False
        # Save that change to the test database
        self.user.save()

        # Submit the form with that users email
        self.client.post(reverse("forgot_password"), {"email": "kaleb@example.com"})
        # Passes if no email was sent
        self.assertEqual(len(mail.outbox), 0)

    # Test: something that isn't an email address is rejected
    def test_invalid_email_format_is_rejected(self):
        # submit the form with text that isn't a valid email
        response = self.client.post(reverse("forgot_password"), {"email": "not-an-email"})

        # passes if the form is displayed with errors
        self.assertEqual(response.status_code, 200)  # form re-rendered with errors
        # Passes if no email was sent
        self.assertEqual(len(mail.outbox), 0)


# group of tests for the "enter your code" step
class VerifyCodeTests(TestCase):
    @classmethod

    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            # Username, email, and password for the test account
            username="kaleb", email="kaleb@example.com", password="old-password-123"
        )

    # A helper method that does step one and returns the code
    def request_code(self):
        """Go through the forgot-password step and return the emailed code."""
        # Submit the forgot-password form so a code is generated and emailed
        self.client.post(reverse("forgot_password"), {"email": "kaleb@example.com"})
        # Find the 6-digit number in the email body and return it as a string
        return re.search(r"\b(\d{6})\b", mail.outbox[0].body).group(1)

    # Test: you can't open the verify page without doing step one
    def test_verify_page_requires_forgot_password_step_first(self):
        # visit the verify page directly without requesting a code
        response = self.client.get(reverse("verify_code"))
        # passes if sent back to the forgot-password page
        self.assertRedirects(response, reverse("forgot_password"))

    # Test: the right code logs you in
    def test_correct_code_logs_the_user_in(self):
        # Request a code and get the real one from the email
        code = self.request_code()

        # Submit that code on the verify page
        response = self.client.post(reverse("verify_code"), {"code": code})

        # Passes if the login succeeded
        self.assertEqual(response.status_code, 302)
        # passes if the user is now logged in
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.pk)

    # Test: a wrong code is rejected
    def test_wrong_code_does_not_log_in(self):
        # request a code and get the real one from the email
        code = self.request_code()
        # Build a wrong code (000000, unless the real code happens to be that)
        wrong = "000000" if code != "000000" else "123456"

        # Submit the wrong code on the verify page
        response = self.client.post(reverse("verify_code"), {"code": wrong})

        # passses if page loaded again ( wrong code)
        self.assertEqual(response.status_code, 200)
        # passes if page shows the error message
        self.assertContains(response, "Invalid or expired code.")
        # passes if user not logged in
        self.assertNotIn("_auth_user_id", self.client.session)

    # Test: a code works only once
    def test_code_cannot_be_reused(self):
        # Request a code and get the real one from the email
        code = self.request_code()
        # Submit the correct code which logs the user in and consumes the code
        self.client.post(reverse("verify_code"), {"code": code})
        # Log out, which also clears the session
        self.client.logout()

        # Without a fresh request, the verify page is closed and the code is gone
        # Try submitting the same code again
        response = self.client.post(reverse("verify_code"), {"code": code})
        # passes if the page redirects to forgot-password
        self.assertRedirects(response, reverse("forgot_password"))
        # passes if user is not logged in
        self.assertNotIn("_auth_user_id", self.client.session)

    # Test: too many wrong guesses lock the code
    def test_code_locks_after_max_attempts(self):
        # Request a code and get the real one from the email
        code = self.request_code()
        # Build a wrong code (000000, unless the real code happens to be that)
        wrong = "000000" if code != "000000" else "111111"

        # Repeat the next line 5 times
        for _ in range(5):
            # Submit the wrong code, using up one attempt each time
            self.client.post(reverse("verify_code"), {"code": wrong})

        # Even the correct code fails now
        # Now submit the correct code after all 5 attempts are used
        self.client.post(reverse("verify_code"), {"code": code})
        # passes if user is still not logged in, so the lockout worked
        self.assertNotIn("_auth_user_id", self.client.session)