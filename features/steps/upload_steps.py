from behave import given, when, then 

from django.contrib.auth import get_user_model 
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse 

from crate.models import Song 
from crate.tests.helpers import make_wav    # reuse the valid-WAV generator

User = get_user_model()


@given('"{username}" uploads a song titled "{title}" with an audio file')
@when('"{username}" uploads a song titled "{title}" with an audio file')
def upload_song(context, username, title):
    audio = SimpleUploadedFile("track.wav", make_wav(), content_type="audio/wav")
    context.response = context.test.client.post(reverse("upload_song"), {
        "title": title, "artist": "Test Artist",
        "genre": "", "album": "", "audio_file": audio,
    })


@when('"{username}" views the song list')
def view_song_list(context, username):
    context.response = context.test.client.get(reverse("song_list"))


@then('the song "{title}" exists for "{username}"')
def song_exists(context, title, username):
    user = User.objects.get(username=username)
    context.test.assertTrue(Song.objects.filter(title=title, user=user).exists())


@then('the song "{title}" belongs to "{username}"')
def song_belongs(context, title, username):
    user = User.objects.get(username=username)
    song = Song.objects.get(title=title)
    context.test.assertEqual(song.user, user)


@then('the song "{title}" is stored on Cloudinary')
def song_on_cloudinary(context, title):
    song = Song.objects.get(title=title)
    context.test.assertIn("res.cloudinary.com", song.audio_file.url)


@then('the song list does not show "{title}"')
def song_list_excludes(context, title):
    titles = [s.title for s in context.response.context["songs"]]
    context.test.assertNotIn(title, titles)