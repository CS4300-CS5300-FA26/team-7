
from django.contrib.auth import get_user_model, SESSION_KEY
from django.test import TestCase
from django.urls import reverse
 
User = get_user_model()
 

# ============ Account Page Tests ==============

class ChangePasswordTests(TestCase):
    #Account setup for tests
    def setUp(self):
        self.old_password = 'oldpass123!'
        self.new_password = 'newpass123'
        self.user = User.objects.create_user(
            username='tester', password=self.old_password
        )
        self.client.login(username='tester', password=self.old_password)
        self.url = reverse('my_account')

    # helper function for the form submission
    def post_change(self, current, new1, new2, **kwargs):
        return self.client.post(self.url, {
            'old_password': current,
            'new_password1': new1,
            'new_password2': new2,
        }, **kwargs)

    # Helper to check if you are still logged in true if logged in
    def assert_logged_in(self):
        self.assertEqual(self.client.session[SESSION_KEY], str(self.user.pk))

    # Access
    def test_login_required(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)
        self.assertNotIn(SESSION_KEY, self.client.session)

    # Scenario 1: opening the change-password form
    def test_account_page_shows_change_password_link(self):
        #go to the account page
        response = self.client.get(self.url)
        #If page loaded the test passes
        self.assertEqual(response.status_code, 200)
        #Passes if change password on page
        self.assertContains(response, 'Change Password')
        #passes if the form isn't open (just button visible) because form = None
        self.assertIsNone(response.context['form'])

    def test_change_password_form_has_three_fields(self):
        #visit the account page, "click" the change password button
        response = self.client.get(self.url + '?change_password=1')
        #passes if we are on the page
        self.assertEqual(response.status_code, 200)
        # passes if the page contains the old_password field
        self.assertContains(response, 'name="old_password"')
        #passes if contains the new password field
        self.assertContains(response, 'name="new_password1"')
        self.assertContains(response, 'name="new_password2"')

    # Scenario 2: changing the password successfully
    def test_password_changed_successfully(self):
        #submit the form with correct passwords
        response = self.post_change(
            self.old_password, self.new_password, self.new_password
        )
        #passes if we are back on account page
        self.assertRedirects(response, self.url)
        #reload the user from the database to get new password
        self.user.refresh_from_db()
        # passes if the new password works
        self.assertTrue(self.user.check_password(self.new_password))
        #passes if the old password no longer works
        self.assertFalse(self.user.check_password(self.old_password))

    def test_success_shows_confirmation_message(self):
        #submit the form changing the password
        response = self.post_change(
            self.old_password, self.new_password, self.new_password,
            follow=True,
        )
        #passes if the dialog is on the screen
        self.assertContains(response, 'Your password has been updated.')

    def test_user_stays_logged_in_after_change(self):
        #submit the form with new password
        self.post_change(self.old_password, self.new_password, self.new_password)
        #passes if logged in still
        self.assert_logged_in()

    # Scenario 3: new passwords do not match
    def test_mismatched_passwords_not_updated(self):
        #submit the form with two different new passwords
        response = self.post_change(
            self.old_password, 'newpass123', 'newpass124'
        )
        #passes if we are still on the form
        self.assertEqual(response.status_code, 200)
        # get the user information
        self.user.refresh_from_db()
        #passes if still has the old password
        self.assertTrue(self.user.check_password(self.old_password))
        #passes if not the new password
        self.assertFalse(self.user.check_password('newpass123'))

    def test_mismatched_passwords_show_error(self):
        #submit form with correct old password but no matching new password
        response = self.post_change(
            self.old_password, 'newpass123', 'newpass124'
        )
        #hold the error code from the form submission
        form = response.context['form']
        #passes if the right error message came up
        self.assertEqual(
            form.errors['new_password2'].as_data()[0].code,
            'password_mismatch',
        )
        #confirms that page displays text relevant to the matching passwords
        self.assertContains(response, 'match')

    def test_mismatched_passwords_keep_user_logged_in(self):
        #submit form with correct old password but no matching new password
        self.post_change(self.old_password, 'newpass123', 'newpass124')
        # passes if the user is still logged in
        self.assert_logged_in()

    # Extra: wrong current password
    def test_wrong_current_password_not_updated(self):
        #submit with wrong old password
        response = self.post_change(
            'wrongpass', self.new_password, self.new_password
        )
        #passes if not redirected
        self.assertEqual(response.status_code, 200)
        #passes if error occured
        self.assertIn('old_password', response.context['form'].errors)
        #refresh user info
        self.user.refresh_from_db()
        #passes if old password still works (not changed)
        self.assertTrue(self.user.check_password(self.old_password))
