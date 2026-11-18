"""Song editing, validation, and ownership regression tests."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from crate.models import Song


class EditSongTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user('editor', password='StrongPass123!')
        self.other = user_model.objects.create_user('other', password='StrongPass123!')
        self.song = Song.objects.create(
            title='Original', artist='Artist', album='Old album', genre='Jazz',
            audio_file='audio/original.mp3', minutes=3, seconds=12, user=self.owner,
        )
        self.url = reverse('edit_song', args=[self.song.pk])
        self.client.force_login(self.owner)

    def test_get_prefills_form_without_audio_field(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Original')
        self.assertEqual(response.context['form'].instance, self.song)
        self.assertNotIn('audio_file', response.context['form'].fields)

    def test_save_metadata_preserves_audio_and_duration(self):
        response = self.client.post(self.url, {
            'title': 'Updated', 'artist': 'New artist', 'album': 'New album',
            'genre': 'Rock', 'year': '2024',
        })
        self.assertRedirects(response, reverse('song_list'))
        self.song.refresh_from_db()
        self.assertEqual((self.song.title, self.song.artist, self.song.album,
                          self.song.genre, self.song.year),
                         ('Updated', 'New artist', 'New album', 'Rock', 2024))
        self.assertEqual(self.song.audio_file.name, 'audio/original.mp3')
        self.assertEqual((self.song.minutes, self.song.seconds), (3, 12))

    def test_invalid_year_does_not_save(self):
        response = self.client.post(self.url, {
            'title': 'Changed', 'artist': 'Artist', 'year': '99',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context['form'], 'year', 'Enter a four-digit release year.')
        self.song.refresh_from_db()
        self.assertEqual(self.song.title, 'Original')

    def test_other_user_cannot_view_or_edit(self):
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.assertEqual(self.client.post(self.url, {'title': 'Stolen', 'artist': 'X'}).status_code, 404)
        self.song.refresh_from_db()
        self.assertEqual(self.song.title, 'Original')

    def test_anonymous_user_redirected_to_login(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_edit_link_visible_in_song_list(self):
        response = self.client.get(reverse('song_list'))
        self.assertContains(response, self.url)
