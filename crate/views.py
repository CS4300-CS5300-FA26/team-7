from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.views.decorators.http import require_POST
from django.contrib.auth.forms import UserCreationForm
from crate.models import Song, Playlist

# we will use this when setting up authentication through Django accounts
from django.contrib.auth.decorators import login_required

# ============ VIEWS ==============

def home_view(request):
    return render(request, 'home.html')

# Handles new-user registration.
# On POST: validates the submitted signup form; if valid, creates the user,
# logs them in immediately, and sends them to the homepage.
# On GET (or invalid form): shows a blank/re-rendered signup form.
def signup_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()  # Saves the new user to the database
            login(request, user)  # Automatically logs the user in after signing up
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'registration/signup.html', {'form': form})

# Displays every song in the database as a list.
# Login required — only authenticated users can view it.
@login_required
def song_list(request):
    # grab songs from the database store it in songs
    songs = Song.objects.all()
    # pass the songs to the template as songs and render the page
    return render(request, 'crate/song_list.html', {'songs': songs})

# Displays all playlists (newest first) plus the full song list.
# The playlists populate the page's table; the songs feed the
# "Create Playlist" popup's song picker. Login required.
@login_required
def playlists(request):
    playlists = Playlist.objects.all().order_by('-created_at')
    songs = Song.objects.all().order_by('title')
    return render(request, 'crate/playlists.html', {
        'playlists': playlists,
        'songs': songs,
    })

# Handles the "Create Playlist" form submission (POST only).
# Reads the playlist name and the set of checked song IDs, creates the
# playlist, then attaches the selected songs via the M:N relationship.
# Redirects back to the playlists page when done.
@require_POST
@login_required
def create_playlist(request):
    name = request.POST.get('name', '').strip()
    song_ids = request.POST.getlist('songs')    # all checked boxes named "songs"
    if name:
        playlist = Playlist.objects.create(name=name)   # save first - needed for M:N
        playlist.songs.set(song_ids)                    # attach selected songs
    return redirect('playlists')

# Renders the user's account page. Placeholder — no data wired up yet.
@login_required
def my_account(request):
    return render(request, 'crate/my_account.html')

# Renders the recommendations page. Placeholder — no data wired up yet.
@login_required
def recommendations(request):
    return render(request, 'crate/recommendations.html')
