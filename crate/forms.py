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


#######################################
#forgot password
#######################################

class ForgotPasswordForm(forms.Form):
    email = forms.EmailField()


class VerifyCodeForm(forms.Form):
    code = forms.CharField(
        min_length=6,
        max_length=6,
        widget=forms.TextInput(attrs={"autocomplete": "one-time-code", "inputmode": "numeric"}),
    )