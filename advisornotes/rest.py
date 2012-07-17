from advisornotes.models import AdvisorNote
from coredata.models import Role, Person, Unit
from dashboard.models import UserConfig
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import transaction
import base64
import json

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

@transaction.commit_on_success
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
    file_list = []
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
        
        #Check for fileupload
        file_info = {}
        if 'filename' in note and 'mediatype' in note and 'data' in note:
            filename = note['filename']
            mediatype = note['mediatype']
            file_data = note['data']
            if not isinstance(filename, basestring):
                raise ValidationError("Note filename must be a string")
            if not isinstance(mediatype, basestring):
                raise ValidationError("Note mediatype must be a string")
            if not isinstance(file_data, basestring):
                raise ValidationError("Note file data must be a string")
            
            try:
                file_data = base64.b64decode(file_data)
            except TypeError:
                raise ValidationError("Invalid base64 data for note file attachment")
            
            file_info = {'name': filename, 'mediatype': mediatype, 'data': file_data}
        
        note = AdvisorNote()
        note.student = student
        note.advisor = advisor
        note.unit = unit
        note.text = text
        notes_list.append(note)
        file_list.append(file_info)
        
    for index in range(len(notes_list)):
        note = notes_list[index]
        file_info = file_list[index]
        if not 'name' in file_info:
            note.save()
        else:
            note.file_attachment.save(name=file_info['name'], content=ContentFile(file_info['data']), save=False)
            note.file_mediatype = file_info['mediatype']
            note.save()
        

def new_advisor_notes(post_data):
    """
    Parses the JSON post data, validates, and save the advisor notes
    """
    data = json.loads(post_data) # throws ValueError on bad JSON, UnicodeDecodeError on bad UTF-8
    
    advisor, unit = _validate_credentials(data)
    _create_advising_notes(data, advisor, unit)
    
    
  
