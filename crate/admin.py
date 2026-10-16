from django.contrib import admin

from .models import Song

 
@admin.register(Song)
class SongAdmin(admin.ModelAdmin):
    # Duration comes from the audio file, so it can't be edited by hand.
    readonly_fields = ("minutes", "seconds")
    list_display = ("title", "artist", "genre", "minutes", "seconds")
 
