from django import forms
from .models import Song

class SongForm(forms.ModelForm):
    class Meta:
        model = Song
        fields = ['title', 'artist', 'genre', 'album', 'audio_file']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # The model allows songs without audio (e.g. via admin), but the upload page needs a file.
        self.fields['audio_file'].required = True