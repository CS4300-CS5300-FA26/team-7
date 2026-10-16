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
    # leaving as main page until we make a dedicated page for home
    path('song_list/', views.song_list, name='song_list'),
    path('songs/<int:id>/delete/', views.song_delete, name='song_delete'),
    path('recommendations/', views.recommendations, name='recommendations'),
    path('playlists/', views.playlists, name='playlists'),
    path('my_account/', views.my_account, name='my_account'),

    #For user authentication
    path('accounts/', include('django.contrib.auth.urls')),
    # Custom signup URL
    path('accounts/signup/', views.signup_view, name='signup'),

    # For file uploads
    path('upload_song/', views.upload_song, name="upload_song"),
    
    
    # Simple homepage target
    path('', views.home_view, name='home')
]

#serve media files statically during local development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)