"""Shared test helpers: the standard test password and builders for tiny, valid
audio files (WAV, MP3, FLAC) so tests never need real recordings.
"""

import io
import os
import struct
import tempfile
import wave

from django.core.files.uploadedfile import SimpleUploadedFile

from mutagen.easyid3 import EasyID3
from mutagen.flac import FLAC
from mutagen.id3 import ID3, TALB, TCON, TIT2, TPE1


STRONG_PASSWORD = "Sup3r-Secret-Pass!"


def make_wav(seconds=5, rate=1000):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(1)
        w.setframerate(rate)
        w.writeframes(b"\x80" * (rate * seconds))
    return buf.getvalue()


# One valid MPEG-1 Layer III frame (128 kbps, 44.1 kHz), repeated: enough for
# mutagen to recognise the bytes as an MP3 without needing real audio.
MP3_FRAME = b"\xff\xfb\x90\x00" + b"\x00" * 413

MP3_BYTES = MP3_FRAME * 20


def make_mp3(**tags):
    """Return the bytes of a small MP3, with ID3 tags if any are given."""
    if not tags:
        return MP3_BYTES
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        f.write(MP3_BYTES)
        path = f.name
    try:
        id3 = EasyID3()
        id3.update(tags)
        id3.save(path)
        with open(path, "rb") as f:
            return f.read()
    finally:
        os.unlink(path)


def make_flac(vorbis=None, id3=None):
    """
    Return the bytes of a minimal, valid FLAC file (header only, no audio
    frames, which is all tag reading needs). `vorbis` is a dict of FLAC's own
    tags; `id3` is a dict of title/artist/album/genre to put in an ID3 header
    in front of the file, which some taggers do instead of using FLAC tags.
    """
    # STREAMINFO: 44.1 kHz, 2 channels, 16-bit, 1 second of samples
    streaminfo = struct.pack(">HHII", 4096, 4096, 0, 0)[:4] + b"\x00" * 6
    packed = (44100 << 44) | (1 << 41) | (15 << 36) | 44100
    streaminfo += struct.pack(">Q", packed) + b"\x00" * 16
    data = b"fLaC" + b"\x80" + struct.pack(">I", len(streaminfo))[1:] + streaminfo
    with tempfile.NamedTemporaryFile(suffix=".flac", delete=False) as f:
        f.write(data)
        path = f.name
    try:
        if vorbis:
            flac = FLAC(path)
            flac.add_tags()
            for key, value in vorbis.items():
                flac[key] = value
            flac.save()
        if id3:
            frames = {"title": TIT2, "artist": TPE1, "album": TALB, "genre": TCON}
            tag = ID3()
            for key, value in id3.items():
                tag.add(frames[key](encoding=3, text=value))
            tag.save(path)
        with open(path, "rb") as f:
            return f.read()
    finally:
        os.unlink(path)


def upload(data, name="track.mp3", content_type="audio/mpeg"):
    return SimpleUploadedFile(name, data, content_type=content_type)