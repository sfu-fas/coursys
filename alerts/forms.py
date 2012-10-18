from django import forms

sample_email = """
Hello, student {{student}}. 

Your GPA, {{gpa}} is bad, and you should feel bad. Here's a picture of a bear: {{bear_picture}}. 

Sincerely: 
Mr. Advisor Man

"""

class BulkEmailForm(forms.Form):
    #avoidspam = forms.BooleanField( required=True, 
    #                                initial=True, 
    #                                label="Do not e-mail students who have already received this e-mail today.")
    email = forms.CharField( required=True, 
                             label="Content", 
                             initial=sample_email, 
                             widget=forms.Textarea)
