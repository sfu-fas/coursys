from django import forms

class TokenForm(forms.Form):
    otp_token = forms.CharField(label="Authenticator Token", required=True, max_length=6, min_length=6)

    def __init__(self, devices=None, *args, **kwargs):
        super(TokenForm, self).__init__(*args, **kwargs)

        self.devices = devices

    def clean_otp_token(self):
        otp_token = self.cleaned_data['otp_token']
        self.device = None

        # check each of the user's devices (to allow entering TOPT or static recovery code).
        for dev in self.devices:
            if dev.verify_token(otp_token):
                self.device = dev
                return otp_token

        raise forms.ValidationError('Incorrect token.')
