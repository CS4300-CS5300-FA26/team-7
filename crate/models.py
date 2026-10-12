from django.db import models
from django.conf import settings

class Song(models.Model):

    title = models.CharField(max_length=200)
    artist = models.CharField(max_length=200)
    genre = models.CharField(max_length=200, blank=True)
    album = models.CharField(max_length=200, blank=True)

    #for when songs are tied to a specific user.  Will go way outside the scope of this branch
    '''user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name='songs'  # Allows you to query: user.songs.all()
    )'''

    duration_seconds = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.title} — {self.artist}"

