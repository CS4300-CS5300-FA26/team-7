"""Tests that audio uploads are wired to Cloudinary storage."""
 
from unittest.mock import patch
 
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
 
from cloudinary_storage.storage import VideoMediaCloudinaryStorage
 
from crate.models import Song
 
User = get_user_model()
 



# ============ CLOUDINARY STORAGE ==============
class AudioStorageWiringTests(TestCase):
    """The audio_file field must be wired to Cloudinary's video storage."""

    def test_audio_file_uses_cloudinary_video_storage(self):
        storage = Song._meta.get_field("audio_file").storage
        self.assertIsInstance(storage, VideoMediaCloudinaryStorage)

    def test_audio_stored_as_video_resource_type(self):
        storage = Song._meta.get_field("audio_file").storage
        self.assertEqual(storage.RESOURCE_TYPE, "video")

class AudioUploadRoutingTests(TestCase):
    """Saving a Song with audio should upload to Cloudinary, not the local disk."""

    @patch("cloudinary.uploader.upload")
    def test_saving_audio_uploads_to_cloudinary_as_video(self, mock_upload):
        mock_upload.return_value = {"public_id": "audio/test-track"}
        user = User.objects.create_user("alice", password="Sup3r-Secret-Pass!")
        audio = SimpleUploadedFile("track.mp3", b"\xff\xfb\x90\x00fake", content_type="audio/mpeg")
        song = Song.objects.create(title="T", artist="A", audio_file=audio, user=user)

        self.assertTrue(mock_upload.called)
        self.assertEqual(mock_upload.call_args.kwargs["resource_type"], "video")
        self.assertIn("res.cloudinary.com", song.audio_file.url)
        self.assertIn("/video/", song.audio_file.url)
