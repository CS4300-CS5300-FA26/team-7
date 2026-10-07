from django.db import models

class Song(models.Model):

    title = models.CharField(max_length=200)
    artist = models.CharField(max_length=200)
    genre = models.CharField(max_length=200, blank=True)
    album = models.CharField(max_length=200, blank=True)

    duration_seconds = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.title} — {self.artist}"

