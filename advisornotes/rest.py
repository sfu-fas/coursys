import json
from django.core.exceptions import ValidationError
from coredata.models import Role, Person, Unit
from dashboard.models import UserConfig
from advisornotes.models import AdvisorNote


def _validate_credentials(data):
    try:
        advisor = data['advisor']
        secret = data['secret']
        unit = data['unit']
    except KeyError:
        raise ValidationError("Necessary credentials not present")
    
    try:
        Role.objects.get(role='ADVS', unit__label=unit, person__userid=advisor)
        config = UserConfig.objects.get(user__userid=advisor, key='advisor-token')
        if not 'token' in config.value or config.value['token'] != secret:
            raise ValidationError("Secret token didn't match")
    except Role.DoesNotExist:
        raise ValidationError("User doesn't have the necessary permissions")
    except UserConfig.DoesNotExist:
        raise ValidationError("No token has been generated for user")
    
    advisor = Person.objects.get(userid=advisor)
    unit = Unit.objects.get(label=unit)
    return advisor, unit

def _create_advising_notes(data, advisor, unit):
    try:
        notes = data['notes']
        if not isinstance(notes, (list, tuple)):
            raise ValidationError("Notes not in list format")
        if len(notes) is 0:
            raise ValidationError("No advising notes present")
    except KeyError:
        raise ValidationError("No advising notes present")
    
    notes_list = []
    for note in notes:
        try:
            emplid = note['emplid']
            text = note['text']
            if not isinstance(emplid, int):
                raise ValidationError("Note emplid must be an integer")
            if not isinstance(text, basestring):
                raise ValidationError("Note text must be a string")
        except KeyError:
            raise ValidationError("Emplid or text not present in note")
        try:
            student = Person.objects.get(emplid=emplid)
        except Person.DoesNotExist:
            raise ValidationError("Emplid '%d' doesn't exist" % emplid)
        
        note = AdvisorNote()
        note.student = student
        note.advisor = advisor
        note.unit = unit
        note.text = text
        notes_list.append(note)
        
    for note in notes_list:
        note.save()
        

def new_advisor_notes(post_data):
    """
    Parses the JSON post data, validates, and save the advisor notes
    """
    try:
        data = json.loads(post_data)
    except ValueError:
        raise ValidationError("Invalid JSON format")
    
    advisor, unit = _validate_credentials(data)
    _create_advising_notes(data, advisor, unit)
    
    
  
