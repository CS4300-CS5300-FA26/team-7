from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth import login
from django.views.decorators.http import require_POST
from django.contrib.auth.forms import UserCreationForm
from django.views.decorators.http import require_POST
from crate.models import Song, Playlist, read_audio_metadata
from .forms import SongForm

#Imports for my_account view
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.shortcuts import render, redirect

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

# Renders the user's account page. Handles user password change
@login_required
def my_account(request):
    form = None
    #If the user submits the form
    if request.method == 'POST':
        #using djangos builtin password change form for simple implimentation
        form = PasswordChangeForm(request.user, request.POST)
        #If the user enters valid current password, and new passwords
        if form.is_valid():
            #sets the password for the user
            user = form.save()
            update_session_auth_hash(request, user)  # keeps the user logged in
            messages.success(request, 'Your password has been updated.')
            #back to account page
            return redirect('my_account')
    #If not a POST
    elif 'change_password' in request.GET:
        #Display empty form
        form = PasswordChangeForm(request.user)
    # renders template and passes the form
    return render(request, 'crate/my_account.html', {'form': form})

# Renders the recommendations page. Placeholder — no data wired up yet.
@login_required
def recommendations(request):
    return render(request, 'crate/recommendations.html')

@login_required
def upload_song(request):
    if request.method == 'POST':
        form = SongForm(request.POST, request.FILES)
        # Song.clean()/save() read the audio file, validate it, and set minutes/seconds
        if form.is_valid():
            form.save()
            return redirect('song_list')
    else:
        form = SongForm()
    return render(request, 'crate/upload_song.html', {'form': form})


# Called by the upload page's JavaScript as soon as a file is chosen. Reads the
# file's tags (title/artist/album/genre) and returns them as JSON so the form
# can be pre-filled. Nothing is saved here.
@login_required
@require_POST
def song_metadata(request):
    audio_file = request.FILES.get('audio_file')
    if audio_file is None:
        return JsonResponse({'error': 'No file uploaded.'}, status=400)
    return JsonResponse(read_audio_metadata(audio_file))
 
@login_required
@require_POST
def song_delete(request, id):
    song = get_object_or_404(Song, id=id)
    song.delete()
    return redirect('song_list')