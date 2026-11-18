"""Cloudinary storage for song artwork."""
from unittest.mock import patch

from cloudinary_storage.storage import MediaCloudinaryStorage
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from crate.models import Song


class CoverCloudinaryTests(TestCase):
    def test_cover_uses_cloudinary_image_storage(self):
        storage = Song._meta.get_field("cover").storage
        self.assertIsInstance(storage, MediaCloudinaryStorage)
        self.assertEqual(storage.RESOURCE_TYPE, "image")

    @patch("cloudinary.uploader.upload")
    def test_cover_upload_uses_image_resource_and_cloudinary_url(self, upload):
        upload.return_value = {"public_id": "covers/test-cover"}
        user = get_user_model().objects.create_user("cover-user", password="StrongPass123!")
        cover = SimpleUploadedFile(
            "cover.png",
            # A valid one-pixel PNG.
            bytes.fromhex(
                "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
                "0000000b49444154789c636000020000050001a5f645400000000049454e44ae426082"
            ),
            content_type="image/png",
        )
        song = Song.objects.create(title="Track", artist="Artist", user=user, cover=cover)
        self.assertTrue(upload.called)
        self.assertEqual(upload.call_args.kwargs["resource_type"], "image")
        self.assertIn("res.cloudinary.com", song.cover.url)
        self.assertIn("/image/", song.cover.url)
