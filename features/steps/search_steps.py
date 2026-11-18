from behave import given, when, then

from django.contrib.auth import get_user_model
from django.urls import reverse

from crate.models import Song
from crate import views

User = get_user_model()
PW = "Sup3r-Secret-Pass!"


@given('I am a logged-in user')
def logged_in(context):
    user, _ = User.objects.get_or_create(username="alice")
    user.set_password(PW)
    user.save()
    context.user = user
    context.test.client.force_login(user)


@given('I own the song "{title}" by "{artist}"')
def own_song(context, title, artist):
    Song.objects.create(title=title, artist=artist, genre="Rock",
                        minutes=3, seconds=58, user=context.user)


@when('I search for "{query}"')
def do_search(context, query):
    context.response = context.test.client.get(reverse("search"), {"q": query})


@then('the web results include "{title}"')
def web_includes(context, title):
    titles = [w["title"] for w in context.response.context["web_results"]]
    context.test.assertIn(title, titles)


@then('the web results do not include "{title}"')
def web_excludes(context, title):
    titles = [w["title"] for w in context.response.context["web_results"]]
    context.test.assertNotIn(title, titles)


@then('my library results include "{title}"')
def library_includes(context, title):
    titles = [s.title for s in context.response.context["songs"]]
    context.test.assertIn(title, titles)


@then('the web results play royalty-free music')
def web_royalty_free(context):
    results = context.response.context["web_results"]
    context.test.assertTrue(results)
    for w in results:
        context.test.assertEqual(w["audio_url"], views.ROYALTY_FREE_AUDIO_URL)