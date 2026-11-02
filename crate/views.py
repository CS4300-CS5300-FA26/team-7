from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth import login
from django.views.decorators.http import require_POST
from django.contrib.auth.forms import UserCreationForm
from django.views.decorators.http import require_POST
from crate.models import Song, Playlist, read_audio_metadata
from .forms import SongForm
from django.db.models import Case, F, IntegerField, Q, When
from django.db.models.functions import Lower

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
    return render(request, 'crate/home.html')

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

# Displays the logged-in user's own songs as a list.
# Login required — only authenticated users can view it, and nobody sees
# anyone else's songs.
@login_required
def song_list(request):
    # grab this user's songs from the database store it in songs
    songs = Song.objects.filter(user=request.user)
    #allows this user's playlists to displayed on song page
    playlists = Playlist.objects.filter(user=request.user)
    # pass the songs to the template as songs and render the page
    return render(request, 'crate/song_list.html', {'songs': songs, 'playlists' : playlists})

# Displays the user's playlists (newest first) plus the user's song list.
# The playlists populate the page's table; the songs feed the
# "Create Playlist" popup's song picker. Login required.
@login_required
def playlists(request):
    playlists = Playlist.objects.filter(user=request.user).order_by('-created_at')
    songs = Song.objects.filter(user=request.user).order_by('title')
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
        playlist = Playlist.objects.create(name=name, user=request.user)   # save first - needed for M:N
        # only the user's own songs can be attached, whatever ids were submitted
        song_ids = [i for i in song_ids if i.isdigit()]
        playlist.songs.set(Song.objects.filter(user=request.user, id__in=song_ids))
    return redirect('playlists')

#Allows viewing a playlist
@login_required
def playlist_detail(request, playlist_id):
    #Searches for playlist from id and returns a 404 error if not found
    #(only the owner's playlists are found; anyone else's is a 404)
    playlist = get_object_or_404(Playlist, id=playlist_id, user=request.user)

    #Finds songs that are already in the playlist
    songs_in_playlist = playlist.songs.filter(user=request.user)

    #Finds the user's songs that are not in the playlist
    available_songs = Song.objects.filter(user=request.user).exclude(
        playlists=playlist
    )

    return render(request, 'crate/playlist_detail.html', {
        'playlist': playlist,
        'songs': songs_in_playlist,
        'available_songs': available_songs,
    })

#Allows adding a song to playlist
@login_required
@require_POST
def add_song_to_playlist(request, song_id):
    #Searches for playlist and song from id and returns a 404 error if not found
    playlist_id = request.POST.get('playlist_id')
    #(both must belong to the logged-in user)
    playlist = get_object_or_404(Playlist, id=playlist_id, user=request.user)
    song = get_object_or_404(Song, id=song_id, user=request.user)

    #Adds song to playlist
    playlist.songs.add(song)

    #Returns user to either playlist detail page or song list page
    next_page = request.POST.get('next')
    if next_page == 'playlist_detail':
        return redirect('playlist_detail', playlist_id=playlist.id)
    
    return redirect('song_list')

#Allows removing a song from playlist without deleting the song itself
@login_required
@require_POST
def remove_song_from_playlist(request, playlist_id, song_id):
    #Searches for playlist and song from id and returns a 404 error if not found
    #(both must belong to the logged-in user)
    playlist = get_object_or_404(Playlist, id=playlist_id, user=request.user)
    song = get_object_or_404(Song, id=song_id, user=request.user)

    #Removes song from playlist
    playlist.songs.remove(song)

    #Returns user to playlist detail page
    return redirect('playlist_detail', playlist_id=playlist.id)

# Renders the user's account page. Placeholder — no data wired up yet.
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
            song = form.save(commit=False)
            song.user = request.user   # the uploader owns the song
            song.save()
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
    song = get_object_or_404(Song, id=id, user=request.user)   # other users' songs are a 404
    song.delete()
    return redirect('song_list')

#The four current options to search by
SORT_CHOICES = ['title', 'artist', 'genre', 'length']

#Recieves songs, what to sort by, and wheter it is ascending or descending
def sort_songs(songs, sort, direction):
    descending = direction == 'desc'

    def ordered(expression):
        return expression.desc() if descending else expression.asc()

    #Calculates total length of song in seconds for sorting purposes
    if sort == 'length':
        songs = songs.annotate(total_seconds=F('minutes') * 60 + F('seconds'))
        primary = [
            F('total_seconds').desc(nulls_last=True) if descending
            else F('total_seconds').asc(nulls_last=True)
        ]

    #Makes it so songs without a genre will always appear at the bottom (May Change)    
    elif sort == 'genre':
        songs = songs.annotate(
            has_no_genre=Case(
                When(genre='', then=1),
                default=0,
                output_field=IntegerField(),
            ),
        )
        primary = ['has_no_genre', ordered(Lower('genre'))]
    else:
        primary = [ordered(Lower(sort))]

    return songs.order_by(*primary, Lower('title'), 'id')

@login_required
def search(request):
    songs = Song.objects.filter(user=request.user)

    q = request.GET.get('q', '').strip()
    if q:
        songs = songs.filter(
            Q(title__icontains=q) | Q(artist__icontains=q)
            | Q(album__icontains=q) | Q(genre__icontains=q)
        )

    sort = request.GET.get('sort', '').strip().lower()
    if sort not in SORT_CHOICES:
        sort = ''
    direction = 'desc' if request.GET.get('dir') == 'desc' else 'asc'
    songs = sort_songs(songs, sort, direction) if sort else songs.order_by('id')

    return render(request, 'crate/search.html', {
        'songs': songs,
        'q': q,
        'sort_choices': SORT_CHOICES,
        'current_sort': sort,
        'current_dir': direction,
    })