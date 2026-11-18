# behave hooks. We stub Cloudinary's upload call for any scenario tagged
# @cloudinary so uploads never hit the network or a real account.
from unittest.mock import patch


def before_scenario(context, scenario):
    context._cloud_patch = None 
    if "cloudinary" in scenario.effective_tags:
        context._cloud_patch = patch(
            "cloudinary.uploader.upload",
            return_value={"public_id": "audio/test"}, 
        )
        context._cloud_patch.start()

    context._mb_patch = None
    if "musicbrainz" in scenario.effective_tags:
        context._mb_patch = patch(
            "crate.views.musicbrainz.search_songs",
            return_value=[
                {"title": "Creep", "artist": "Radiohead", "album": "Pablo Honey", "length": "3:58", "mbid": "m1"},
                {"title": "Karma Police", "artist": "Radiohead", "album": "OK Computer", "length": "4:21", "mbid": "m2"},
            ],
        )
        context._mb_patch.start()


def after_scenario(context, scenario):
    if getattr(context, "_cloud_patch", None) is not None:
        context._cloud_patch.stop()
        context._cloud_patch = None

    if getattr(context, "_mb_patch", None) is not None:
        context._mb_patch.stop()
        context._mb_patch = None 