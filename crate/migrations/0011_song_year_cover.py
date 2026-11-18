from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('crate', '0010_alter_song_audio_file')]

    operations = [
        migrations.AddField(model_name='song', name='year', field=models.PositiveIntegerField(blank=True, null=True)),
        migrations.AddField(model_name='song', name='cover', field=models.ImageField(blank=True, null=True, upload_to='covers/')),
    ]
