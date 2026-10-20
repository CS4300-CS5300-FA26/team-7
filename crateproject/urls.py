"""
URL configuration for crateproject project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.urls import path, include
from django.contrib import admin
from django.conf.urls.static import static

# allows us to take our views and create a url to that page
from crate import views


urlpatterns = [
    path('admin/', admin.site.urls),
    
    path('song_list/', views.song_list, name='song_list'),
    path('songs/<int:id>/delete/', views.song_delete, name='song_delete'),

    path('recommendations/', views.recommendations, name='recommendations'),
    
    path('playlists/', views.playlists, name='playlists'),
    path('playlists/create/', views.create_playlist, name='create_playlist'),

    #For Adding song to playlist
    path(
        'songs/<int:song_id>/add-to-playlist/',
        views.add_song_to_playlist,
        name='add_song_to_playlist',
    ),

    #For Playlist detail
    path(
        'playlists/<int:playlist_id>/',
        views.playlist_detail,
        name='playlist_detail',
    ),

    #For Removing song from playlist
    path(
        'playlists/<int:playlist_id>/remove-song/<int:song_id>/',
        views.remove_song_from_playlist,
        name='remove_song_from_playlist',
    ),
 
    #For user authentication
    path('accounts/', include('django.contrib.auth.urls')),
    # Custom signup URL
    path('accounts/signup/', views.signup_view, name='signup'),
    path('my_account/', views.my_account, name='my_account'),

    # For file uploads
    path('upload_song/', views.upload_song, name="upload_song"),
    path('upload_song/metadata/', views.song_metadata, name="song_metadata"),
       
    
    # Simple homepage target
    path('', views.home_view, name='home')
]

#serve media files statically during local development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)