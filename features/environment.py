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


def after_scenario(context, scenario):
    if getattr(context, "_cloud_patch", None) is not None:
        context._cloud_patch.stop()
        context._cloud_patch = None