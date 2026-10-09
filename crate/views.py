from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from crate.models import Song

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
    return render(request, 'crate/myaccount.html')

@login_required
def my_songs(request):
    return render(request, 'crate/mysongs.html')

@login_required
def playlists(request):
    return render(request, 'crate/playlists.html')

@login_required
def recommendations(request):
    return render(request, 'crate/recommendations.html')

@login_required
def song_list(request):
    return render(request, 'crate/song_list.html')