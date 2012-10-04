from dashboard.models import UserConfig
from django.core.exceptions import ValidationError
from coredata.models import Role, Person, Unit
import json
import datetime

_token_not_found = """The secret token provided in the JSON request 
                        doesn't match the user's secret token; or the 
                        user has not been assigned a secret token.""" 

def _check_token(person, secret, key):
    try:
        config = UserConfig.objects.get(user__userid=person, key=key)
        if config.value['token'] == secret:
            return True
        return False
    except UserConfig.DoesNotExist:
        return False

def validate_credentials(data):
    """ Determine if the data contains a valid user, secret, and unit. 

    If the data doesn't validate, it will throw a "ValidationError". 
    """
    try:
        person = data['person']
    except KeyError:
        raise ValidationError("The key 'person' is not present. Please validate as a coursys user.")

    try:
        secret = data['secret']
    except KeyError:
        raise ValidationError("The key 'secret' is not present. ")

    try:
        unit = data['unit']
    except KeyError:
        raise ValidationError("The key 'unit' is not present.")

    if  _check_token(person, secret, 'problems-token'):
        person = Person.objects.get(userid=person)
        unit = Unit.objects.get(label=unit)
        return person, unit, 'problems-token'

    if  _check_token(person, secret, 'advisor-token'):
        person = Person.objects.get(userid=person)
        unit = Unit.objects.get(label=unit)
        return person, unit, 'advisor-token'
    
    raise ValidationError(_token_not_found)
