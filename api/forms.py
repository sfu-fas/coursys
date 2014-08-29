from django import forms
from oauth_provider.forms import AuthorizeRequestTokenForm

class AuthForm(AuthorizeRequestTokenForm):
    def __init__(self, *args, **kwargs):
        super(AuthorizeRequestTokenForm, self).__init__(*args, **kwargs)
        self.fields['authorize_access'].label = 'Allow access as described above'