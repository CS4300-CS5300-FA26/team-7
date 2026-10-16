from django.db import models
from django.conf import settings
import mutagen
from django.core.exceptions import ValidationError


def read_audio_length(fileobj):
    """Return the length of an audio file in seconds, or None if it can't be read."""
    try:
        audio = mutagen.File(fileobj)
        length = None if audio is None else audio.info.length
    except Exception:
        length = None
    finally:
        try:
            fileobj.seek(0)  # leave the file ready to be saved to storage
        except Exception:
            pass
    return length
 

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
    minutes = models.PositiveIntegerField(null=True, blank=True)
    seconds = models.PositiveIntegerField(null=True, blank=True)
        
    audio_file = models.FileField(upload_to="audio/", default='', blank=True, null=True)

    def __str__(self):
        return f"{self.title} — {self.artist}"
        # ---- duration handling ----
 
    def _has_new_audio(self):
        """True when an audio file has been assigned but not yet stored."""
        return bool(self.audio_file) and not self.audio_file._committed
 
    def _set_duration_from_audio(self):
        """Fill minutes/seconds from the new audio file. Returns False if unreadable."""
        length = read_audio_length(self.audio_file.file)
        if length is None:
            return False
        self.minutes, self.seconds = divmod(int(length), 60)
        return True
 
    def clean(self):
        # Runs for ModelForms (admin + upload page), so a non-audio file gets a
        # proper error message instead of being saved.
        super().clean()
        if self._has_new_audio() and not self._set_duration_from_audio():
            raise ValidationError(
                {"audio_file": "Could not read this file as audio. Upload a valid audio file."}
            )
 
    def save(self, *args, **kwargs):
        # Whenever a new file is attached, the stored duration is recalculated.
        # (If a file can't be parsed here, e.g. Song.objects.create(...) with
        # junk bytes, any existing values are left alone.)
        if self._has_new_audio():
            self._set_duration_from_audio()
        super().save(*args, **kwargs)
