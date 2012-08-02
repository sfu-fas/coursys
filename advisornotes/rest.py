from advisornotes.models import AdvisorNote, Problem
from coredata.models import Role, Person, Unit
from dashboard.models import UserConfig
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db.models import Q
import base64
import json
import datetime

def _validate_credentials(data):
    try:
        person = data['person']
        secret = data['secret']
        unit = data['unit']
    except KeyError:
        raise ValidationError("Necessary credentials not present")
    
    try:
        config = UserConfig.objects.get(user__userid=person, key='problems-token')
        if config.value['token'] != secret:
            raise ValidationError("Secret token didn't match")
    except UserConfig.DoesNotExist:
        try:
            config = UserConfig.objects.get(user__userid=person, key='advisor-token')
            Role.objects.get(role='ADVS', unit__label=unit, person__userid=person)
            if config.value['token'] != secret:
                raise ValidationError("Secret token didn't match")
        except UserConfig.DoesNotExist:   
            raise ValidationError("No token has been generated for user")
        except Role.DoesNotExist:
            raise ValidationError("User doesn't have the necessary permissions")
    
    person = Person.objects.get(userid=person)
    unit = Unit.objects.get(label=unit)
    return person, unit, config.key


def _create_advising_notes(data, advisor, unit):
    try:
        notes = data['notes']
        if not isinstance(notes, (list, tuple)):
            raise ValidationError("Notes not in list format")
        if len(notes) is 0:
            raise ValidationError("No advising notes present")
    except KeyError:
        raise ValidationError("No advising notes present")
    
    for note in notes:
        advisornote = AdvisorNote()
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
        
        advisornote.student = student
        advisornote.advisor = advisor
        advisornote.unit = unit
        advisornote.text = text
        
        #Check for fileupload
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
            
            advisornote.file_attachment.save(name=filename, content=ContentFile(file_data), save=False)
            advisornote.file_mediatype = mediatype
        
        advisornote.save()
        
        
def _create_advising_problems(data, person):
    try:
        problems = data['problems']
        if not isinstance(problems, (list, tuple)):
            raise ValidationError("Problems not in list format")
        if len(problems) is 0:
            raise ValidationError("No problems present")
    except KeyError:
        raise ValidationError("No problems present")
    
    for problem in problems:
        comments = None
        try:
            emplid = problem['emplid']
            code = problem['code']
            description = problem['description']
            unit = problem['unit']
            resolution_lasts = problem['resolution_lasts']
            
            if not isinstance(emplid, int) or not isinstance(resolution_lasts, int):
                raise ValidationError("Problem emplid & resolution_lasts must be integers")
            try:
                student = Person.objects.get(emplid=emplid)
            except Person.DoesNotExist:
                raise ValidationError("Emplid '%d' doesn't exist" % emplid)
            if not resolution_lasts > 0:
                raise ValidationError("Resolution_lasts must be greater than zero") 
            
            if not isinstance(code, basestring) or not isinstance(description, basestring):
                raise ValidationError("Problem code & description must be strings")
            if len(code) > 30 or len(description) > 50:
                raise ValidationError("Problem code & description must be less than or equal to 30 & 50 characters respectively")
            
            try:
                unit = Unit.objects.get(label=unit)
            except Unit.DoesNotExist:
                raise ValidationError("Unit '%s' does not exist" % unit)
            
            if 'comments' in problem:
                comments = problem['comments']
                if not isinstance(comments, basestring):
                    raise ValidationError("Problem comments must be a string")
        
        except KeyError:
            raise ValidationError("Necessary fields not present in problem")
        
        
        current = Problem.objects.filter(Q(resolved_until__gte=datetime.date.today()) | Q(resolved_until__isnull=True)
                                         , person=student, code=code, unit=unit)
        if len(current) is 0:
            problem = Problem()
            problem.person = student
            problem.code = code
            problem.description = description
            problem.comments = comments
            problem.resolution_lasts = resolution_lasts
            problem.unit = unit
            problem.save()
        
     
        
def new_advisor_notes(post_data):
    """
    Parses the JSON post data, validates, and save the advisor notes
    """
    data = json.loads(post_data) # throws ValueError on bad JSON, UnicodeDecodeError on bad UTF-8
    
    person, unit, key = _validate_credentials(data)
    if key == "advisor-token":
        _create_advising_notes(data, person, unit)
    else:
        _create_advising_problems(data, person)
    
  
