from django.db import models
from django.conf import settings
import mutagen
from mutagen.easyid3 import EasyID3
from django.core.exceptions import ValidationError
from enum import Enum
 
 
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
 
 
# Which tag names to try for each form field, best match first.
METADATA_KEYS = {
    "title": ("title",),
    "artist": ("artist", "albumartist", "performer"),
    "album": ("album",),
    "genre": ("genre",),
}
 
 
def _first_text(sources, keys):
    """First non-blank tag value for any of `keys`, looking through each tag source in turn."""
    for key in keys:
        for tags in sources:
            try:
                values = tags.get(key)
            except Exception:
                continue
            if isinstance(values, str):
                values = [values]
            for value in values or []:
                text = str(value).strip()
                if text:
                    return text[:200]  # the model fields are max_length=200
    return None
 
 
def read_audio_metadata(fileobj):
    """
    Return whatever title/artist/album/genre tags an audio file has, as a dict
    like {"title": "So What", "artist": "Miles Davis"}. Fields the file doesn't
    have are left out, and an unreadable or untagged file gives {}.
    """
    sources = []
    try:
        # easy=True gives the same tag names for mp3/m4a/flac/ogg
        audio = mutagen.File(fileobj, easy=True)
        if getattr(audio, "tags", None):
            sources.append(audio.tags)
    except Exception:
        pass
    try:
        # Some files (notably FLAC) carry their tags in an ID3 header instead of,
        # or as well as, their own tag format. Native tags win when both exist.
        fileobj.seek(0)
        sources.append(EasyID3(fileobj))
    except Exception:
        pass
    finally:
        try:
            fileobj.seek(0)
        except Exception:
            pass
 
    found = {}
    for field, keys in METADATA_KEYS.items():
        text = _first_text(sources, keys)
        if text:
            found[field] = text
    return found
 
 
class Song(models.Model):
    title = models.CharField(max_length=200)
    artist = models.CharField(max_length=200)
    genre = models.CharField(max_length=200, blank=True)
    album = models.CharField(max_length=200, blank=True)
 
    # The user who uploaded the song. Users only ever see their own songs.
    # (null=True so songs that existed before this field was added still load;
    # songs with no owner are visible to nobody until an admin assigns one.)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='songs',  # lets you query: user.songs.all()
        null=True,
        blank=True,
    )
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
 
class Playlist(models.Model):
    name = models.CharField(max_length=200)
    # The user who created the playlist. Users only ever see their own playlists.
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='playlists',
        null=True,
        blank=True,
    )
    songs = models.ManyToManyField(Song, related_name='playlists', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
 
    def __str__(self):
        return self.name