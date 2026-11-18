"""Store new song cover uploads on Cloudinary rather than ephemeral local disk."""
from django.db import migrations, models
import cloudinary_storage.storage


class Migration(migrations.Migration):
    dependencies = [("crate", "0011_song_year_cover")]

    operations = [
        migrations.AlterField(
            model_name="song",
            name="cover",
            field=models.ImageField(
                blank=True, null=True, upload_to="covers/",
                storage=cloudinary_storage.storage.MediaCloudinaryStorage(),
            ),
        ),
    ]
