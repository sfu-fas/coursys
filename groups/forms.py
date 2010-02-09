from django import forms

class GroupForm(forms.Form):
    name=forms.CharField(max_length=30, label='Name:')
    manager=forms.CharField(max_length=20, label='Group Manager:')
    
    #TODO Invite students to the group
