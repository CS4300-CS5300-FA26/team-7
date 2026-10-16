from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.views.decorators.http import require_POST
from crate.models import Song
from .forms import SongForm
import mutagen

# we will use this when setting up authentication through Django accounts
from django.contrib.auth.decorators import login_required

# ============ VIEWS ==============

def home_view(request):
    return render(request, 'home.html')

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

# view for song_list
@login_required
def song_list(request):
    # grab songs from the database store it in songs
    songs = Song.objects.all()
    # pass the songs to the template as songs and render the page
    return render(request, 'crate/song_list.html', {'songs': songs})

@login_required
def my_account(request):
    return render(request, 'crate/my_account.html')

@login_required
def playlists(request):
    return render(request, 'crate/playlists.html')

@login_required
def recommendations(request):
    return render(request, 'crate/recommendations.html')

@login_required
def upload_song(request):
    if request.method == 'POST':
        form = SongForm(request.POST, request.FILES)
        try:
            #set duration
            uploaded_file = request.FILES['audio_file']
            duration_in_seconds = mutagen.File(uploaded_file).info.length
            form.instance.minutes = duration_in_seconds // 60
            form.instance.seconds = duration_in_seconds % 60
            
            print(f"Song is {form.instance.minutes}:{form.instance.seconds} long")
            if form.is_valid():
                form.save()
                return redirect('song_list')
        except Exception as e:
            print(f"Could not parse audio metadata: {e}")
    
    else:
        form = SongForm()
    return render(request, 'crate/upload_song.html', {'form': form})

@login_required
@require_POST
def song_delete(request, id):
    song = get_object_or_404(Song, id=id)
    song.delete()
    return redirect('song_list')