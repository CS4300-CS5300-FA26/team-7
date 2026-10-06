from django.shortcuts import render, redirect
from crate.models import Song

# we will use this when setting up authentication through Django accounts
from django.contrib.auth.decorators import login_required

# Create your views here.

# view for song_list
def song_list(request):
    # grab songs from the database store it in songs
    songs = Song.objects.all()
    # pass the songs to the template as songs and render the page
    return render(request, 'crate/song_list.html', {'songs': songs})
