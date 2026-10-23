from behave import given, when, then
from django.contrib.auth import get_user_model 
from django.urls import reverse 
from crate.models import Song, Playlist 

User = get_user_model()

def _passwords(context):
    if not hasattr(context, "passwords"):
        context.passwords = {}
    return context.passwords 

@given('a user "{username}" with password "{password}"')
def create_user(context, username, password):
    user, _ = User.objects.get_or_create(username=username)
    user.set_password(password)
    user.save()
    _passwords(context)[username] = password 

@given('"{username}" has a song titled "{title}"')
def user_has_song(context, username, title):
    user = User.objects.get(username=username)
    Song.objects.create(title=title, artist="Test Artist", user=user)


@given('"{username}" is logged in')
@when('"{username}" is logged in')
def login(context, username):
    ok = context.test.client.login(
        username=username, password=_passwords(context)[username])
    context.test.assertTrue(ok, f"login failed for {username}")


@given('"{username}" creates a playlist named "{name}" containing "{song_title}"')
@when('"{username}" creates a playlist named "{name}" containing "{song_title}"')
def create_playlist(context, username, name, song_title):
    user = User.objects.get(username=username)
    song = Song.objects.get(title=song_title, user=user)
    context.test.client.post(
        reverse("create_playlist"), {"name": name, "songs": [str(song.id)]})


@when('"{username}" submits the create-playlist form with a blank name')
def create_blank(context, username):
    context.test.client.post(
        reverse("create_playlist"), {"name": "   ", "songs": []})


@when('"{username}" views the playlists page')
def view_playlists(context, username):
    context.response = context.test.client.get(reverse("playlists"))


@then('the playlist "{name}" exists for "{username}"')
def playlist_exists(context, name, username):
    user = User.objects.get(username=username)
    context.test.assertTrue(Playlist.objects.filter(name=name, user=user).exists())


@then('the playlist "{name}" contains "{title}"')
def playlist_contains(context, name, title):
    playlist = Playlist.objects.get(name=name)
    context.test.assertTrue(playlist.songs.filter(title=title).exists())


@then('the playlist "{name}" does not contain "{title}"')
def playlist_not_contains(context, name, title):
    playlist = Playlist.objects.get(name=name)
    context.test.assertFalse(playlist.songs.filter(title=title).exists())


@then('the playlists page does not list "{name}"')
def page_does_not_list(context, name):
    listed = [p.name for p in context.response.context["playlists"]]
    context.test.assertNotIn(name, listed)


@then('"{username}" has no playlists')
def no_playlists(context, username):
    user = User.objects.get(username=username)
    context.test.assertEqual(Playlist.objects.filter(user=user).count(), 0)