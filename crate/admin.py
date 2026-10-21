from django.contrib import admin

from .models import Song, Playlist

 
@admin.register(Song)
class SongAdmin(admin.ModelAdmin):
    # Duration comes from the audio file, so it can't be edited by hand.
    readonly_fields = ("minutes", "seconds")
    list_display = ("title", "artist", "user", "genre", "minutes", "seconds")
    list_filter = ("user",)
 

@admin.register(Playlist)
class PlaylistAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "created_at")
    list_filter = ("user",)